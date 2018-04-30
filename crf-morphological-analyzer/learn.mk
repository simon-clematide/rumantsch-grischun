# learning curves

MAXITER?=50
THREADS?=4

size:= 1 2 3 4 5 6 7

$(shell mkdir -p learn.d/)
lc_folds?= 1 2 3 4 5 6 7 8 9 10

rm_train-file := train/trainall.txt

train-files:= $(foreach _n,$(size),learn.d/rm_train_$(_n).txt)
train-fold-files:= $(foreach f,$(lc_folds),$(foreach _n,$(size),learn.d/rm_train_$(f)_$(_n).txtv))
train-mod-files:= $(foreach f,$(lc_folds),$(foreach _n,$(size),learn.d/rm_train_$(f)_$(_n).mod))

#$(info $(train-mod-files))

# Rule template for BOW evaluation
define FOLD_TRAIN_RULE

learn.d/rm_train_%.txt: $(rm_train-file)
	bash lib/randomize_sequences.bash < $$< | head -n $$$$(($$* * 1000)) > $$@

learn.d/rm_train_$(FOLD)_%.txtv learn.d/test_$(FOLD)_%.txtv learn.d/dev_$(FOLD)_%.txtv : learn.d/rm_train_%.txt
	perl lib/split-train-test.perl -cont 10/$(FOLD) -nthd -dv learn.d/dev_$(FOLD)_$$*.txtv -tr learn.d/rm_train_$(FOLD)_$$*.txtv -te learn.d/test_$(FOLD)_$$*.txtv  $$<


learn.d/rm_train_$(FOLD)_%.mod : learn.d/rm_train_$(FOLD)_%.txtv learn.d/test_$(FOLD)_%.txtv learn.d/dev_$(FOLD)_%.txtv 
	nice wapiti train -i $(MAXITER) -p $(TEMPLATE) -t $(THREADS) -d learn.d/dev_$(FOLD)_$$*.txtv learn.d/rm_train_$(FOLD)_$$*.txtv > learn.d/rm_train_$(FOLD)_$$*.mod 2> learn.d/rm_train_$(FOLD)_$$*.mod.err
	nice wapiti label -m learn.d/rm_train_$(FOLD)_$$*.mod -c learn.d/test_$(FOLD)_$$*.txtv > learn.d/test_$(FOLD)_$$*.mod.eval 2> learn.d/test_$(FOLD)_$$*.eval.err


endef

$(eval $(foreach FOLD,$(lc_folds),$(FOLD_TRAIN_RULE)))






learn-target: $(train-files)  $(train-fold-files) $(train-mod-files)


