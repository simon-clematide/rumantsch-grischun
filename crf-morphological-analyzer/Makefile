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
	nice wapiti train -p $(TEMPLATE) -t 12 $(TRAIN) > $(MODEL) || rm -f $@

final: $(MODEL)


train/trainall.txt: $(EVALTRAIN) $(EVALTEST)
	cat $+ > $@
