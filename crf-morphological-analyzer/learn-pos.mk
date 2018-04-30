# learning curves
include Makefile
MAXITER?=50
THREADS?=4
LEARNDIR:=learn-pos.d
size:= 1 2 3 4 5 6 7 8 9 
size:= 9
TEMPLATEPOS:=templates/rumantsch-template-pos.txt
$(shell mkdir -p $(LEARNDIR)/)
lc_folds?= 1 2 3 4 5 6 7 8 9 10

rm_train-pos-file := train/trainall-pos.txt

# pli	+Adv
# che	+Subj
# 800	+Dig+Card

train/trainall-pos.txt: train/trainall.txt
	perl -lne 'print  if /^\s*$$/;if (s/^(\S+)\s+(\+[^+^]+).*/\1\t\2/) { print;} else { print STDERR $$_;}' < $< > $@

train-pos-files:= $(foreach _n,$(size),$(LEARNDIR)/rm_train_$(_n).txt)
train-fold-files:= $(foreach f,$(lc_folds),$(foreach _n,$(size),$(LEARNDIR)/rm_train_$(f)_$(_n).txtv))
train-mod-files:= $(foreach f,$(lc_folds),$(foreach _n,$(size),$(LEARNDIR)/rm_train_$(f)_$(_n).mod))

#$(info $(train-mod-files))

# Rule template for BOW evaluation
define FOLD_TRAIN_RULE

$(LEARNDIR)/rm_train_%.txt: $(rm_train-pos-file)
	bash lib/randomize_sequences.bash < $$< | head -n $$$$(($$* * 1000)) > $$@

$(LEARNDIR)/rm_train_$(FOLD)_%.txtv $(LEARNDIR)/test_$(FOLD)_%.txtv $(LEARNDIR)/dev_$(FOLD)_%.txtv : $(LEARNDIR)/rm_train_%.txt
	perl lib/split-train-test.perl -cont 10/$(FOLD) -nthd -dv $(LEARNDIR)/dev_$(FOLD)_$$*.txtv -tr $(LEARNDIR)/rm_train_$(FOLD)_$$*.txtv -te $(LEARNDIR)/test_$(FOLD)_$$*.txtv  $$<


$(LEARNDIR)/rm_train_$(FOLD)_%.mod : $(LEARNDIR)/rm_train_$(FOLD)_%.txtv $(LEARNDIR)/test_$(FOLD)_%.txtv $(LEARNDIR)/dev_$(FOLD)_%.txtv 
	nice wapiti train -i $(MAXITER) -p $(TEMPLATEPOS) -t $(THREADS) -d $(LEARNDIR)/dev_$(FOLD)_$$*.txtv $(LEARNDIR)/rm_train_$(FOLD)_$$*.txtv > $(LEARNDIR)/rm_train_$(FOLD)_$$*.mod 2> $(LEARNDIR)/rm_train_$(FOLD)_$$*.mod.err
	nice wapiti label -m $(LEARNDIR)/rm_train_$(FOLD)_$$*.mod -c $(LEARNDIR)/test_$(FOLD)_$$*.txtv > $(LEARNDIR)/test_$(FOLD)_$$*.mod.eval 2> $(LEARNDIR)/test_$(FOLD)_$$*.eval.err


endef

$(eval $(foreach FOLD,$(lc_folds),$(FOLD_TRAIN_RULE)))






learn-pos-target: $(train-pos-files)  $(train-fold-files) $(train-mod-files)



