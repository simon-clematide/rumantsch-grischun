# -*- coding: utf-8 -*-
# Author: Reto Baumgartner

from __future__ import division
import sys
import subprocess
import re
import codecs
from optparse import OptionParser

sys.stdout = codecs.getwriter('utf-8')(sys.__stdout__)
sys.stderr = codecs.getwriter('utf-8')(sys.__stderr__)
sys.stdin = codecs.getreader('utf-8')(sys.__stdin__)


# use: python analyse.py < infile [> outfile]
# or: python analyse.py infile [> outfile]

# Variables to be set before use:
# flookup (foma) and saved automaton:
flookup = "flookup"
analyseautomat = "GrischunGuessing.fst"
# wapiti and model:
wapiti = "wapiti"
taggingmodel = "modell9"
# True = output will remain sentence split (no impact on non-split input):
sentenesSplit = True
# True = lemma and analysis will be separated (xfst style):
lemmaSplit = True
# True = blank line between every word (xfst and foma style):
blankLine = False

################################################################################

def betterPrint(token, analysis):
    if lemmaSplit:
        analysisPlus = re.sub(r'^([^^]+)\+(Abbr|Adj|Adv|Art|CM|Conj|Dig|Initial|Interj|Let|Noun|Num|Prep|Pron|Prop|Punc|PUNCT|Rom|Sent|Subj|Verb)', r'\1\t+\2', analysis, 1)
        print(token + "\t" + analysisPlus)
    else:
        print(token + "\t" + analysis)

def processSentence(sentence, lastsentence,options=None):
    # Collect output from morphology analysis:
    if options.debug: print >> sys.stderr, '#MORPHO-CALL', " ".join([flookup, analyseautomat])
    sentence_utf8 = sentence.encode('utf-8')
    morpho = subprocess.Popen(
        [flookup, analyseautomat],
        stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    morphoout, stderr = morpho.communicate(sentence_utf8)
    morphowords = morphoout.decode('utf-8').rstrip().split("\n\n")
    if options.debug: print >> sys.stderr,morphowords
    # Rewind input
    #input_file.seek(0)

    # Collect output from PoS-tagging
    if options.debug: print >> sys.stderr, '#CRF-CALL', " ".join([wapiti, "label", "-m", taggingmodel, "-n", "3", "-p", "-s"])
    pos = subprocess.Popen(
        [wapiti, "label", "-m", taggingmodel, "-n", "3", "-p", "-s"],
        stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    posout, stderr = pos.communicate(sentence_utf8)
    poswordsmulti = posout.decode('utf-8').rstrip().split("\n\n")
    poswords = []
    poswords.append(poswordsmulti[0].split("\n")[1:])
    poswords.append(poswordsmulti[1].split("\n")[1:])
    poswords.append(poswordsmulti[2].split("\n")[1:])

    wordcounter = 0
    # Compare results
    for i,mw in enumerate(morphowords):
        wordcounter += 1

        matching = []
        matchingminus1 = []
        matchingminus2 = []
        notmatching = []

        morphocandidates = mw.split("\n")

        for p in poswords:
            postoken = p[i].split("\t")[0]
            postagging = p[i].split("\t")[1]
            postags = postagging.split("+")[1:]
            posscore = eval(p[i].split("\t")[2].split("/")[1])

            for m in morphocandidates:
                if m == '': continue
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

def main():
    """
    Invoke this module as a script
    """
    global taggingmodel
    global analyseautomat
    parser = OptionParser(version='%prog 0.99')
    parser.add_option('-l', '--logfile', dest='logfilename',
                      help='write log to FILE', metavar='FILE')
    parser.add_option('-q', '--quiet',
                      action='store_true', dest='quiet', default=False,
                      help='do not print status messages to stderr')
    parser.add_option('-d', '--debug',
                      action='store_true', dest='debug', default=False,
                      help='print debug information')
    parser.add_option('-m', '--model',
                      action='store', dest='model', default=taggingmodel,
                      help='choose trained crf model for morphological tagging (%default)')
    parser.add_option('-a', '--analyzer',
                      action='store', dest='analyzer', default=analyseautomat,
                      help='choose binary finite state analyzer transducer (%default)')

    (options, args) = parser.parse_args()
    if options.debug: print >> sys.stderr, "options=",options

    if options.model != taggingmodel:
        taggingmodel = options.model
    if options.analyzer != analyseautomat:
        analyseautomat = options.analyzer

    # Input as argument or piped
    if len(args) > 0:
        input_file = codecs.open(args[0],'r','utf-8')
    else:
        input_file = sys.stdin

    # Process sentences in input
    sentences = input_file.read().split("\n\n")
    if options.debug: print >>sys.stderr, sentences
    sentencecounter = 0
    for s in sentences:
        s = s.strip()
        if s == '': continue
        sentencecounter += 1
        lastsentence = False
        if sentencecounter == len(sentences):
            lastsentence = True
        processSentence(s, lastsentence,options=options)
        if sentenesSplit and not lastsentence:
            print("")


if __name__ == '__main__':
    main()
