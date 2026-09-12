# Morphological Processing for Rumansh



### Some important links
  * Hugging Face Dataset: [CL-UZH/romansh-grischun-morphological-corpus](https://huggingface.co/datasets/simon-clmtd/romansh-grischun-morphological-corpus)
  * Hugging Face Demo Space: [Romansh Morphology Space](https://huggingface.co/spaces/simon-clmtd/romansh-morphology)
  * git repo: <https://gitlab.cl.uzh.ch/siclemat/rumantsch-morphologie>
  * Pledari Grond online lexicon: <http://pledarigrond.ch/rumantschgrischun>
  * A larger introduction to Romansh: Renzo Caduff, Uorschla N. Caprez und Georges Darms. 2008 *Grammatica d’instrucziun dal rumantsch grischun* <https://doc.rero.ch/record/9712/files/Gramminstr.pdf>
  * A shorter introduction: Lia Rumantscha: *RUMANTSCH GRISCHUN PER RUMANTSCHS* <http://pledarigrond.ch/rumantschgrischun/assets/binary/grammatica.pdf>
  * Open Xerox Italian tag compatibility: <http://open.xerox.com/Services/fst-nlp-tools/Consume/176>
  * Bilingwis with parallel texts on Swiss Laws: [http://kitt.cl.uzh.ch/kitt/bilingwis/](http://kitt.cl.uzh.ch/kitt/bilingwis/?languagepair=derm&lang=de&corpus=slcbilingwis&language=0)

---

## Reproducing the Wapiti CRF Tagger from Hugging Face Data

The morphological disambiguator (Wapiti CRF) can be trained directly and reproducibly on the official standardized dataset hosted on Hugging Face:

```bash
# 1. Download and format train, validation, and test splits from Hugging Face Hub
make hf-data

# 2. Train the Wapiti CRF model using early stopping on the validation split
make hf-train

# 3. Evaluate the trained model on the test split (both raw CRF and FST-constrained)
make hf-eval

# Or run the full end-to-end pipeline in one step:
make hf-all
```

### Evaluation Benchmark on Standard Test Split:
- **CRF Raw Full Morphological Tag Accuracy**: `89.56%`
- **CRF Raw Major POS Accuracy**: `91.30%`
- **FST Lexicon Candidate Coverage**: `83.52%`
- **Combined FST+CRF Disambiguation Accuracy**: `89.15%`
- **Combined FST+CRF Major POS Accuracy**: `91.40%`

You can also customize the dataset configuration, threads, or target subset when invoking make:
```bash
make hf-all HF_CONFIG=quotidiana THREADS=8
```
