# Tokenization Issues and Discrepancies in Romansh Morphology

This document records known tokenization discrepancies between the runtime Python tokenizer (`app.py`, `pipeline.py`, `gradio_analyzer.py`) and the gold annotated datasets (`hf_export/all/` / `crf-morphological-analyzer/train/`), distinguishing issues that have been systematically improved from legacy corpus issues that will **not** be resolved at runtime.

---

## 1. Summary of Tokenizer Evaluation

Evaluation of the Python tokenizer against all **10,348 gold tokens** across the 487 sentences in the standardized Romansh dataset:

| State | Sentences Discrepant | Percentage | Notes |
|---|---|---|---|
| **Baseline Tokenizer** | 87 / 487 | 17.9% | Baseline before compound, ordinal, and abbreviation rules |
| **Refined Tokenizer** | 41 / 487 | 8.4% | After compound preservation, abbreviations, units, ordinals, symbols |
| **Remaining Discrepancies** | 41 / 487 | 8.4% | **All** remaining cases are gold corpus flaws or deliberately separated units |

---

## 2. Issues Implemented & Improved in the Runtime Tokenizer

The following patterns have been incorporated into the runtime tokenizer regex and pre-processing:

1. **Proclitic Apostrophes (`d'`, `l'`, `s'`, `n'`, `m'`, `t'`, `ch'`, `qu'`)**:
   - Both ASCII `'` and typographical apostrophes (`’`, `‘`, `ʼ`) followed by letters are split so the proclitic retains the apostrophe:
     - `d'officitad` $\rightarrow$ `['d\'', 'officitad']`
     - `l’onn` $\rightarrow$ `['l’', 'onn']`
     - `ch’el` $\rightarrow$ `['ch’', 'el']`
2. **Hyphenated Compounds & Proper Surnames**:
   - Hyphenated words are preserved as single tokens:
     - Placenames & surnames: `Widmer-Schlumpf`, `Breil-vitg`, `Breil-Schlans`, `Vendsyssel-Thy`, `Georg-August`, `Ruprecht-Karl`, `Friedrich-Schiller`.
     - Compound nouns: `chasa-pravenda`, `plaiv-mamma`, `chor-baselgia`, `chaura-capricorn`, `barba-chaura`, `Mini-ABC`, `chewing-gum`, `vis-à-vis`.
3. **Romansh Ordinals with Numeric Prefixes**:
   - Patterns matching `\d+(?:avel|avla|avels|avlas)` are kept intact:
     - `19avel`, `20avel`, `16avel`.
4. **Standard Abbreviations & Initialisms**:
   - Common single-word and multi-period abbreviations preserve their periods without splitting or triggering false sentence boundaries:
     - `ca.`, `dr.`, `prof.`, `etc.`, `usw.`, `resp.`, `lic.`, `euv.`, `LR.`, `S.`, `C.`.
     - Multi-period abbreviations: `a.C.` (avant Cristus), `s.C.` (suenter Cristus), `s.m.` (sur mar).
5. **Units of Measurement**:
   - Units with powers: `km2`, `m2`, `m3`, `cm3`.
   - Temperature: `°C`.
6. **Time Specifications**:
   - Timestamps like `10:50` or `3:13` are kept intact rather than split into numbers and colons.
7. **Punctuation & Editorial / Mathematical Symbols**:
   - Preserved rather than dropped: `/`, `=`, `%`, `§`, `*`, `†`, `…`, `—`, `–`.

---

## 3. Unresolved Discrepancies (Will NOT be "Fixed" in Runtime Tokenizer)

The remaining ~40 sentence discrepancies in the gold corpora represent historical transcription artifacts, corpus errors, or deliberate linguistic design decisions. They should **not** be altered in the runtime tokenizer:

### 3.1 Historical Gold Transcription Errors: Unsplit Punctuation
In several early news and Wikipedia TSV files, punctuation was accidentally left attached to words during manual annotation:
- **Attached Question Marks**: `onns?`, `café?`, `trapla?`, `test?`, `vardad?`, `num?`.
- **Attached Exclamation Marks**: `Maria!`, `prontas!`, `mort!`, `you!`.
- **Attached Semicolons & Colons**: `marcants;`, `fils;`, `adina:`.
- **Attached Terminal Periods**: `citads.`, `pajais.`, `minutas.`, `10.50.`, `226.`.
- **Attached Quotes**: `«millenni»`, `1919–1969»`, `zutger…»`.

*Decision*: The runtime tokenizer correctly separates punctuation into independent tokens (`['onns', '?']`, `['Maria', '!']`, `['«', 'millenni', '»']`). We do **not** mimic the gold corpus's unsplit punctuation.

### 3.2 Legacy Annotations Flagged with `#PROBLEM: Tokenizer`
In `crf-morphological-analyzer/train/rmquotidiana/*.tsv`, forms where an enclitic subject pronoun was attached to a conjunction or verb were tagged with an explicit comment `#PROBLEM: Tokenizer`:
- `ch’jau` (for *ch'jau* / *che jau*)
- `avev’jau` (for *aveva jau*)
- `er’jau` (for *era jau*)

*Decision*: The runtime tokenizer splits these into `['ch’', 'jau']` and `['avev’', 'jau']`. This separation is linguistically correct. The gold dataset contains these historical flaws because changing them would break backwards compatibility with the pre-compiled Wapiti training alignments.

### 3.3 Slash-Separated Alternatives & Date Spans
- Examples in gold: `Danis/Tavanasa`, `december/schaner`, `Melcher/Pult`, `1893/94`, `1895/96`.
- Gold treated these as single strings, whereas standard NLP tokenization separates the slash delimiter: `['Danis', '/', 'Tavanasa']`.

*Decision*: The runtime tokenizer separates tokens by `/`. Joining arbitrary words across slashes into compound tokens creates infinite out-of-vocabulary combinations that fail FST analysis.

### 3.4 Foreign English Contractions
- Examples in gold: `I’ll` (treated as a single token in an English quote).
- Runtime tokenizer: Proclitic apostrophe rule splits after `I’`: `['I’', 'll']`.

*Decision*: Romansh morphological processing does not maintain English contraction rules.

### 3.5 Full Stop in Complex Expressions (`Expo.01.`, `28.01.2018`)
- In `Expo.01.` or `28.01.2018`, periods within dates or exhibition brand names are tokenized according to standard punctuation rules unless explicitly enumerated in domain gazetteers.

---

## 4. Maintenance Recommendation

When preparing future versions (v2.0+) of the Romansh POS benchmark:
1. Normalize the gold `.tsv` files to separate attached punctuation (`onns?` $\rightarrow$ `onns` + `?`).
2. Resolve `#PROBLEM: Tokenizer` items into proclitic/verb + enclitic pronoun tokens.
3. Retrain the Wapiti CRF model on the cleaned gold corpus so that training data and runtime tokenization achieve 100% mutual alignment.
