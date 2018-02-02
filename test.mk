
# make rules for regression tests

# coverage tests with dardin wikipedia items

manual-files+= crf-morphological-analyzer/train/dardin-tagged-with-lemma.txt

test/coverage/dardin-tagged-with-lemma-types.tsv: $(manual-files)
	sort -u $+ |grep -P '\+' | grep -vP '\+Prop'> $@
	
	
test/coverage/dardin-tagged-with-lemma-types.fn.tsv: test/coverage/dardin-tagged-with-lemma-types.tsv Grischun.fst
	python lib/test_fsm.py Grischun.fst  -q -m coverage $< > $@


test-coverage-target: test/coverage/dardin-tagged-with-lemma-types.fn.tsv

test/special/pledari_verb_presind_1p_sg.txt.out.tsv: test/special/pledari_verb_presind_1p_sg.txt Grischun.fst
	python lib/test_fsm.py Grischun.fst -i Adj+Noun+Adv+Interj+Prep+Rom+Num  -I Apo+Pron+2P+3P+Pron+Inf+PastPart+Gerund+Cond+Pl $<  2> $@.log | sort -k3 > $@

test/coverage/unanalyzed/ch-law-uniq-words-unknown.tsv: test/coverage/unanalyzed/ch-law-uniq-words.txt
	flookup Grischun.fst < $< | grep -P "\+\?" | perl -lne 's/\s+\+\?//; print' | grep -v -P '(^\d+\S*|^\w\.|^[A-Z-][A-Z-]+.*|.*["^].*)$$' > $@



test/adj/adj-e-fem-pos.txt.out: test/adj/adj-e-fem-pos.txt
	flookup fstbinaries/Adjective.fst < $< |grep -P '\+\?' > $@

test/adj/adj-ic.txt.out: test/adj/adj-ic.txt
	flookup fstbinaries/Adjective.fst < $< |grep -P '\+\?' > $@

test/adj/adj-al.txt.out: test/adj/adj-al.txt
	flookup fstbinaries/Adjective.fst < $< |grep -P '\+\?' > $@

test/adj/adj-iv.txt.out: test/adj/adj-iv.txt
	flookup fstbinaries/Adjective.fst < $< |grep -P '\+\?' > $@
test/adj/adj-us.txt.out: test/adj/adj-us.txt
	flookup fstbinaries/Adjective.fst < $< |grep -P '\+\?' > $@
test/adj/adj-nt.txt.out: test/adj/adj-nt.txt
	flookup fstbinaries/Adjective.fst < $< |grep -P '\+\?' > $@
test/adj/adj-in.txt.out: test/adj/adj-in.txt
	flookup fstbinaries/Adjective.fst < $< |grep -P '\+\?' > $@


check-redundancy-noun:
	flookup fstbinaries/Noun.fst < wordlists/noun-masc-plur.txt | python lib/check_plur_sing_doubles.py -m M 2> test/noun/noun-masc-plur-antilemma-new.txt.log | sort -u > test/noun/noun-masc-plur-antilemma-new.txt
	flookup fstbinaries/Noun.fst < wordlists/noun-fem-plur.txt | python lib/check_plur_sing_doubles.py -m F 2> test/noun/noun-fem-plur-antilemma-new.txt.log  | sort -u > test/noun/noun-fem-plur-antilemma-new.txt


## apply antilemmas
apply-noun-masc-plur:
	comm -13 <(sort -u test/noun/noun-masc-plur-antilemma.txt) <(sort -u wordlists/noun-masc-plur.txt) | sort -u > wordlists/noun-masc-plur.txt.new ; mv wordlists/noun-masc-plur.txt.new  wordlists/noun-masc-plur.txt
## apply antilemmas
apply-noun-fem-plur:
	comm -13 <(sort -u test/noun/noun-fem-plur-antilemma.txt) <(sort -u wordlists/noun-fem-plur.txt) |sort -u > wordlists/noun-fem-plur.txt.new ; mv wordlists/noun-fem-plur.txt.new  wordlists/noun-fem-plur.txt


SHELL:=/bin/bash
