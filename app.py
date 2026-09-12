"""
Hugging Face Space Application for Romansh Morphology
Provides:
1. Morphological Disambiguator (FST candidate generation + Wapiti CRF sequence disambiguation)
2. Morphological Candidate Analyzer (all licensed FST readings)
3. Surface Form Generator (generator.fst)
4. About, Resource Versions & Architecture

All lexical data aligns with Pledari Grond (Lia Rumantscha).
"""

import json
import os
import re
import shutil
import subprocess
import tarfile
import gradio as gr

# Try importing native foma C-binding
try:
    import foma
    FOMA_AVAILABLE = True
except ImportError:
    FOMA_AVAILABLE = False


# Resource versions and metadata
RESOURCE_VERSIONS = {
    "app_version": "1.2.0",
    "dataset_repo": "simon-clmtd/romansh-grischun-morphological-corpus",
    "dataset_sha": "93e0ad7620e699a2587113bcd3782e451508a9ba",
    "foma_version": "0.10.0 (Flookup/Foma C-API)",
    "wapiti_version": "1.5.0 (L-BFGS CRF Engine)",
    "fst_analyzer": "GrischunGuessing.fst (Rumantsch Grischun Lexicon + Guesser)",
    "fst_generator": "fstbinaries/generator.fst (Inverted Paradigm Transducer)",
    "crf_model": "data/model.mod (Trained on HF Hub Corpus with early stopping)",
    "crf_template": "crf-morphological-analyzer/templates/rumantsch-template.txt",
    "license": "CC BY-SA 4.0",
    "institutions": "Department of Computational Linguistics, University of Zurich & Lia Rumantscha"
}


def ensure_wapiti_binary():
    """Ensure wapiti executable is compiled and available in PATH or ./wapiti"""
    if shutil.which("wapiti"):
        return "wapiti"
    local_wapiti = os.path.abspath("./wapiti")
    if os.path.exists(local_wapiti) and os.access(local_wapiti, os.X_OK):
        return local_wapiti

    tar_path = "wapiti_src.tar.gz"
    if os.path.exists(tar_path):
        try:
            print("Compiling Wapiti from bundled source archive...")
            build_dir = "/tmp/wapiti_build"
            os.makedirs(build_dir, exist_ok=True)
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(path=build_dir)
            
            # Run make inside build directory
            subprocess.run(["make", "-j2"], cwd=build_dir, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            built_bin = os.path.join(build_dir, "wapiti")
            if os.path.exists(built_bin):
                shutil.copy(built_bin, local_wapiti)
                os.chmod(local_wapiti, 0o755)
                print(f"Successfully compiled and placed wapiti at {local_wapiti}")
                return local_wapiti
        except Exception as e:
            print(f"Failed to compile wapiti from source: {e}")

    return None


class MorphologyService:
    def __init__(self):
        self.analyzer_path = "GrischunGuessing.fst"
        self.generator_path = "fstbinaries/generator.fst"
        self.crf_model_path = "data/model.mod"
        
        self.analyzer_fst = None
        self.generator_fst = None
        self.use_flookup = False
        self.wapiti_bin = ensure_wapiti_binary()
        
        self.setup_fst()

    def setup_fst(self):
        if FOMA_AVAILABLE:
            try:
                if os.path.exists(self.analyzer_path):
                    self.analyzer_fst = foma.FST.load(self.analyzer_path)
                if os.path.exists(self.generator_path):
                    self.generator_fst = foma.FST.load(self.generator_path)
            except Exception as e:
                print(f"Native foma load warning: {e}. Falling back to flookup subprocess.")
                self.use_flookup = True
        else:
            self.use_flookup = True

    def analyze_word_raw(self, word: str):
        """Produce all morphologically licensed candidate analyses for a word"""
        if self.analyzer_fst is not None and not self.use_flookup:
            try:
                res = list(self.analyzer_fst.apply_up(word))
                if not res and word != word.lower():
                    res = list(self.analyzer_fst.apply_up(word.lower()))
                return res
            except Exception:
                pass

        try:
            p = subprocess.Popen(
                ["flookup", "-x", self.analyzer_path],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            out, _ = p.communicate(input=f"{word}\n")
            lines = [l.split("\t")[-1].strip() for l in out.strip().split("\n") if "\t" in l]
            valid = [l for l in lines if l != "+?"]
            if not valid and word != word.lower():
                p2 = subprocess.Popen(
                    ["flookup", "-x", self.analyzer_path],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                out2, _ = p2.communicate(input=f"{word.lower()}\n")
                lines2 = [l.split("\t")[-1].strip() for l in out2.strip().split("\n") if "\t" in l]
                valid = [l for l in lines2 if l != "+?"]
            return valid if valid else ["+?"]
        except Exception as e:
            return [f"+? (Error: {e})"]

    def generate_form(self, analysis_str: str):
        """Generate inflected surface form(s) from analysis string using generator.fst"""
        analysis_str = analysis_str.strip()
        if not analysis_str:
            return []

        if self.generator_fst is not None and not self.use_flookup:
            try:
                res = list(self.generator_fst.apply_up(analysis_str))
                surfaces = [r.split("+", 1)[0] for r in res]
                return sorted(list(set(surfaces)))
            except Exception:
                pass

        try:
            p = subprocess.Popen(
                ["flookup", "-x", self.generator_path],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            out, _ = p.communicate(input=f"{analysis_str}\n")
            lines = [l.split("\t")[-1].strip() for l in out.strip().split("\n") if "\t" in l]
            surfaces = [l.split("+", 1)[0] for l in lines if l != "+?"]
            return sorted(list(set(surfaces)))
        except Exception:
            return []

    @staticmethod
    def tokenize(text: str):
        """Tokenize text into sentences and tokens respecting apostrophes and punctuation"""
        token_pattern = r"""
            (?:[A-Za-zÀ-ÿ]+(?:'[A-Za-zÀ-ÿ]*)?)|
            (?:[0-9]+)|
            (?:[.!?;:,„"'"'()]+)
        """
        lines = text.split("\n")
        sentences = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            toks = re.findall(token_pattern, line, re.VERBOSE)
            toks = [t.strip() for t in toks if t.strip()]
            if toks:
                # Simple sentence boundary splitting on terminal punctuation
                curr_sent = []
                for t in toks:
                    curr_sent.append(t)
                    if t in [".", "!", "?", ";"]:
                        sentences.append(curr_sent)
                        curr_sent = []
                if curr_sent:
                    sentences.append(curr_sent)
        return sentences

    def disambiguate_sentence(self, tokens):
        """Disambiguate sentence tokens by intersecting CRF n-best predictions with FST candidates"""
        if not tokens:
            return []

        # If Wapiti is not available, fallback to first FST candidate
        if not self.wapiti_bin or not os.path.exists(self.crf_model_path):
            results = []
            for tok in tokens:
                cands = self.analyze_word_raw(tok)
                first_cand = cands[0] if cands and cands != ["+?"] else tok + "+?"
                lemma = first_cand.split("+", 1)[0] if "+" in first_cand else tok
                tag = "+" + first_cand.split("+", 1)[1] if "+" in first_cand else "+?"
                others = cands[1:] if len(cands) > 1 else []
                results.append({
                    "Token": tok,
                    "Selected Lemma": lemma,
                    "Disambiguated Analysis": tag,
                    "Confidence": "N/A",
                    "Disambiguation Method": "FST Heuristic Fallback (Wapiti Unavailable)",
                    "Other Filtered Candidates": ", ".join(others) if others else "None"
                })
            return results

        # Run wapiti label
        input_str = "\n".join(tokens) + "\n"
        cmd = [self.wapiti_bin, "label", "-m", self.crf_model_path, "-n", "3", "-p", "-s"]
        try:
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = p.communicate(input=input_str)
        except Exception as e:
            stdout = ""

        blocks = stdout.strip().split("\n\n")
        parsed_nbest = []
        for block in blocks:
            lines = [l for l in block.strip().split("\n") if not l.startswith('#') and not l.startswith('*')]
            sent_preds = []
            for l in lines:
                parts = l.split('\t')
                if len(parts) >= 2:
                    tok = parts[0]
                    pred_tag = parts[1]
                    score_str = parts[2] if len(parts) >= 3 else "1.0/1.0"
                    try:
                        score = eval(score_str.split('/')[1]) if '/' in score_str else float(score_str)
                    except Exception:
                        score = 1.0
                    sent_preds.append((tok, pred_tag, score))
            if sent_preds:
                parsed_nbest.append(sent_preds)

        results = []
        for i, tok in enumerate(tokens):
            cands = self.analyze_word_raw(tok)
            fst_tags = set()
            cand_map = {}
            for c in cands:
                if "+" in c:
                    tag = "+" + c.split("+", 1)[1]
                    fst_tags.add(tag)
                    cand_map[tag] = c

            selected_tag = None
            selected_lemma = None
            source = "CRF Fallback"
            prob = 0.0

            for rank_idx, rank_preds in enumerate(parsed_nbest):
                if i < len(rank_preds):
                    _, p_tag, p_score = rank_preds[i]
                    if rank_idx == 0:
                        prob = p_score
                    if p_tag in fst_tags:
                        selected_tag = p_tag
                        selected_lemma = cand_map[p_tag].split("+", 1)[0]
                        source = "FST-Licensed (CRF Rank 1)" if rank_idx == 0 else f"FST-Licensed (CRF Rank {rank_idx+1})"
                        prob = p_score
                        break
                    # Subset feature match
                    p_feats = set(p_tag.split('+')[1:])
                    matched = False
                    for f_tag, f_cand in cand_map.items():
                        f_feats = set(f_tag.split('+')[1:])
                        if p_feats.issubset(f_feats):
                            selected_tag = f_tag
                            selected_lemma = f_cand.split("+", 1)[0]
                            source = "FST Candidate (Feature Match)"
                            prob = p_score
                            matched = True
                            break
                    if matched:
                        break

            if selected_tag is None:
                if parsed_nbest and i < len(parsed_nbest[0]):
                    selected_tag = parsed_nbest[0][i][1]
                    prob = parsed_nbest[0][i][2]
                else:
                    selected_tag = "+?"
                selected_lemma = tok

            other_cands = [c for c in cands if not (selected_tag and selected_tag in c)]
            results.append({
                "Token": tok,
                "Selected Lemma": selected_lemma,
                "Selected Analysis": selected_tag,
                "Model Confidence": f"{prob*100:.1f}%" if prob > 0 else "N/A",
                "Selection Method": source,
                "Alternative Analyses": ", ".join(other_cands) if other_cands else "None"
            })
        return results


service = MorphologyService()


# ----------------------------------------------------------------------
# Gradio Handlers
# ----------------------------------------------------------------------

def run_disambiguation(text: str):
    if not text or not text.strip():
        return [], "Please enter Romansh text to disambiguate."

    sentences = service.tokenize(text)
    headers = ["Token", "Selected Lemma", "Selected Analysis", "Model Confidence", "Selection Method", "Alternative Analyses"]
    all_rows = []
    total_tokens = 0
    for sent in sentences:
        dict_rows = service.disambiguate_sentence(sent)
        for r in dict_rows:
            all_rows.append([r[h] for h in headers])
        total_tokens += len(sent)

    status_msg = f"Disambiguated {len(sentences)} sentence(s) with {total_tokens} total token(s)."
    return all_rows, status_msg



def run_raw_analysis(text: str):
    if not text or not text.strip():
        return "Please enter Romansh text to inspect candidate analyses."

    sentences = service.tokenize(text)
    output_blocks = []
    token_counter = 0

    for sent in sentences:
        for token in sent:
            token_counter += 1
            candidates = service.analyze_word_raw(token)
            block = [f"=== Token {token_counter}: {token} ==="]
            if not candidates or candidates == ["+?"]:
                block.append("  (No licensed analysis found: +?)")
            else:
                for idx, cand in enumerate(candidates, 1):
                    marker = " [Guessed Stem]" if "+UNKNOWN" in cand else ""
                    block.append(f"  {idx}. {cand}{marker}")
            output_blocks.append("\n".join(block))
        output_blocks.append("")  # Sentence separator

    return "\n\n".join(output_blocks).strip()


def run_generation(analysis_input: str):
    if not analysis_input or not analysis_input.strip():
        return "Please provide an analysis string (e.g. chantar+Verb+PresInd+1P+Sg)."

    analysis_input = analysis_input.strip()
    surfaces = service.generate_form(analysis_input)

    if not surfaces:
        return f"No surface form generated for:\n  {analysis_input}\n\nPlease verify that the lemma and tags match the system tagset."

    lines = [f"Input Analysis: {analysis_input}", "Generated Surface Form(s):"]
    for s in surfaces:
        lines.append(f"  • {s}")
    return "\n".join(lines)


# ----------------------------------------------------------------------
# UI Layout
# ----------------------------------------------------------------------
custom_css = """
.container { max-width: 1040px; margin: auto; }
.output-box { font-family: monospace; font-size: 0.95rem; }
.table-box { font-size: 0.95rem; }
"""

with gr.Blocks(title="Rumantsch Grischun Morphology", css=custom_css) as demo:
    gr.Markdown(
        f"""
        # 🏔️ Rumantsch Grischun Morphology & Disambiguation
        **Finite-State Morphological Pipeline with CRF Disambiguation for Rumantsch Grischun (ISO 639-3: `roh`)**  
        *Department of Computational Linguistics (Text Technology Group), University of Zurich & Lia Rumantscha — Version {RESOURCE_VERSIONS['app_version']}*
        """
    )

    with gr.Tabs():
        # TAB 1: Disambiguated Analysis (Primary)
        with gr.TabItem("Morphological Disambiguator"):
            gr.Markdown(
                """
                ### Contextual Morphological Disambiguation

                The finite-state analyzer first produces the possible morphological analyses for each word. Because many word forms are ambiguous, a statistical sequence model (Wapiti CRF) then uses the surrounding words to choose the analysis that best fits the sentence context.

                The selected analysis gives the lemma and morphological features of the word. Alternative analyses proposed by the finite-state analyzer remain available for inspection.

                When possible, the system selects among analyses licensed by the finite-state morphology. For words that cannot be analyzed by the finite-state system, the statistical model can provide a fallback prediction.
                """
            )
            with gr.Row():
                with gr.Column(scale=4):
                    dis_input = gr.Textbox(
                        label="Romansh Input Text",
                        lines=4,
                        value="La vulp era puspè ina giada fomentada. Qua ha ella vis in corv che tegneva in toc chaschiel."
                    )
                    dis_btn = gr.Button("Disambiguate Text", variant="primary")

                    gr.Examples(
                        examples=[
                            ["La vulp era puspè ina giada fomentada."],
                            ["Qua ha ella vis in corv che tegneva in toc chaschiel."],
                            ["Ils uffants giugavan en il prau."],
                            ["Nus eschan or da chasa per ir a scola."],
                            ["Las novas tecnologias furneschan soluziuns innovativas per l'ambient."],
                        ],
                        inputs=[dis_input]
                    )

            dis_status = gr.Markdown("")
            dis_table = gr.Dataframe(
                headers=["Token", "Selected Lemma", "Selected Analysis", "Model Confidence", "Selection Method", "Alternative Analyses"],
                datatype=["str", "str", "str", "str", "str", "str"],
                wrap=True,
                elem_classes=["table-box"]
            )

            with gr.Accordion("ℹ️ Guide: How Morphological Disambiguation Works", open=False):
                gr.Markdown(
                    """
                    #### Result Columns
                    - **Token**: The word form as it occurs in the input text.
                    - **Selected Lemma**: The dictionary or citation form associated with the selected analysis.
                    - **Selected Analysis**: The morphological analysis selected in context. For example, `esser + Verb + ImpInd + 3P + Sg` means *esser*, verb, imperfect indicative, third person singular.
                    - **Model Confidence**: How strongly the statistical sequence model favors the selected analysis in this context. This is useful for identifying uncertain decisions, but it should not be interpreted as a probability that the analysis is linguistically correct.
                    - **Selection Method**: How the final analysis was obtained:
                      - **`FST-Licensed (CRF Rank 1)`**: The contextual model’s preferred analysis is also licensed by the finite-state morphology.
                      - **`FST-Licensed (CRF Rank 2/3)`**: The model’s first choice was incompatible with the finite-state analyses, so the best higher-ranked licensed analysis was selected.
                      - **`FST Candidate (Feature Match)`**: An FST analysis was selected because its main morphological features agree with the statistical prediction, although there was no exact match.
                      - **`CRF Fallback`**: The finite-state analyzer provided no suitable analysis, so the result comes from the statistical sequence model alone.
                    - **Alternative Analyses**: Other morphological analyses produced by the finite-state analyzer for this word form but not selected in the current sentence.

                    #### Concrete Example: *La vulp era puspè ina giada fomentada.*
                    In isolation, *era* has several possible analyses, including the noun *era* ("garden bed"), the adverb *era* ("also"), and forms of the verb *esser*. In this sentence, the contextual model selects `esser + Verb + ImpInd + 3P + Sg` (*"was"*). The alternative analyses remain visible in the final column so that the disambiguation decision can be inspected.
                    """
                )

            with gr.Accordion("📖 Quick Guide: How to Read the Morphological Tags", open=False):
                gr.Markdown(
                    """
                    The analyzer uses Xerox/Foma-style feature tags prefixed with `+`. Common elements:

                    | Category | Tag Examples | Meaning |
                    |---|---|---|
                    | **Part of Speech** | `+Noun`, `+Verb`, `+Adj`, `+Adv`, `+Art`, `+Pron`, `+Prep`, `+Conj`, `+Subj`, `+Num`, `+Prop` | Primary syntactic category |
                    | **Gender** | `+Masc`, `+Fem`, `+MF` | Masculine, Feminine, Invariant/Either |
                    | **Number** | `+Sg`, `+Pl` | Singular, Plural |
                    | **Person** | `+1P`, `+2P`, `+3P` | First, Second, Third person |
                    | **Verb Tense & Mood** | `+PresInd`, `+ImpInd`, `+PastPart`, `+Inf`, `+Gerund`, `+Con`, `+Cond`, `+Impv` | Present Indicative, Imperfect, Past Participle, Infinitive, Gerund, Subjunctive/Conjunctive, Conditional, Imperative |
                    | **Pronoun Type** | `+Pers`, `+Poss`, `+Dem`, `+Indef`, `+Rel`, `+Refl`, `+Interrog` | Personal, Possessive, Demonstrative, Indefinite, Relative, Reflexive, Interrogative |
                    | **Case / Function** | `+Nom`, `+Acc`, `+Dat`, `+AccDat`, `+Aton`, `+Ton` | Nominative, Accusative, Dative, Weak/Atonic, Stressed/Tonic |
                    | **Orthography** | `+Apo`, `*` prefix | Elided with apostrophe (e.g. *l'*, *d'*), Capitalized surface form |

                    *(See the **Versions & Architecture** tab for full linguistic documentation and references).*
                    """
                )

            dis_btn.click(fn=run_disambiguation, inputs=[dis_input], outputs=[dis_table, dis_status])



        # TAB 2: Candidate Analyzer (Raw FST)
        with gr.TabItem("Candidate Explorer (Raw FST)"):
            gr.Markdown(
                """
                ### All Morphologically Licensed Readings
                Inspect all candidate analyses produced by `GrischunGuessing.fst` prior to sequence disambiguation.
                """
            )
            with gr.Row():
                with gr.Column():
                    raw_input = gr.Textbox(
                        label="Romansh Input Text",
                        lines=4,
                        value="La vulp era puspè ina giada fomentada."
                    )
                    raw_btn = gr.Button("Explore Candidates", variant="primary")
                with gr.Column():
                    raw_output = gr.Textbox(
                        label="All Licensed Morphological Analyses",
                        lines=14,
                        elem_classes=["output-box"]
                    )

            raw_btn.click(fn=run_raw_analysis, inputs=[raw_input], outputs=[raw_output])

        # TAB 3: Generator
        with gr.TabItem("Morphological Generator"):
            gr.Markdown(
                """
                ### Surface Form Generation
                Generate inflected surface form(s) from a Lemma and Feature Specification (`generator.fst`).
                """
            )
            with gr.Row():
                with gr.Column():
                    gen_input = gr.Textbox(
                        label="Lexical Analysis String",
                        placeholder="chantar+Verb+PresInd+1P+Sg",
                        lines=2,
                        value="chantar+Verb+PresInd+1P+Sg"
                    )
                    gen_btn = gr.Button("Generate Surface Form", variant="primary")

                    gr.Examples(
                        examples=[
                            ["chantar+Verb+PresInd+1P+Sg"],
                            ["chantar+Verb+PresInd+3P+Pl"],
                            ["chantar+Verb+Gerund"],
                            ["chantar+Verb+PastPart+Masc+Sg"],
                            ["vulp+Noun+Fem+Pl"],
                            ["chaschiel+Noun+Masc+Sg"],
                            ["grischun+Adj+Fem+Sg"],
                            ["bel+Adj+Fem+Sg"],
                        ],
                        inputs=[gen_input]
                    )

                with gr.Column():
                    gen_output = gr.Textbox(
                        label="Generated Surface Result",
                        lines=8,
                        elem_classes=["output-box"]
                    )

            gen_btn.click(fn=run_generation, inputs=[gen_input], outputs=[gen_output])

        # TAB 4: Resource Versions & Architecture
        with gr.TabItem("Versions & Architecture"):
            gr.Markdown(
                f"""
                ### Resource Versions & System Provenance

                | Resource / Component | Specification / Version | Link / Reference |
                |---|---|---|
                | **Application Version** | `v{RESOURCE_VERSIONS['app_version']}` | Hugging Face Spaces |
                | **Dataset Repository** | `{RESOURCE_VERSIONS['dataset_repo']}` | [Dataset on Hub](https://huggingface.co/datasets/{RESOURCE_VERSIONS['dataset_repo']}) |
                | **Dataset Commit SHA** | `{RESOURCE_VERSIONS['dataset_sha']}` | Verified benchmark split |
                | **Morphological Analyzer** | `{RESOURCE_VERSIONS['fst_analyzer']}` | Foma / XFST binary |
                | **Surface Generator** | `{RESOURCE_VERSIONS['fst_generator']}` | Inverted transducer |
                | **CRF Disambiguator** | `{RESOURCE_VERSIONS['wapiti_version']}` | Wapiti L-BFGS Engine |
                | **Trained CRF Model** | `{RESOURCE_VERSIONS['crf_model']}` | 89.56% full tag acc, 91.40% POS acc |
                | **Feature Template** | `{RESOURCE_VERSIONS['crf_template']}` | Affixes, context & orthography patterns |
                | **Primary Lexicon** | Pledari Grond (Lia Rumantscha) | [pledarigrond.ch](https://pledarigrond.ch) |
                | **License** | `{RESOURCE_VERSIONS['license']}` | Creative Commons Attribution-ShareAlike 4.0 |

                ---

                #### Two-Stage Architecture
                1. **Candidate Generation**:
                   - Two-level finite-state transducers (`GrischunGuessing.fst`) analyze tokens into all possible `<Lemma>+<POS>+<Features>` readings.
                   - Regular inflectional paradigms are augmented with guessing rules for unseen stems (`[Guessed Stem]`).
                2. **Sequence Disambiguation**:
                   - A Conditional Random Field (CRF) trained with Wapiti predicts the sequence probability distribution over morphosyntactic tags.
                   - The system ranks and filters the FST candidate space using the CRF posterior probabilities, guaranteeing that selected readings remain morphologically valid.

                #### Authors & Institutional Affiliation
                - Developed at the **Department of Computational Linguistics (Text Technology Group), University of Zurich (UZH)**:
                  Simon Clematide, Reto Baumgartner, Martina Bachmann, Rolf Badat, Daniel Hegglin, Susanna Tron, Melanie Widmer, Nora Lötscher, Noëmi Aepli, Martin Cantieni, Victoria Mosca.
                - Lexical data and grammatical cooperation: **Lia Rumantscha**.
                """
            )

if __name__ == "__main__":
    demo.launch()

