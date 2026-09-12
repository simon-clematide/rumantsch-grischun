#!/usr/bin/env python3
"""
Evaluation Harness for Rumantsch Grischun Morphological Processing Pipeline.
Evaluates:
1. FST Token Coverage (% tokens with >= 1 analysis)
2. FST Curated Lexicon Coverage (% tokens without +UNKNOWN)
3. FST Ambiguity Rate (mean candidates per token)
4. FST Oracle Recall (% tokens where gold tag is present among FST candidates)
5. Disambiguator Primary POS Accuracy
6. Disambiguator Full Morphological Tag Accuracy
"""

import argparse
import glob
import os
import re
import sys
from typing import Dict, List, Tuple

# Ensure current dir is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pipeline import MorphologicalPipeline, WapitiDisambiguator


POS_CATEGORIES = [
    "Abbr", "Adj", "Adv", "Art", "Conj", "Dig", "Initial", "Interj",
    "Let", "Noun", "Num", "Prep", "Pron", "Prop", "Prt", "Punc",
    "PUNCT", "Rom", "Subj", "Verb", "Sent", "CM"
]


def load_gold_corpus(filepath: str) -> List[List[Tuple[str, str, str]]]:
    """Loads a gold TSV file returning list of sentences: [(token, lemma, full_tag), ...]"""
    sentences = []
    current_sent = []

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                if current_sent:
                    sentences.append(current_sent)
                    current_sent = []
                continue

            parts = line.split("\t")
            token = parts[0].strip()
            lemma = parts[1].strip() if len(parts) > 1 else ""
            tag = parts[2].strip() if len(parts) > 2 else (parts[1].strip() if len(parts) == 2 else "")

            # Strip problem notes
            if "#" in tag:
                tag = tag.split("#", 1)[0].strip()

            current_sent.append((token, lemma, tag))

        if current_sent:
            sentences.append(current_sent)

    return sentences


def extract_primary_pos(tag_or_cand: str) -> str:
    """Extracts primary POS tag, e.g. '+Verb' from 'chantar+Verb+PresInd+3P+Sg' or '+Verb+PresInd'"""
    for pos in POS_CATEGORIES:
        if f"+{pos}" in tag_or_cand:
            return f"+{pos}"
    return ""


def evaluate_corpus(name: str, sentences: List[List[Tuple[str, str, str]]], pipeline: MorphologicalPipeline):
    total_tokens = 0
    covered_tokens = 0
    known_tokens = 0
    total_candidates = 0
    gold_in_candidates = 0
    correct_pos = 0
    correct_full = 0

    for sent in sentences:
        tokens = [item[0] for item in sent]
        gold_tags = [item[2] for item in sent]

        processed = pipeline.process_sentence(tokens)

        for item, gold_tag in zip(processed, gold_tags):
            total_tokens += 1
            cands = item["fst_candidates"]
            total_candidates += len(cands)

            if cands and cands != ["+?"]:
                covered_tokens += 1
                if any("+UNKNOWN" not in c for c in cands):
                    known_tokens += 1

            gold_clean = gold_tag.lstrip("*")
            gold_pos = extract_primary_pos(gold_clean)

            # Oracle Recall: Is gold tag present in FST candidate set?
            has_gold = False
            for c in cands:
                c_clean = c.lstrip("*")
                if c.endswith(gold_tag) or c_clean.endswith(gold_clean) or c == gold_tag or c_clean == gold_clean:
                    has_gold = True
                    break
            if has_gold:
                gold_in_candidates += 1

            # Disambiguator evaluation
            pred_selected = item["selected"]
            pred_clean = pred_selected.lstrip("*")
            pred_pos = extract_primary_pos(pred_clean)

            if pred_pos and gold_pos and pred_pos == gold_pos:
                correct_pos += 1

            if (
                pred_selected == gold_tag
                or pred_clean.endswith(gold_clean)
                or pred_selected.endswith(gold_tag)
                or pred_clean == gold_clean
            ):
                correct_full += 1

    mean_cands = total_candidates / total_tokens if total_tokens else 0.0
    cov_pct = (covered_tokens / total_tokens * 100) if total_tokens else 0.0
    known_pct = (known_tokens / total_tokens * 100) if total_tokens else 0.0
    recall_pct = (gold_in_candidates / total_tokens * 100) if total_tokens else 0.0
    pos_acc = (correct_pos / total_tokens * 100) if total_tokens else 0.0
    full_acc = (correct_full / total_tokens * 100) if total_tokens else 0.0

    print(f"\n=======================================================")
    print(f"  Evaluation Report: {name.upper()}")
    print(f"=======================================================")
    print(f"  Total Sentences          : {len(sentences):>8}")
    print(f"  Total Tokens             : {total_tokens:>8}")
    print(f"-------------------------------------------------------")
    print(f"  FST Token Coverage       : {cov_pct:>7.2f}% ({covered_tokens}/{total_tokens})")
    print(f"  FST Curated Lexicon Cov. : {known_pct:>7.2f}% ({known_tokens}/{total_tokens})")
    print(f"  FST Ambiguity Rate       : {mean_cands:>7.2f} candidates/token")
    print(f"  FST Oracle Candidate Rec.: {recall_pct:>7.2f}% ({gold_in_candidates}/{total_tokens})")
    print(f"-------------------------------------------------------")
    print(f"  Disambiguator POS Acc.   : {pos_acc:>7.2f}% ({correct_pos}/{total_tokens})")
    print(f"  Disambiguator Full Acc.  : {full_acc:>7.2f}% ({correct_full}/{total_tokens})")
    print(f"=======================================================")


def main():
    parser = argparse.ArgumentParser(description="Evaluate Rumantsch morphological pipeline.")
    parser.add_argument("--corpus", default="all", choices=["dardin", "rtr", "all"], help="Corpus to evaluate")
    args = parser.parse_args()

    pipeline = MorphologicalPipeline()

    test_files = {
        "dardin": ["crf-morphological-analyzer/train/dardin.tsv"],
        "rtr": ["crf-morphological-analyzer/train/rtr.tsv"],
    }

    if args.corpus in test_files:
        files = test_files[args.corpus]
        sents = []
        for f in files:
            sents.extend(load_gold_corpus(f))
        evaluate_corpus(args.corpus, sents, pipeline)
    else:
        for cname, files in test_files.items():
            sents = []
            for f in files:
                sents.extend(load_gold_corpus(f))
            evaluate_corpus(cname, sents, pipeline)


if __name__ == "__main__":
    main()
