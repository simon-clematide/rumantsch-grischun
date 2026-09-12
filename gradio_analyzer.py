import gradio as gr
import os
import re

# Try to import foma (preferred) or pyfoma (fallback)
FOMA_AVAILABLE = False
PYFOMA_AVAILABLE = False

try:
    import foma
    FOMA_AVAILABLE = True
except ImportError:
    try:
        from pyfoma import FST
        PYFOMA_AVAILABLE = True
    except ImportError:
        pass


class RumantschMorphAnalyzer:
    def __init__(self):
        self.fst_path = os.path.join('GrischunGuessing.fst')
        self.transducer = None
        self.engine_type = None  # 'foma' or 'pyfoma'
        self.setup_complete = False
        self.error_message = ""
        self.setup_analyzer()
    
    def setup_analyzer(self):
        """Load FST using native foma or pyfoma fallback"""
        if not (FOMA_AVAILABLE or PYFOMA_AVAILABLE):
            self.error_message = "Neither foma nor pyfoma library is available"
            print("Neither foma nor pyfoma library is available")
            return
            
        if not os.path.exists(self.fst_path):
            self.error_message = f"FST file not found at {self.fst_path}"
            print(f"✗ FST file not found at {self.fst_path}")
            return
        
        # Check file size
        file_size = os.path.getsize(self.fst_path)
        print(f"FST file size: {file_size} bytes")
        
        # 1. Try native foma C-binding (recommended)
        if FOMA_AVAILABLE:
            try:
                print("Loading FST using native foma.FST.load()...")
                self.transducer = foma.FST.load(self.fst_path)
                self.engine_type = "foma"
                self.setup_complete = True
                print("✓ Successfully loaded FST via native foma engine")
                return
            except Exception as e:
                print(f"Native foma load failed, trying pyfoma fallback: {e}")

        # 2. Try pyfoma fallback
        if PYFOMA_AVAILABLE:
            try:
                print("Loading foma format file using pyfoma FST.load_foma()...")
                fst_dict = FST.load_foma(self.fst_path)
                if fst_dict:
                    fst_name = list(fst_dict.keys())[0]
                    self.transducer = fst_dict[fst_name]
                    self.engine_type = "pyfoma"
                    self.setup_complete = True
                    print(f"✓ Successfully loaded FST '{fst_name}' via pyfoma")
                else:
                    self.error_message = "No FSTs found in file"
            except Exception as e:
                self.error_message = f"Failed to load foma file: {e}"
                print(f"✗ Error loading FST: {e}")
    
    def tokenize_text(self, text):
        """Tokenization for Romansh respecting apostrophes, compounds, and punctuation"""
        text = text.replace('\r', '')
        text = re.sub(r"\b([A-Za-zÀ-ÿ]+['’‘ʼ])(?=[A-Za-zÀ-ÿ])", r"\1 ", text)

        tokens = []
        token_pattern = r'''
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
        '''
        
        for line in text.split('\n'):
            line = line.strip()
            if line:
                line_tokens = re.findall(token_pattern, line, re.VERBOSE)
                for token in line_tokens:
                    if token.strip():
                        tokens.append(token.strip())
                tokens.append('LINEBREAK')
        
        return [t for t in tokens if t]
    
    def analyze_word(self, word):
        """Analyze a single word using the FST"""
        if not self.setup_complete or self.transducer is None:
            return [f"{word}\t+? (FST not available)"]
        
        analyses = []
        
        try:
            if self.engine_type == "foma":
                # Native foma uses apply_up (surface -> analysis)
                results = list(self.transducer.apply_up(word))
                if not results and word != word.lower():
                    results = list(self.transducer.apply_up(word.lower()))
                for result in results:
                    analyses.append(f"{word}\t{result}")
            else:
                # pyfoma fallback
                # Try analyze first (surface to analysis)
                results = list(self.transducer.analyze(word))
                
                if results:
                    for result in results:
                        if result and result != word:
                            analyses.append(f"{word}\t{result}")
                
                # If no results with analyze, try generate (might be reversed)
                if not analyses:
                    generate_results = list(self.transducer.generate(word))
                    if generate_results:
                        for result in generate_results:
                            if result and result != word:
                                analyses.append(f"{word}\t{result} (via generate)")
                
                # If still no results, try lowercase
                if not analyses and word != word.lower():
                    lower_results = list(self.transducer.analyze(word.lower()))
                    if lower_results:
                        for result in lower_results:
                            if result and result != word.lower():
                                analyses.append(f"{word}\t{result}")
                    
                    # Also try generate with lowercase
                    if not analyses:
                        lower_gen_results = list(self.transducer.generate(word.lower()))
                        if lower_gen_results:
                            for result in lower_gen_results:
                                if result and result != word.lower():
                                    analyses.append(f"{word}\t{result} (via generate)")
            
            # If still no results, word is not in FST
            if not analyses:
                analyses.append(f"{word}\t+?")
                
        except Exception as e:
            analyses.append(f"{word}\t+? (error: {str(e)})")
            import traceback
            print(f"Error analyzing '{word}': {traceback.format_exc()}")
        
        return analyses
    
    def analyze_text(self, text):
        """Analyze complete text"""
        if not text or len(text.strip()) == 0:
            return "Please enter some text to analyze."
        
        if len(text) > 10000:
            return "Sorry, input is limited to 10,000 characters!"
        
        if not self.setup_complete:
            error_info = f"Error: FST transducer not loaded.\n"
            if self.error_message:
                error_info += f"Details: {self.error_message}\n"
            error_info += "\nPossible solutions:\n"
            error_info += "1. Check that GrischunGuessing.fst is a valid gzipped foma file\n"
            error_info += "2. Verify the file is not corrupted\n"
            error_info += "3. Ensure pyfoma is installed correctly"
            return error_info
        
        tokens = self.tokenize_text(text)
        results = []
        
        for token in tokens:
            if token == 'LINEBREAK':
                results.append('')  # Empty line for sentence breaks
            else:
                word_analyses = self.analyze_word(token)
                
                # Format output: show word and all its analyses
                result_lines = [f"=== {token} ==="]
                for i, analysis in enumerate(word_analyses, 1):
                    # Extract just the morphological analysis part
                    if '\t' in analysis:
                        word_part, morph_part = analysis.split('\t', 1)
                        result_lines.append(f"  {i}. {morph_part}")
                    else:
                        result_lines.append(f"  {i}. {analysis}")
                
                results.append('\n'.join(result_lines))
        
        return '\n\n'.join(results)

# Initialize analyzer
analyzer = RumantschMorphAnalyzer()

def analyze_wrapper(text):
    return analyzer.analyze_text(text)

def get_system_info():
    """Show system information"""
    info = []
    info.append(f"Engine: {analyzer.engine_type or 'None'}")
    info.append(f"foma Available: {FOMA_AVAILABLE} | pyfoma Available: {PYFOMA_AVAILABLE}")
    
    if analyzer.setup_complete:
        info.append("✓ FST transducer loaded and ready")
        try:
            if analyzer.engine_type == "foma":
                # foma.FST string representation includes states, transitions, etc.
                fst_summary = str(analyzer.transducer).strip().split('\n')
                for line in fst_summary[:4]:
                    info.append(f"  {line}")
                test_results = list(analyzer.transducer.apply_up("vulp"))
                info.append(f"Test apply_up('vulp'): {test_results}")
            else:
                if hasattr(analyzer.transducer, 'states'):
                    state_count = len(analyzer.transducer.states) if analyzer.transducer.states else 0
                    info.append(f"FST state count: {state_count}")
        except Exception as e:
            info.append(f"Info note: {e}")
    elif analyzer.error_message:
        info.append(f"✗ Error: {analyzer.error_message}")
    else:
        info.append("✗ FST transducer not loaded")
    
    fst_exists = os.path.exists(analyzer.fst_path)
    info.append(f"FST file exists: {fst_exists}")
    
    if fst_exists:
        try:
            file_size = os.path.getsize(analyzer.fst_path)
            info.append(f"FST file size: {file_size} bytes")
            info.append("File format: Gzipped foma net")
        except Exception as e:
            info.append(f"Error reading file: {e}")
    
    return "\n".join(info)

# Create Gradio interface
with gr.Blocks(title="Rumantsch FST Morphological Analyzer") as demo:
    gr.Markdown("# Rumantsch Morphological Analyzer")
    gr.Markdown("**pyfoma-powered FST Analysis** - Uses pyfoma finite state transducer for morphological analysis")
    
    with gr.Row():
        with gr.Column(scale=1):
            input_text = gr.Textbox(
                label="Input Text (Romansh)",
                placeholder="Enter Romansh text...",
                lines=6,
                value="La vulp era puspè ina giada fomentada."
            )
            analyze_btn = gr.Button("Analyze with FST", variant="primary")
            
            # System status
            gr.Textbox(
                label="System Status",
                value=get_system_info(),
                lines=4,
                interactive=False
            )
            
        with gr.Column(scale=1):
            output_text = gr.Textbox(
                label="FST Morphological Analyses",
                lines=15,
                interactive=False,
                placeholder="FST analyses will appear here..."
            )
    
    analyze_btn.click(
        fn=analyze_wrapper,
        inputs=input_text,
        outputs=output_text
    )
    
    with gr.Row():
        gr.Examples(
            examples=[
                ["La vulp era puspè ina giada fomentada."],
                ["Qua ha ella vis in corv che tegneva in toc chaschiel."],
                ["Ils uffants giugavan en il garden."],
                ["Nus eschan or da chasa per ir a scola."],
                ["Ti es bel e forta."],
                ["Jeu am la natira grischuna."]
            ],
            inputs=input_text,
            label="Example Sentences"
        )
    
    with gr.Accordion("About FST Analysis", open=False):
        gr.Markdown("""
        ### Finite State Transducer Analysis
        
        This analyzer uses a **pyfoma finite state transducer (FST)** built specifically for Romansh morphology.
        The FST contains:
        
        - **Complete lexicon** of Romansh words
        - **Morphological rules** for inflection and derivation  
        - **Analysis tags** showing grammatical features
        
        ### Output Format
        Each word shows all possible morphological analyses from the FST.
        Words not found in the FST are marked with **+?**
        
        ### FST File
        Uses: `GrischunGuessing.fst`
        
        This FST includes both known words and unknown word guessing patterns
        for comprehensive coverage of Romansh morphology.
        """)
    
    with gr.Accordion("Technical Requirements", open=False):
        gr.Markdown("""
        ### Dependencies
        - **pyfoma Python library**: `pip install git+https://github.com/mhulden/pyfoma.git`
        - **FST file**: `GrischunGuessing.fst` (gzipped foma format)
        
        ### Installation
        ```bash
        pip install git+https://github.com/mhulden/pyfoma.git
        pip install gradio
        ```
        
        ### FST File Format
        The analyzer uses `load_foma()` from pyfoma 2 which automatically handles:
        - **Gzipped foma files**: Standard format with `.fst` extension
        - **Plain text foma files**: Uncompressed foma format
        
        The foma format starts with `##foma-net` and contains FST data.
        Multiple FSTs in one file are supported (first one is used).
        
        ### About pyfoma 2
        pyfoma 2 includes native support for loading foma-format files created
        by the foma command-line tools using the `load_foma()` function.
        """)
    
    gr.Markdown("---")
    gr.Markdown("*pyfoma-based morphological analysis for Romansh*")

if __name__ == "__main__":
    demo.launch()
