
EVALTRAIN:=train/train4500.txt
EVALTEST:=test/dino-corr.txt
TPL:=rumantsch-template.txt
EVALMODEL:=$(EVALTRAIN).mod
cycle:
	nice wapiti train -p $(TPL) -t 12 $(EVALTRAIN) > $(EVALMODEL)


TRAIN:=train/trainall.txt
TPL:=rumantsch-template.txt
MODEL:=$(TRAIN).mod
$(MODEL): $(TRAIN)
	nice wapiti train -p $(TPL) -t 12 $(TRAIN) > $(MODEL) || rm -f $@

final: $(MODEL)


train/trainall.txt: $(EVALTRAIN) $(EVALTEST)
	cat $+ > $@
