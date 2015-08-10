
INPUT:=train4500.txt
TPL:=rumantsch-template.txt
MODEL:=$(INPUT).mod
cycle:
	nice wapiti train -p $(TPL) -t 12 $(INPUT) > $(MODEL)
