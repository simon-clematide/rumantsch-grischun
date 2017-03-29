THREADS?=4
TEMPLATE?=templates/rumantsch-template.txt
EVALTRAIN:=train/train4500.txt
EVALTEST:=test/dino-corr.txt
TPL:=rumantsch-template.txt
EVALMODEL:=$(EVALTRAIN).mod
cycle:
	nice wapiti train -p $(TEMPLATE) -t 12 $(EVALTRAIN) > $(EVALMODEL)


TRAIN:=train/trainall.txt

MODEL:=$(TRAIN).mod
$(MODEL): $(TRAIN)
	bash lib/randomize_sequences.bash < $< > $<.random
	perl lib/split-train-test.perl -cont 10/1 -tr $<.random.train -te $<.random.dev $<.random
	nice wapiti train -p $(TEMPLATE) -t $(THREADS) -d $<.random.dev $<.random.train > $(MODEL) || rm -f $@

final: $(MODEL)


train/trainall.txt: $(EVALTRAIN) $(EVALTEST)
	cat $+ > $@
