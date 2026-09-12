#!/usr/bin/env python3
"""
export_hf_datasets.py — Standardize and export Rumantsch Grischun POS & Morphology datasets
to Hugging Face Hub format (Parquet, JSON Lines, and CoNLL-U).

Features:
- Native Xerox/Foma morphological tags as primary representation.
- Missing lemmas ('???') preserved strictly as null/None in gold layer.
- Derived Universal Dependencies (UPOS and FEATS).
- Multi-configuration support (quotidiana, dardin, wiki_dino, rtr, misc, and all benchmark).
- Standard dataset card generation.
"""

import argparse
import glob
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pyarrow as pa
import pyarrow.parquet as pq

# Mapping from primary Foma tags to Universal Dependencies UPOS

UPOS_MAP = {
    "Noun": "NOUN",
    "Prop": "PROPN",
    "Verb": "VERB",
    "Adj": "ADJ",
    "Adv": "ADV",
    "Art": "DET",
    "Pron": "PRON",
    "Prep": "ADP",
    "Conj": "CCONJ",
    "Subj": "SCONJ",
    "Num": "NUM",
    "Dig": "NUM",
    "Prt": "PART",
    "Interj": "INTJ",
    "Abbr": "NOUN",
    "Initial": "PROPN",
    "Punc": "PUNCT",
    "Sent": "PUNCT",
    "CM": "PUNCT",
    "Let": "SYM",
    "Rom": "NUM",
    "Symbol": "SYM",
    "For": "X",
}


def parse_morph_feats(tags: List[str]) -> Tuple[str, str, Dict[str, str]]:
    """Extracts coarse POS, native primary tag, and decomposed UD FEATS."""
    if not tags:
        return "X", "", {}

    primary_tag = tags[0].split("^")[0]
    upos = UPOS_MAP.get(primary_tag, "X")
    feats: Dict[str, str] = {}

    for t in tags:
        # Gender
        if t == "Fem":
            feats["Gender"] = "Fem"
        elif t == "Masc":
            feats["Gender"] = "Masc"
        elif t == "MF":
            feats["Gender"] = "Masc,Fem"

        # Number
        elif t == "Sg":
            feats["Number"] = "Sing"
        elif t == "Pl":
            feats["Number"] = "Plur"

        # Person
        elif t == "1P":
            feats["Person"] = "1"
        elif t == "2P":
            feats["Person"] = "2"
        elif t == "3P":
            feats["Person"] = "3"

        # Verb Tense / Aspect / Mood / Form
        elif t == "PresInd":
            feats["Tense"] = "Pres"
            feats["Mood"] = "Ind"
            feats["VerbForm"] = "Fin"
        elif t == "ImpInd":
            feats["Tense"] = "Imp"
            feats["Mood"] = "Ind"
            feats["VerbForm"] = "Fin"
        elif t == "PastPart":
            feats["Tense"] = "Past"
            feats["VerbForm"] = "Part"
        elif t == "Inf":
            feats["VerbForm"] = "Inf"
        elif t == "Gerund":
            feats["VerbForm"] = "Ger"
        elif t == "Cond":
            feats["Mood"] = "Cnd"
            feats["VerbForm"] = "Fin"
        elif t == "Con":
            feats["Mood"] = "Sub"
            feats["VerbForm"] = "Fin"
        elif t == "Impv":
            feats["Mood"] = "Imp"
            feats["VerbForm"] = "Fin"

        # Pronoun / Determiner types
        elif t == "Def":
            feats["PronType"] = "Art"
            feats["Definite"] = "Def"
        elif t == "Indef":
            feats["PronType"] = "Art"
            feats["Definite"] = "Ind"
        elif t == "Dem":
            feats["PronType"] = "Dem"
        elif t == "Pers":
            feats["PronType"] = "Prs"
        elif t == "Poss":
            feats["Poss"] = "Yes"
        elif t == "Refl":
            feats["Reflex"] = "Yes"
        elif t == "Rel":
            feats["PronType"] = "Rel"
        elif t == "Interrog":
            feats["PronType"] = "Int"

        # Numeral type
        elif t == "Card":
            feats["NumType"] = "Card"
        elif t == "Ord":
            feats["NumType"] = "Ord"

    return upos, primary_tag, feats


def feats_dict_to_string(feats: Dict[str, str]) -> str:
    """Formats feature dictionary into sorted pipe-delimited CoNLL-U style string."""
    if not feats:
        return "_"
    return "|".join(f"{k}={v}" for k, v in sorted(feats.items()))


def parse_tsv_file(filepath: str, corpus_name: str) -> List[Dict[str, Any]]:
    """Parses a gold TSV file into clean sentence dictionaries."""
    sentences = []
    current_tokens = []
    current_lemmas = []
    current_native_pos = []
    current_morph_tags = []
    current_upos = []
    current_feats = []
    current_notes = []
    current_capitalized = []

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line.strip() or line.startswith("#"):
                if current_tokens:
                    sentences.append({
                        "tokens": current_tokens,
                        "lemmas": current_lemmas,
                        "native_pos": current_native_pos,
                        "morph_tags": current_morph_tags,
                        "upos": current_upos,
                        "feats": current_feats,
                        "is_capitalized": current_capitalized,
                        "notes": current_notes,
                    })
                    (
                        current_tokens,
                        current_lemmas,
                        current_native_pos,
                        current_morph_tags,
                        current_upos,
                        current_feats,
                        current_notes,
                        current_capitalized,
                    ) = [], [], [], [], [], [], [], []
                continue

            parts = line.split("\t")
            token = parts[0].strip()
            raw_lemma = parts[1].strip() if len(parts) > 1 else ""
            raw_tag = parts[2].strip() if len(parts) > 2 else (parts[1].strip() if len(parts) == 2 else "")
            note = parts[3].strip() if len(parts) > 3 else ""

            # Check if tag has attached problem note in column 3
            if " " in raw_tag and ("#PROBLEM" in raw_tag or "#" in raw_tag):
                tag_parts = raw_tag.split("#", 1)
                raw_tag = tag_parts[0].strip()
                note = (note + " #" + tag_parts[1]).strip()

            # Handle lemma normalization: preserve ??? strictly as None in gold layer
            is_cap = raw_lemma.startswith("*")
            lemma = raw_lemma.lstrip("*") if raw_lemma else None
            if lemma == "???" or lemma == "":
                lemma = None

            # Parse tag elements
            tag_tokens = [t for t in raw_tag.split("+") if t]
            upos, native_pos, feats_dict = parse_morph_feats(tag_tokens)
            feats_str = feats_dict_to_string(feats_dict)

            current_tokens.append(token)
            current_lemmas.append(lemma)
            current_native_pos.append("+" + native_pos if native_pos else "")
            current_morph_tags.append(raw_tag)
            current_upos.append(upos)
            current_feats.append(feats_str)
            current_capitalized.append(is_cap)
            current_notes.append(note if note else None)

    if current_tokens:
        sentences.append({
            "tokens": current_tokens,
            "lemmas": current_lemmas,
            "native_pos": current_native_pos,
            "morph_tags": current_morph_tags,
            "upos": current_upos,
            "feats": current_feats,
            "is_capitalized": current_capitalized,
            "notes": current_notes,
        })

    return sentences


def split_sentences(sentences: List[Dict[str, Any]], train_ratio=0.8, val_ratio=0.1) -> Dict[str, List[Dict[str, Any]]]:
    """Deterministic document-preserving sentence split."""
    total = len(sentences)
    if total < 5:
        return {"train": sentences, "validation": [], "test": []}

    n_train = int(total * train_ratio)
    n_val = int(total * val_ratio)
    if n_val == 0 and total >= 3:
        n_val = 1

    return {
        "train": sentences[:n_train],
        "validation": sentences[n_train : n_train + n_val],
        "test": sentences[n_train + n_val :],
    }


def write_conllu(sentences: List[Dict[str, Any]], filepath: Path):
    with open(filepath, "w", encoding="utf-8") as f:
        for s in sentences:
            f.write(f"# sent_id = {s['id']}\n")
            f.write(f"# text = {' '.join(s['tokens'])}\n")
            for i, token in enumerate(s["tokens"], 1):
                lemma = s["lemmas"][i - 1] or "_"
                upos = s["upos"][i - 1]
                xpos = s["morph_tags"][i - 1] or "_"
                feats = s["feats"][i - 1] or "_"
                f.write(f"{i}\t{token}\t{lemma}\t{upos}\t{xpos}\t{feats}\t_\t_\t_\t_\n")
            f.write("\n")


def write_jsonl(sentences: List[Dict[str, Any]], filepath: Path):
    with open(filepath, "w", encoding="utf-8") as f:
        for s in sentences:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")


def write_parquet(sentences: List[Dict[str, Any]], filepath: Path):
    table = pa.Table.from_pylist(sentences)
    pq.write_table(table, filepath)


def generate_dataset_card(export_path: Path, repo_id: str):

    card_content = f"""---
annotations_creators:
- expert-generated
language:
- rm
language_creators:
- found
license: cc-by-sa-4.0
multilinguality:
- monolingual
pretty_name: Romansh Grischun Morphological Corpus
size_categories:
- 10K<n<100K
source_datasets:
- original
tags:
- token-classification
- pos-tagging
- morphological-analysis
- lemmatization
- universal-dependencies
- romansh
- rumantsch-grischun
task_categories:
- token-classification
task_ids:
- part-of-speech
configs:

- config_name: default
  data_files:
  - split: train
    path: all/train.parquet
  - split: validation
    path: all/validation.parquet
  - split: test
    path: all/test.parquet
- config_name: all
  data_files:
  - split: train
    path: all/train.parquet
  - split: validation
    path: all/validation.parquet
  - split: test
    path: all/test.parquet
- config_name: quotidiana
  data_files:
  - split: train
    path: quotidiana/train.parquet
  - split: validation
    path: quotidiana/validation.parquet
  - split: test
    path: quotidiana/test.parquet
- config_name: dardin
  data_files:
  - split: train
    path: dardin/train.parquet
  - split: validation
    path: dardin/validation.parquet
  - split: test
    path: dardin/test.parquet
- config_name: rtr
  data_files:
  - split: train
    path: rtr/train.parquet
  - split: validation
    path: rtr/validation.parquet
  - split: test
    path: rtr/test.parquet
- config_name: wiki_dino
  data_files:
  - split: train
    path: wiki_dino/train.parquet
  - split: validation
    path: wiki_dino/validation.parquet
  - split: test
    path: wiki_dino/test.parquet
- config_name: misc
  data_files:
  - split: train
    path: misc/train.parquet
  - split: validation
    path: misc/validation.parquet
  - split: test
    path: misc/test.parquet
---


# Romansh Grischun Morphological Corpus

A morphologically annotated corpus of Rumantsch Grischun, the standardized written variety of Romansh.

## Dataset Summary
This dataset provides gold-standard morphosyntactically annotated and lemmatized corpora for **Rumantsch Grischun** (standard written Romansh, ISO 639-3: `roh`), a national language of Switzerland.

The primary annotation layer preserves the rich **Xerox/Foma two-level morphological tags** used by the finite-state analyzer and CRF disambiguation pipeline, alongside derived **Universal Dependencies (UD)** UPOS and morphological features (FEATS).

Developed at the **[Department of Computational Linguistics](https://www.cl.uzh.ch)**, University of Zurich (**Text Technology Group**), in collaboration with the **[Lia Rumantscha](https://liarumantscha.ch)** (*Pledari Grond*).

## Configurations & Sub-corpora

| Configuration | Source Genre | Tokens | Sentences | Gold Lemmas? | Description |
|---|---|---|---|---|---|
| `quotidiana` | News journalism | 4,625 | 214 | Yes | 11 articles from the Romansh daily newspaper *La Quotidiana* (1997–2008). |
| `dardin` | Local history | 492 | 32 | Yes | Encyclopedic article on Dardin (Breil/Brigels). Standard literary prose. |
| `rtr` | Political broadcast news | 732 | 44 | Yes | News broadcast transcript regarding cantonal government elections. |
| `wiki_dino` | Science encyclopedia | 504 | 20 | Null (`null` in gold) | Romansh Wikipedia article on dinosaurs. Scientific/taxonomic prose. |
| `misc` | Culture & biographies | 3,995 | 177 | Null (`null` in gold) | Biographical and cultural texts (e.g. Gian Bundi fairy tale collections). |
| `all` | Combined benchmark | 10,348 | 487 | Mixed | Unified multi-genre benchmark. |

## Data Fields

- `id`: Unique sentence identifier (`str`).
- `corpus`: Sub-corpus identifier (`str`).
- `tokens`: List of surface words and punctuation (`List[str]`).
- `lemmas`: List of gold lemmas (`List[Optional[str]]`). Missing lemmas in `wiki_dino` and `misc` are preserved as `None` / `null`.
- `morph_tags`: Exact native Xerox/Foma morphological analysis string (`List[str]`), e.g. `+Verb+PresInd+3P+Sg`.
- `native_pos`: Primary POS category tag (`List[str]`), e.g. `+Verb`.
- `upos`: Universal Dependencies Part-of-Speech tag (`List[str]`), e.g. `VERB`, `NOUN`, `ADJ`.
- `feats`: Universal Dependencies morphological features string (`List[str]`), e.g. `Mood=Ind|Number=Sing|Person=3|Tense=Pres`.
- `is_capitalized`: Boolean flag indicating capitalized surface form (`List[bool]`).
- `notes`: Annotation problem notes and comments where available (`List[Optional[str]]`).

## Citation & Attribution

- **Institution**: Department of Computational Linguistics, University of Zurich (Text Technology Group).
- **Authors**: Simon Clematide, Reto Baumgartner, Martina Bachmann, Rolf Badat, Daniel Hegglin, Susanna Tron, Melanie Widmer, Nora Lötscher, Noëmi Aepli, Martin Cantieni, Victoria Mosca.
- **License**: Creative Commons Attribution-ShareAlike 4.0 International (**CC BY-SA 4.0**).
"""
    with open(export_path / "README.md", "w", encoding="utf-8") as f:
        f.write(card_content)


def main():
    parser = argparse.ArgumentParser(description="Export Rumantsch Grischun POS datasets to HF format.")
    parser.add_argument("--export-dir", type=str, default="./hf_export", help="Directory to export files to.")
    parser.add_argument("--push-to-hub", action="store_true", help="Push dataset to Hugging Face Hub.")
    parser.add_argument("--repo-id", type=str, default="CL-UZH/romansh-grischun-morphological-corpus", help="Target HF repo ID.")
    args = parser.parse_args()

    export_path = Path(args.export_dir)
    export_path.mkdir(parents=True, exist_ok=True)

    base_dir = Path("crf-morphological-analyzer/train")

    corpus_sources = {
        "quotidiana": sorted(glob.glob(str(base_dir / "rmquotidiana" / "*.tsv"))),
        "dardin": [str(base_dir / "dardin.tsv")],
        "wiki_dino": [str(base_dir / "wiki-dino.tsv")],
        "rtr": [str(base_dir / "rtr.tsv")],
        "misc": [str(base_dir / "train-misc.tsv")],
    }

    all_data_by_corpus: Dict[str, List[Dict[str, Any]]] = {}
    master_sentences: List[Dict[str, Any]] = []

    print("=" * 60)
    print("Parsing Rumantsch Grischun POS & Morphological Corpora")
    print("=" * 60)

    for corpus_name, file_paths in corpus_sources.items():
        corpus_sents = []
        for fp in file_paths:
            sents = parse_tsv_file(fp, corpus_name)
            for idx, s in enumerate(sents):
                doc_name = Path(fp).stem
                s["id"] = f"{corpus_name}_{doc_name}_{idx + 1:04d}"
                s["corpus"] = corpus_name
                corpus_sents.append(s)

        all_data_by_corpus[corpus_name] = corpus_sents
        master_sentences.extend(corpus_sents)
        n_toks = sum(len(s["tokens"]) for s in corpus_sents)
        print(f"✓ {corpus_name:15s}: {len(corpus_sents):4d} sentences | {n_toks:5d} tokens")

    all_data_by_corpus["all"] = master_sentences
    total_tokens = sum(len(s["tokens"]) for s in master_sentences)
    print(f"✓ {'all (benchmark)':15s}: {len(master_sentences):4d} sentences | {total_tokens:5d} tokens")
    print("=" * 60)

    # Export each configuration
    for config_name, sents in all_data_by_corpus.items():
        config_dir = export_path / config_name
        config_dir.mkdir(parents=True, exist_ok=True)

        splits = split_sentences(sents)

        for split_name, split_sents in splits.items():
            if not split_sents:
                continue
            jsonl_file = config_dir / f"{split_name}.jsonl"
            conllu_file = config_dir / f"{split_name}.conllu"
            parquet_file = config_dir / f"{split_name}.parquet"

            write_jsonl(split_sents, jsonl_file)
            write_conllu(split_sents, conllu_file)
            write_parquet(split_sents, parquet_file)

        print(f"Exported {config_name:15s} -> {config_dir}")


    generate_dataset_card(export_path, args.repo_id)
    print(f"Generated Dataset Card -> {export_path / 'README.md'}")
    print("\n✓ Local export complete.")

    if args.push_to_hub:
        try:
            from huggingface_hub import HfApi

            print(f"\nPushing dataset to Hugging Face Hub: {args.repo_id}...")
            api = HfApi()
            api.create_repo(repo_id=args.repo_id, repo_type="dataset", exist_ok=True)

            api.upload_folder(
                folder_path=str(export_path),
                repo_id=args.repo_id,
                repo_type="dataset",
                commit_message="Initial release of Romansh Grischun morphological corpus"
            )
            print(f"\n✓ Successfully published to https://huggingface.co/datasets/{args.repo_id}")
        except Exception as e:
            print(f"✗ Failed to push to Hugging Face Hub: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
