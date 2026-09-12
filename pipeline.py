#!/usr/bin/env python3
"""
Rumantsch Grischun Morphological Processing Pipeline
Integrates:
1. Tokenizer (Romansh orthographic rules, elisions, punctuation)
2. FST Morphological Analyzer (GrischunGuessing.fst -> Candidate set)
3. Sequence Disambiguator Interface (BaseDisambiguator)
4. Wapiti CRF Implementation (WapitiDisambiguator)
"""

import os
import re
import subprocess
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

try:
    import foma
    FOMA_AVAILABLE = True
except ImportError:
    FOMA_AVAILABLE = False


class BaseDisambiguator(ABC):
    """
    Abstract interface for morphological sequence disambiguation.
    Enforces FST constraints: selects or ranks among candidates licensed by the FST.
    """
    @abstractmethod
    def disambiguate(
        self,
        tokens: List[str],
        candidate_analyses: List[List[str]]
    ) -> List[Dict[str, Any]]:
        pass


class WapitiDisambiguator(BaseDisambiguator):
    """
    Wapiti CRF implementation of the sequence disambiguator.
    Ranks and filters candidates using Wapiti sequence labeling.
    """
    def __init__(self, model_path: str = "crf-morphological-analyzer/train/trainall.txt.mod", n_best: int = 5):
        self.model_path = model_path
        self.n_best = n_best
        self.available = os.path.exists(self.model_path) and self._check_wapiti()

    @staticmethod
    def _check_wapiti() -> bool:
        try:
            res = subprocess.run(["wapiti"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            return False

    def disambiguate(
        self,
        tokens: List[str],
        candidate_analyses: List[List[str]]
    ) -> List[Dict[str, Any]]:
        if not tokens:
            return []

        if not self.available:
            # Fallback: choose first candidate
            return [
                {
                    "surface": t,
                    "selected": cands[0] if cands else "+?",
                    "confidence": 1.0 if cands else 0.0,
                    "fst_candidates": cands,
                    "is_in_fst": bool(cands),
                    "model": "first_candidate_fallback"
                }
                for t, cands in zip(tokens, candidate_analyses)
            ]

        # Prepare input for wapiti: one token per line, followed by blank line
        input_text = "\n".join(tokens) + "\n\n"
        cmd = ["wapiti", "label", "-m", self.model_path, "-n", str(self.n_best), "-p", "-s"]

        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = proc.communicate(input=input_text)
        except Exception as e:
            return [
                {"surface": t, "selected": cands[0] if cands else "+?", "confidence": 0.0, "fst_candidates": cands, "is_in_fst": bool(cands), "error": str(e)}
                for t, cands in zip(tokens, candidate_analyses)
            ]

        # Parse only the first sequence prediction (# 0 ...)
        # Format:
        # # 0 <seq_score>
        # Token \t BestTag \t BestTag/prob
        token_lines = []
        in_first_seq = False
        for line in stdout.split("\n"):
            line = line.strip()
            if line.startswith("# 0"):
                in_first_seq = True
                continue
            elif line.startswith("# ") or line.startswith("*"):
                if in_first_seq:
                    break
                continue
            if in_first_seq and line:
                parts = line.split("\t")
                if len(parts) >= 2:
                    token_lines.append(parts)

        token_results: List[Dict[str, Any]] = []
        for idx, token in enumerate(tokens):
            cands = candidate_analyses[idx] if idx < len(candidate_analyses) else []
            crf_parts = token_lines[idx] if idx < len(token_lines) else [token, ""]
            crf_best = crf_parts[1]
            prob = 0.0
            if len(crf_parts) > 2 and "/" in crf_parts[2]:
                try:
                    prob = float(crf_parts[2].rsplit("/", 1)[1])
                except ValueError:
                    pass

            # Match CRF tag against FST candidates
            selected_cand = None
            for c in cands:
                c_clean = c.lstrip("*")
                if c.endswith(crf_best) or c_clean.endswith(crf_best):
                    selected_cand = c
                    break

            # Fallback 1: match primary POS category
            if not selected_cand and cands and "+" in crf_best:
                primary = crf_best.split("+")[1]
                for c in cands:
                    if f"+{primary}" in c:
                        selected_cand = c
                        break

            # Fallback 2: take first candidate
            if not selected_cand and cands:
                selected_cand = cands[0]

            token_results.append({
                "surface": token,
                "selected": selected_cand if selected_cand else "+?",
                "confidence": prob,
                "crf_tag": crf_best,
                "fst_candidates": cands,
                "is_in_fst": selected_cand in cands
            })

        return token_results


class MorphologicalPipeline:
    def __init__(
        self,
        fst_path: str = "GrischunGuessing.fst",
        disambiguator: Optional[BaseDisambiguator] = None
    ):
        self.fst_path = fst_path
        self.fst = foma.FST.load(fst_path) if FOMA_AVAILABLE and os.path.exists(fst_path) else None
        self.disambiguator = disambiguator or WapitiDisambiguator()

    def tokenize(self, text: str) -> List[List[str]]:
        """Splits text into sentences of tokens."""
        text = re.sub(r"\b([A-Za-zÀ-ÿ]+['’‘ʼ])(?=[A-Za-zÀ-ÿ])", r"\1 ", text)

        token_pattern = r"""
            (?:\b(?:ca|dr|prof|etc|usw|resp|euv|lic|LR|S|C)\.)| # Selected common abbreviations with trailing dot
            (?:\b(?:[a-zA-Z]\.){2,})|                           # Multi-period abbrevs like a.C., s.C., s.m.
            (?:\b\d{1,2}:\d{2}\b)|                              # Timestamps like 10:50, 3:13
            (?:\b[A-Za-zÀ-ÿ]+(?:-[A-Za-zÀ-ÿ]+)+\b)|              # Hyphenated compounds: Widmer-Schlumpf, vis-à-vis, chor-baselgia
            (?:\b\d+(?:avel|avla|avels|avlas)\b)|               # Ordinals: 19avel, 20avel
            (?:(?:km|m|cm|mm)[23]\b)|                           # Units with square/cube: km2, m3
            (?:°C\b)|                                           # Degrees Celsius
            (?:\b[A-Za-zÀ-ÿ]+['’‘ʼ]?)|                          # Normal words with optional trailing apostrophe
            (?:\b\d+\b)|                                        # Numbers
            (?:[«»""„“‘’‹›])|                                 # Quotes
            (?:[.!?;:,()\[\]{}—–\-/=%*†…])                     # Punctuation & math/editorial symbols
        """
        sentences = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            toks = [m.strip() for m in re.findall(token_pattern, line, re.VERBOSE) if m.strip()]
            if toks:
                curr_sent = []
                for t in toks:
                    curr_sent.append(t)
                    if t in [".", "!", "?", ";"]:
                        sentences.append(curr_sent)
                        curr_sent = []
                if curr_sent:
                    sentences.append(curr_sent)
        return sentences

    def analyze_tokens(self, tokens: List[str]) -> List[List[str]]:
        """Stage 1: Finite-State Candidate Analysis"""
        all_cands = []
        for t in tokens:
            if self.fst is not None:
                cands = list(self.fst.apply_up(t))
                if not cands and t != t.lower():
                    cands = list(self.fst.apply_up(t.lower()))
            else:
                p = subprocess.Popen(["flookup", "-x", self.fst_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
                out, _ = p.communicate(input=f"{t}\n")
                cands = [l.split("\t")[-1].strip() for l in out.strip().split("\n") if "\t" in l and l.split("\t")[-1].strip() != "+?"]
            all_cands.append(cands)
        return all_cands

    def process_sentence(self, tokens: List[str]) -> List[Dict[str, Any]]:
        """Complete Two-Stage Processing: FST Analysis + Disambiguation"""
        candidates = self.analyze_tokens(tokens)
        return self.disambiguator.disambiguate(tokens, candidates)


if __name__ == "__main__":
    pipeline = MorphologicalPipeline()
    test_sent = "La vulp era puspè ina giada fomentada .".split()
    print("Input sentence:", " ".join(test_sent))
    res = pipeline.process_sentence(test_sent)
    print("\nProcessed tokens:")
    for r in res:
        print(f"  {r['surface']:<12} -> {r['selected']:<35} (Score: {r['confidence']:.2f}, Candidates: {len(r['fst_candidates'])})")
