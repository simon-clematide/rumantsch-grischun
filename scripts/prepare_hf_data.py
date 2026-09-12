#!/usr/bin/env python3
"""
Fetch dataset splits from Hugging Face Hub and format them for Wapiti CRF training/evaluation.

Output format (Wapiti input):
<Token>\t<MorphTag>
(one token per line, sentences separated by empty line)

Also saves a metadata JSON file (hf_metadata.json) recording the dataset repository,
commit SHA, configuration, and preparation timestamp for reproducible reporting.

Usage:
    python scripts/prepare_hf_data.py --output-dir crf-morphological-analyzer/hf_data
"""

import argparse
import datetime
import json
import os
import sys
from huggingface_hub import HfApi, hf_hub_download


def fetch_and_convert(repo_id: str, config: str, split: str, output_path: str):
    print(f"Fetching {config}/{split}.jsonl from {repo_id}...", file=sys.stderr)
    try:
        downloaded_file = hf_hub_download(
            repo_id=repo_id,
            filename=f"{config}/{split}.jsonl",
            repo_type="dataset",
        )
    except Exception as e:
        print(f"Error downloading {config}/{split}.jsonl: {e}", file=sys.stderr)
        raise

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    sent_count = 0
    token_count = 0
    repaired_tags = 0

    with open(downloaded_file, "r", encoding="utf-8") as fin, open(output_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            tokens = item.get("tokens", [])
            morph_tags = item.get("morph_tags", [])

            if len(tokens) != len(morph_tags):
                print(f"Warning: sentence length mismatch ({len(tokens)} vs {len(morph_tags)}) in {item.get('id')}", file=sys.stderr)
                continue

            for tok, tag in zip(tokens, morph_tags):
                tag_clean = tag.replace("+Typo", "").replace("+Lingo", "").strip()
                # If tag is empty in gold dataset (e.g. unannotated token), supply fallback
                if not tag_clean:
                    if tok.lower() == "ni":
                        tag_clean = "+Conj"
                    else:
                        tag_clean = "+?"
                    repaired_tags += 1
                fout.write(f"{tok}\t{tag_clean}\n")
                token_count += 1

            fout.write("\n")
            sent_count += 1

    print(f"Wrote {sent_count} sentences, {token_count} tokens (repaired {repaired_tags} empty tags) to {output_path}", file=sys.stderr)
    return sent_count, token_count


def get_dataset_metadata(repo_id: str):
    try:
        api = HfApi()
        info = api.dataset_info(repo_id)
        return {
            "repo_id": repo_id,
            "commit_sha": info.sha,
            "last_modified": str(info.last_modified),
        }
    except Exception as e:
        print(f"Notice: could not query dataset info via API: {e}", file=sys.stderr)
        return {
            "repo_id": repo_id,
            "commit_sha": "unknown",
            "last_modified": "unknown",
        }


def main():
    parser = argparse.ArgumentParser(description="Download and format dataset from Hugging Face for Wapiti CRF.")
    parser.add_argument(
        "--repo-id",
        default="simon-clmtd/romansh-grischun-morphological-corpus",
        help="Hugging Face Dataset repo ID (default: simon-clmtd/romansh-grischun-morphological-corpus)",
    )
    parser.add_argument(
        "--config",
        default="all",
        help="Dataset configuration/subset (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        default="crf-morphological-analyzer/hf_data",
        help="Directory to save converted files (default: crf-morphological-analyzer/hf_data)",
    )

    args = parser.parse_args()

    meta = get_dataset_metadata(args.repo_id)
    meta["config"] = args.config
    meta["prepared_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    meta["splits"] = {}

    for split in ["train", "validation", "test"]:
        out_file = os.path.join(args.output_dir, f"{split}.txt")
        sc, tc = fetch_and_convert(args.repo_id, args.config, split, out_file)
        meta["splits"][split] = {"sentences": sc, "tokens": tc}

    meta_file = os.path.join(args.output_dir, "dataset_metadata.json")
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"Saved dataset metadata (SHA: {meta['commit_sha']}) to {meta_file}", file=sys.stderr)
    print("HF data preparation complete!", file=sys.stderr)


if __name__ == "__main__":
    main()
