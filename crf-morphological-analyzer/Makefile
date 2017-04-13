THREADS?=4
#TEMPLATE?=templates/rumantsch-template.txt
TEMPLATE?=templates/tpl_a.txt
EVALTRAIN:=train/train4500.txt
EVALTEST:=test/dino-corr.txt
EVALMODEL:=$(EVALTRAIN).mod
TRAIN:=train/trainall.txt
JOBSIZE:=50

### Evaluate using 10-fold cross-validation
# Testfold are specified, devset folds are derived from that 
FOLDS?= 1 2 3 4 5 6 7 8 9 10
TPL:=$(basename $(notdir $(TEMPLATE)))
CVDATA_OUT:= $(TPL)_cv.d
cvdata-out-files:=$(foreach f, $(FOLDS), $(CVDATA_OUT)/train_$f.tsv)
cvdata-out-files:=$(foreach f, $(FOLDS), $(CVDATA_OUT)/test_$f.tsv)
cvdata-out-files+=$(foreach f, $(FOLDS), $(CVDATA_OUT)/train_$f.mod)
#cvdata-out-files+=$(foreach f, $(FOLDS), $(CVDATA_OUT)/test_$f.eval.tsv)

eval-target: $(cvdata-out-files) $(CVDATA_OUT).eval.tsv


$(CVDATA_OUT)/train_%.tsv $(CVDATA_OUT)/test_%.tsv $(CVDATA_OUT)/dev_%.tsv $(CVDATA_OUT)/train_%.mod: $(TRAIN)
	mkdir -p $(CVDATA_OUT) && \
	bash lib/linize.bash < $< | sort -R --random-source=$<  > $(CVDATA_OUT)/$(notdir $(TRAIN)).unverticalized
	perl lib/split-train-test.perl -cont 10/$* -nthd  -dv $(CVDATA_OUT)/dev_$*.txtv -tr $(CVDATA_OUT)/train_$*.txtv -te $(CVDATA_OUT)/test_$*.txtv  $(CVDATA_OUT)/$(notdir $(TRAIN)).unverticalized
	for f in $(CVDATA_OUT)/dev_$*.txtv  $(CVDATA_OUT)/train_$*.txtv  $(CVDATA_OUT)/test_$*.txtv ; do perl -ne ';s/\x0B/\n/g; print '<  $$f > $${f%v} ; done && rm $(CVDATA_OUT)/*.txtv
	nice wapiti train -i $(JOBSIZE) -p $(TEMPLATE) -t 12 -d $(CVDATA_OUT)/dev_$*.txt $(CVDATA_OUT)/train_$*.txt > $(CVDATA_OUT)/train_$*.mod 2> $(CVDATA_OUT)/train_$*.mod.err
	nice wapiti label -m $(CVDATA_OUT)/train_$*.mod -c $(CVDATA_OUT)/test_$*.txt > $(CVDATA_OUT)/test$*.mod.eval 2> $(CVDATA_OUT)/test$*.eval.err
	

$(CVDATA_OUT).eval.tsv: $(foreach f, $(FOLDS), $(CVDATA_OUT)/train_$f.mod)
	lib/wapiti_cv_eval.py $(CVDATA_OUT)/test*.eval.err > $@
	
cycle:
	nice wapiti train -p $(TEMPLATE) -t 12 $(EVALTRAIN) -c $(CVDATA_OUT)/test_$*.tsv > $(EVALMODEL)



### Produce the final model


MODEL:=$(TRAIN).mod
$(MODEL): $(TRAIN)
	bash lib/randomize_sequences.bash < $< > $<.random
	perl lib/split-train-test.perl -cont 10/1 -tr $<.random.train -te $<.random.dev $<.random
	nice wapiti train -p $(TEMPLATE) -t $(THREADS) -d $<.random.dev $<.random.train > $(MODEL) || rm -f $@

final: $(MODEL)


train/trainall.txt: $(EVALTRAIN) $(EVALTEST)
	cat $+ > $@

# General rule for non-existing directories
%.d:
	mkdir -p $@
SHELL:=/bin/bash
