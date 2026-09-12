#!/usr/bin/env python3
"""
Evaluate Wapiti morphological tagger & FST-constrained disambiguation.

Metrics computed:
1. Raw CRF Exact Tag Accuracy (full morphological tag)
2. Raw CRF Major POS Accuracy (e.g. +Noun, +Verb)
3. FST Candidate Coverage (does GrischunGuessing.fst contain the gold tag?)
4. Combined FST+CRF Disambiguation Accuracy (CRF n-best intersected with FST candidates, as in analyse.py)

Includes dataset SHA, metadata, and Wapiti feature template details in the report.

Usage:
    python scripts/evaluate_tagger.py --model crf-morphological-analyzer/hf_data/model.mod \
                                      --test-file crf-morphological-analyzer/hf_data/test.txt \
                                      --fst GrischunGuessing.fst \
                                      --template crf-morphological-analyzer/templates/rumantsch-template.txt \
                                      --metadata crf-morphological-analyzer/hf_data/dataset_metadata.json
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
import foma


def extract_major_pos(tag):
    if not tag:
        return "UNKNOWN"
    m = re.search(r'\+([A-Za-z]+)', tag)
    if m:
        return "+" + m.group(1)
    return tag


def evaluate(model_path, test_file, fst_path, template_path=None, metadata_path=None):
    # Load dataset metadata if available
    metadata = {}
    if metadata_path and os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except Exception as e:
            print(f"Notice: unable to load metadata file: {e}", file=sys.stderr)

    # Read feature template if provided
    template_lines = []
    if template_path and os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            template_lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]

    print(f"Loading FST from {fst_path}...")
    fst = foma.FST.load(fst_path)

    # Read gold sentences
    gold_sentences = []
    current_sent = []
    with open(test_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                if current_sent:
                    gold_sentences.append(current_sent)
                    current_sent = []
            else:
                parts = line.split('\t')
                tok = parts[0]
                tag = parts[1] if len(parts) > 1 else ""
                current_sent.append((tok, tag))
        if current_sent:
            gold_sentences.append(current_sent)

    total_sents = len(gold_sentences)
    total_tokens = sum(len(s) for s in gold_sentences)
    print(f"Loaded {total_sents} sentences, {total_tokens} tokens from {test_file}")

    # Run wapiti label with n-best predictions (n=3)
    cmd = ["wapiti", "label", "-m", model_path, "-n", "3", "-p", "-s", test_file]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        print(f"Error running wapiti: {stderr.decode('utf-8')}", file=sys.stderr)
        sys.exit(1)

    raw_blocks = stdout.decode('utf-8').strip().split("\n\n")

    parsed_sents_nbest = []
    curr_nbest = []
    for block in raw_blocks:
        lines = block.strip().split("\n")
        if not lines or not lines[0]:
            continue
        entry_lines = [l for l in lines if not l.startswith('#') and not l.startswith('*')]
        if not entry_lines:
            continue
        sent_tokens = []
        for l in entry_lines:
            parts = l.split('\t')
            if len(parts) >= 3:
                tok = parts[0]
                pred_tag = parts[2]
                score_str = parts[3] if len(parts) >= 4 else "1.0/1.0"
                try:
                    score = eval(score_str.split('/')[1]) if '/' in score_str else float(score_str)
                except Exception:
                    score = 1.0
                sent_tokens.append((tok, pred_tag, score))
            elif len(parts) == 2:
                tok = parts[0]
                pred_tag = parts[1]
                sent_tokens.append((tok, pred_tag, 1.0))
        if sent_tokens:
            curr_nbest.append(sent_tokens)
            if len(curr_nbest) == 3:
                parsed_sents_nbest.append(curr_nbest)
                curr_nbest = []
    if curr_nbest:
        parsed_sents_nbest.append(curr_nbest)

    crf_exact_correct = 0
    crf_pos_correct = 0

    fst_coverage_count = 0
    disambig_exact_correct = 0
    disambig_pos_correct = 0

    error_types = Counter()

    for sent_idx, gold_sent in enumerate(gold_sentences):
        if sent_idx >= len(parsed_sents_nbest):
            break
        nbest = parsed_sents_nbest[sent_idx]
        best_pred = nbest[0]

        for tok_idx, (gold_tok, gold_tag) in enumerate(gold_sent):
            if tok_idx >= len(best_pred):
                continue
            pred_tok, pred_tag, _ = best_pred[tok_idx]

            gold_pos = extract_major_pos(gold_tag)
            pred_pos = extract_major_pos(pred_tag)

            if pred_tag == gold_tag:
                crf_exact_correct += 1
            else:
                error_types[(pred_pos, gold_pos)] += 1

            if pred_pos == gold_pos:
                crf_pos_correct += 1

            fst_raw = list(fst.apply_up(gold_tok))
            fst_tags = set()
            for cand in fst_raw:
                if "+" in cand:
                    tag_part = "+" + cand.split("+", 1)[1]
                    fst_tags.add(tag_part)

            if gold_tag in fst_tags:
                fst_coverage_count += 1

            # Intersection logic
            selected_tag = None
            for rank_cand in nbest:
                if tok_idx < len(rank_cand):
                    cand_tag = rank_cand[tok_idx][1]
                    if cand_tag in fst_tags:
                        selected_tag = cand_tag
                        break
                    cand_features = set(cand_tag.split('+')[1:])
                    matched = False
                    for f_tag in fst_tags:
                        f_features = set(f_tag.split('+')[1:])
                        if cand_features.issubset(f_features):
                            selected_tag = f_tag
                            matched = True
                            break
                    if matched:
                        break

            if selected_tag is None:
                selected_tag = pred_tag

            if selected_tag == gold_tag:
                disambig_exact_correct += 1
            if extract_major_pos(selected_tag) == gold_pos:
                disambig_pos_correct += 1

    crf_acc = (crf_exact_correct / total_tokens) * 100
    crf_pos_acc = (crf_pos_correct / total_tokens) * 100
    fst_cov = (fst_coverage_count / total_tokens) * 100
    dis_acc = (disambig_exact_correct / total_tokens) * 100
    dis_pos_acc = (disambig_pos_correct / total_tokens) * 100

    print("\n" + "=" * 70)
    print("                EVALUATION & PROVENANCE REPORT")
    print("=" * 70)
    print("Dataset Provenance:")
    print(f"  HF Repository:           {metadata.get('repo_id', 'simon-clmtd/romansh-grischun-morphological-corpus')}")
    print(f"  Dataset Commit SHA:      {metadata.get('commit_sha', 'N/A')}")
    print(f"  Dataset Config / Subset: {metadata.get('config', 'all')}")
    print(f"  Prepared Timestamp:      {metadata.get('prepared_at_utc', 'N/A')}")
    print("-" * 70)
    print("Wapiti Configuration & Feature Template:")
    print(f"  CRF Model Path:          {model_path}")
    print(f"  Template File:           {template_path or 'N/A'}")
    if template_lines:
        print("  Active Feature Patterns:")
        for tpl in template_lines:
            print(f"    • {tpl}")
    print("-" * 70)
    print("Benchmark Metrics (Test Split):")
    print(f"  Test Sentences:                         {total_sents}")
    print(f"  Test Tokens:                            {total_tokens}")
    print(f"  CRF Raw Full Tag Accuracy:              {crf_acc:6.2f}% ({crf_exact_correct}/{total_tokens})")
    print(f"  CRF Raw Major POS Accuracy:             {crf_pos_acc:6.2f}% ({crf_pos_correct}/{total_tokens})")
    print(f"  FST Lexicon Candidate Coverage:         {fst_cov:6.2f}% ({fst_coverage_count}/{total_tokens})")
    print(f"  Combined FST+CRF Tag Accuracy:          {dis_acc:6.2f}% ({disambig_exact_correct}/{total_tokens})")
    print(f"  Combined FST+CRF Major POS Accuracy:    {dis_pos_acc:6.2f}% ({disambig_pos_correct}/{total_tokens})")
    print("=" * 70)
    print("\nTop 10 CRF Confusion Pairs (Pred -> Gold):")
    for (pred_p, gold_p), cnt in error_types.most_common(10):
        print(f"  {pred_p:<15} -> {gold_p:<15} : {cnt:3d} errors")
    print("=" * 70)

    # Also save report to JSON alongside model
    report_data = {
        "dataset_metadata": metadata,
        "model_path": model_path,
        "template_path": template_path,
        "template_active_patterns": template_lines,
        "metrics": {
            "sentences": total_sents,
            "tokens": total_tokens,
            "crf_tag_accuracy": crf_acc,
            "crf_pos_accuracy": crf_pos_acc,
            "fst_coverage": fst_cov,
            "combined_tag_accuracy": dis_acc,
            "combined_pos_accuracy": dis_pos_acc,
        },
        "top_confusion_pairs": [
            {"pred": p, "gold": g, "count": c}
            for (p, g), c in error_types.most_common(10)
        ]
    }
    report_out = os.path.splitext(model_path)[0] + "_eval_report.json"
    with open(report_out, "w", encoding="utf-8") as rf:
        json.dump(report_data, rf, indent=2, ensure_ascii=False)
    print(f"Evaluation report JSON saved to: {report_out}\n")

    return report_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Wapiti CRF morphological tagger.")
    parser.add_argument("--model", default="crf-morphological-analyzer/hf_data/model.mod")
    parser.add_argument("--test-file", default="crf-morphological-analyzer/hf_data/test.txt")
    parser.add_argument("--fst", default="GrischunGuessing.fst")
    parser.add_argument("--template", default=None)
    parser.add_argument("--metadata", default=None)
    args = parser.parse_args()

    evaluate(args.model, args.test_file, args.fst, args.template, args.metadata)
