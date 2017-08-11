# Final usable networks

# XFST=foma make build # create version with foma
# Default xfst

XFST?=foma


ifeq ($(XFST),hfst-xfst)
XFSTCMD:=hfst-xfst -f foma -F
else ifeq ($(XFST),foma)
XFSTCMD:=foma -f
else ifeq ($(XFST),xfst)
XFSTCMD:=xfst -f
endif

build: Grischun.fst GrischunGuessing.fst cgi-bin/data/GrischunGuessing.fst 

cgi: cgi-bin/data/crf-morphpos-model cgi-bin/tools/analyse.py

world: build cgi

clean:
	rm -f fstbinaries/*.fst Grischun.fst GrischunGuessing.fst


Grischun.fst GrischunGuessing.fst : collection-RG.xfst \
 fstbinaries/Adverb.fst \
 fstbinaries/Adjective.fst fstbinaries/AdjectiveGuessing.fst \
 fstbinaries/Noun.fst fstbinaries/NounGuessing.fst \
 fstbinaries/Verb.fst fstbinaries/VerbGuessing.fst \
 fstbinaries/Numeral.fst fstbinaries/Number.fst \
 fstbinaries/OrthoRule.fst \
 fstbinaries/Capitalization.fst \
 particles/conj.lexc \
 particles/interj.lexc \
 particles/interpunct.lexc \
 particles/letter.lexc \
 particles/prep.lexc \
 art-pron/art.lexc \
 art-pron/pron.lexc
	$(XFSTCMD) collection-RG.xfst

# Networks for the major parts of speech
fstbinaries/Adjective.fst fstbinaries/AdjectiveGuessing.fst : adj/adj.xfst \
 adj/adj-irr.lexc \
 adj/adj-comp-irr.lexc \
 wordlists/adj-reg.txt \
 wordlists/adj-e.txt \
 wordlists/adj-part.txt \
 wordlists/adj-inv.txt
	$(XFSTCMD) adj/adj.xfst

fstbinaries/Adverb.fst : adv/adv.xfst \
 wordlists/adj-reg.txt \
 wordlists/adj-e.txt \
 wordlists/adj-inv.txt \
 wordlists/adv-short.txt
	$(XFSTCMD) adv/adv.xfst

fstbinaries/Noun.fst fstbinaries/NounGuessing.fst : noun/noun.xfst \
 noun/noun-irr.lexc \
 wordlists/noun-fem.txt \
 wordlists/noun-fem-plur.txt \
 wordlists/noun-fem-sing.txt \
 wordlists/noun-masc.txt \
 wordlists/noun-masc-plur.txt \
 wordlists/noun-masc-sing.txt \
 wordlists/noun-part.txt \
 wordlists/noun-proper.txt
	$(XFSTCMD) noun/noun.xfst

fstbinaries/Numeral.fst fstbinaries/Number.fst : num/num.xfst
	$(XFSTCMD) num/num.xfst

fstbinaries/Verb.fst fstbinaries/VerbGuessing.fst : verb/verb.xfst \
 verb/verb-irr.lexc \
 verb/verb-vchg.lexc \
 verb/verb-ar-esch-end.lexc \
 verb/verb-ar-end.lexc \
 verb/verb-er-esch-end.lexc \
 verb/verb-er-end.lexc \
 verb/verb-ir-esch-end.lexc \
 verb/verb-ir-end.lexc \
 verb/verb-part-irr.lexc \
 wordlists/verb-air-esch.txt \
 wordlists/verb-air.txt \
 wordlists/verb-ar-esch.txt \
 wordlists/verb-ar.txt \
 wordlists/verb-er-esch.txt \
 wordlists/verb-er.txt \
 wordlists/verb-er2.txt \
 wordlists/verb-ir-esch.txt \
 wordlists/verb-ir.txt
	$(XFSTCMD) verb/verb.xfst

# Orthography
fstbinaries/Capitalization.fst fstbinaries/OrthoRule.fst : spelling/ortho-rule.xfst
	$(XFSTCMD) spelling/ortho-rule.xfst

# cgi-bin
cgi-bin/data/GrischunGuessing.fst: GrischunGuessing.fst
	ln -f $< $@
cgi-bin/data/crf-morphpos-model:crf-morphological-analyzer/train/trainall.txt.mod
	ln -f $< $@
cgi-bin/tools/analyse.py:crf-morphological-analyzer/lib/analyse.py
	mkdir -p $(@D) && ln -f $< $@
	
crf-morphological-analyzer/train/trainall.txt.mod:
	cd crf-morphological-analyzer && make final
