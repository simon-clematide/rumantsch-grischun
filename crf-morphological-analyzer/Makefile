

#####################################################################
# THREADS: user-settable make variable
#
# Number of threads wapiti uses while training (option -p
# THREADS). Set this to the number of available cores for most
# efficient training.
#####################################################################
THREADS?=4


#####################################################################
# TEMPLATE: user-settable make variable
#
# The location of wapiti's pattern file for training (relative to this
# makefile).
#####################################################################

TEMPLATE?=templates/rumantsch-template.txt


#####################################################################
# JOBSIZE: user-settable make variable
#
# Number of segments used by wapiti in one batch of a thread.
#####################################################################

JOBSIZE?=40



#####################################################################
# TRAIN: full training file for wapiti
#
# Built from different training files and separate test file.
#####################################################################
TRAIN:=train/trainall.txt

EVALTRAIN+=train/quotidiana-done-no-lemma.txt
EVALTRAIN+=train/train-misc-no-lemma.txt
EVALTRAIN+=train/dardin-no-lemma.txt

EVALTEST:=train/wiki-dino-no-lemma.txt

train-tsv-files+=$(EVALTRAIN:-no-lemma.txt=.tsv)
train-tsv-files+=$(EVALTEST:-no-lemma.txt=.tsv)

%-no-lemma.txt: %.tsv
	perl -lne 'chomp; s/\s+/\t/; s{^(\S+)\t(\S+)\t(\S+).*}{$$1\t$$3}; print;' <  $< > $@
# remove the lemmas for training
#train/dardin-no-lemma.txt: train/dardin.tsv
#	cut -f 1,3 $< > $@
# remove the lemmas for training
#train/wiki-dino-no-lemma.txt: train/wiki-dino.tsv
#	cut -f 1,3 $< > $@

# Separate lemma from morphological features
#train/dardin-tagged-with-lemma.tsv: train/dardin-tagged-with-lemma.txt
#	perl -F"\t" -lane 's/(^\S+)\t([^+]*)(.*)/\1\t\2\t\3/g;print' < $< > $@


#train/train-misc-no-lemma.txt: train/train-misc.tsv
#	cut -f 1,3 $< > $@

train/quotidiana-done.tsv:train/rmquotidiana/done.txt
	cd $(<D) && cat -s $$(cat $(<F))  > $(abspath $@)
	
#train/quotidiana-done-no-lemma.txt: train/quotidiana-done.tsv
#	cut -f 1,3 $< > $@

# build the full training set for evaluation
$(TRAIN): $(EVALTRAIN) $(EVALTEST)
	perl -lne 's/\+(Lingo|Typo)//g; print;' $+ > $@


EVALMODEL:=$(EVALTRAIN).mod

RMTEMP:=touch

### Evaluate using 10-fold cross-validation
# Test folds are specified, devset folds are derived from them
FOLDS?= 1 2 3 4 5 6 7 8 9 10
TPL:=$(basename $(notdir $(TEMPLATE)))
CVDATA_OUT:= $(TPL)_cv.d
cvdata-out-files:=$(foreach f, $(FOLDS), $(CVDATA_OUT)/train_$f.tsv)
cvdata-out-files:=$(foreach f, $(FOLDS), $(CVDATA_OUT)/test_$f.tsv)
cvdata-out-files+=$(foreach f, $(FOLDS), $(CVDATA_OUT)/train_$f.mod)
#cvdata-out-files+=$(foreach f, $(FOLDS), $(CVDATA_OUT)/test_$f.eval.tsv)



#####################################################################
# eval-target:
#
# Do a full cross-validation and evaluation round.
#####################################################################

eval-target: $(cvdata-out-files) $(CVDATA_OUT).eval.tsv


$(CVDATA_OUT)/train_%.tsv $(CVDATA_OUT)/test_%.tsv $(CVDATA_OUT)/dev_%.tsv $(CVDATA_OUT)/train_%.mod: $(TRAIN)
	mkdir -p $(CVDATA_OUT) && \
	bash lib/linize.bash < $< | sort -R --random-source=$<  > $(CVDATA_OUT)/$(notdir $(TRAIN)).unverticalized
	perl lib/split-train-test.perl -cont 10/$* -nthd  -dv $(CVDATA_OUT)/dev_$*.txtv -tr $(CVDATA_OUT)/train_$*.txtv -te $(CVDATA_OUT)/test_$*.txtv  $(CVDATA_OUT)/$(notdir $(TRAIN)).unverticalized
	for f in $(CVDATA_OUT)/dev_$*.txtv  $(CVDATA_OUT)/train_$*.txtv  $(CVDATA_OUT)/test_$*.txtv ; do perl -ne ';s/\x0B/\n/g; print '<  $$f > $${f%v} ; done && $(RMTEMP) $(CVDATA_OUT)/*.txtv
	nice wapiti train -i $(JOBSIZE) -p $(TEMPLATE) -t 12 -d $(CVDATA_OUT)/dev_$*.txt $(CVDATA_OUT)/train_$*.txt > $(CVDATA_OUT)/train_$*.mod 2> $(CVDATA_OUT)/train_$*.mod.err
	nice wapiti label -m $(CVDATA_OUT)/train_$*.mod -c $(CVDATA_OUT)/test_$*.txt > $(CVDATA_OUT)/test$*.mod.eval 2> $(CVDATA_OUT)/test$*.eval.err


$(CVDATA_OUT).eval.tsv: $(foreach f, $(FOLDS), $(CVDATA_OUT)/train_$f.mod)
	lib/wapiti_cv_eval.py $(CVDATA_OUT)/test*.eval.err >> $@


### Produce the final model


MODEL:=$(TRAIN).mod
$(MODEL): $(TRAIN)
	bash lib/randomize_sequences.bash < $< > $<.random
	perl lib/split-train-test.perl -cont 10/1 -tr $<.random.train -te $<.random.dev $<.random
	nice wapiti train -p $(TEMPLATE) -t $(THREADS) -d $<.random.dev $<.random.train > $(MODEL) || rm -f $@

final: $(MODEL)



# General rule for non-existing directories
%.d:
	mkdir -p $@

# Quality assurance	
include qa.mk

include learn.mk
SHELL:=/bin/bash


