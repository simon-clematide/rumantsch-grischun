# -*- coding: utf-8 -*-
# Author: Reto Baumgartner

from __future__ import division
import sys
import subprocess
import re

# use: python analyse.py < infile [> outfile]
# or: python analyse.py infile [> outfile]

# Variables to be set before use:
# flookup (foma) and saved automaton:
flookup = "flookup"
analyseautomat = "GrischunGuessing.fst"
# wapiti and model:
wapiti = "../wapiti/wapiti"
taggingmodel = "modell7"
# True = output will remain sentence split (no impact on non-split input):
sentenesSplit = True
# True = lemma and analysis will be separated (xfst style):
lemmaSplit = True
# True = blank line between every word (xfst and foma style):
blankLine = True

################################################################################

def betterPrint(token, analysis):
    if lemmaSplit:
        analysisPlus = re.sub(r'^([^^]+)\+(Adj|Adv|Art|Conj|Dig|Initial|Interj|Let|Noun|Num|Prep|Pron|Prop|Punc|PUNCT|Rom|Subj|Verb)', r'\1\t+\2', analysis, 1)
        print(token + "\t" + analysisPlus) 
    else:
        print(token + "\t" + analysis)

def processSentence(sentence, lastsentence):
    # Collect output from morphology analysis:
    morpho = subprocess.Popen(
        [flookup, analyseautomat],
        stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    morphoout, stderr = morpho.communicate(sentence)
    morphowords = morphoout.rstrip().split("\n\n")

    # Rewind input
    #input_file.seek(0)

    # Collect output from PoS-tagging
    pos = subprocess.Popen(
        [wapiti, "label", "-m", taggingmodel, "-n", "3", "-p", "-s"],
        stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    posout, stderr = pos.communicate(sentence)
    poswordsmulti = posout.rstrip().split("\n\n")
    poswords = []
    poswords.append(poswordsmulti[0].split("\n")[1:])
    poswords.append(poswordsmulti[1].split("\n")[1:])
    poswords.append(poswordsmulti[2].split("\n")[1:])

    wordcounter = 0
    # Compare results
    for i in range(len(morphowords)):
        wordcounter += 1

        matching = []
        matchingminus1 = []
        matchingminus2 = []
        notmatching = []

        morphocandidates = morphowords[i].split("\n")

        for p in poswords:
            postoken = p[i].split("\t")[0]
            postagging = p[i].split("\t")[1]
            postags = postagging.split("+")[1:]
            posscore = eval(p[i].split("\t")[2].split("/")[1])

            for m in morphocandidates:
                morphotoken, morphoanalysis = m.split("\t", 1)
                morpholemma, morphotagging = morphoanalysis.split("+", 1)
                morphotags = morphotagging.split("+")

                if morphoanalysis == "+?":
                    notmatching.append((postoken, morphoanalysis, posscore, postagging))
                elif set(postags).issubset(morphotags):
                    matching.append((postoken, morphoanalysis, posscore, postagging))
                elif len(set(postags)-set(morphotags)) == 1:
                    matchingminus1.append((postoken, morphoanalysis, posscore, postagging))
                elif len(set(postags)-set(morphotags)) == 2:
                    matchingminus2.append((postoken, morphoanalysis, posscore, postagging))
                else:
                    notmatching.append((postoken, morphoanalysis, posscore, postagging))

        # Choose and print the best candidate
        if len(matching) > 0:
            best = sorted(matching, key=lambda m: m[2])
            betterPrint(best[-1][0], best[-1][1])

        elif len(matchingminus1) > 0:
            best = sorted(matchingminus1, key=lambda m: m[2])
            betterPrint(best[-1][0], best[-1][1])

        elif len(matchingminus2) > 0:
            best = sorted(matchingminus2, key=lambda m: m[2])
            betterPrint(best[-1][0], best[-1][1])

        else:
            if notmatching[0][1] == "+?":
                betterPrint(notmatching[-1][0], notmatching[-1][0] + notmatching[-1][3])
            else:
                best = sorted(notmatching, key=lambda m: m[2])
                betterPrint(best[-1][0], best[-1][1])
        if blankLine and wordcounter == len(morphowords) and lastsentence:
            pass
        elif blankLine:
            print("")

# Input as argument or piped
if len(sys.argv) > 1:
    input_file = open(sys.argv[1], "r")
else:
    input_file = sys.stdin

# Process sentences in input
sentences = input_file.read().split("\n\n")
sentencecounter = 0
for s in sentences:
    sentencecounter += 1
    lastsentence = False
    if sentencecounter == len(sentences):
        lastsentence = True
    processSentence(s, lastsentence)
    if sentenesSplit and not lastsentence:
        print("")