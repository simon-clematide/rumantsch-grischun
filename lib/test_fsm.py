#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Should work under Python 2 or 3
from __future__ import unicode_literals, print_function
from optparse import OptionParser
import os
import sys
import codecs
from collections import defaultdict

UNKNOWNFREQTHRESHOLD = 1

IGNOREDPOSTAGS = set()
RESTRICTEDPOSTAGS = set()
IGNOREMORPHTAGS = set()
"""
Module for testing the correctness and completeness of transducers according to test words
"""

# python 2/3 compatibility
if sys.version_info < (3, 0):
  sys.stderr = codecs.getwriter('UTF-8')(sys.stderr)
  sys.stdout = codecs.getwriter('UTF-8')(sys.stdout)
  sys.stdin = codecs.getreader('UTF-8')(sys.stdin)
else:
  sys.stderr = codecs.getwriter('UTF-8')(sys.stderr.buffer)
  sys.stdout = codecs.getwriter('UTF-8')(sys.stdout.buffer)
  sys.stdin = codecs.getreader('UTF-8')(sys.stdin.buffer)


def read_testdata(testfiles, options=None):
    """Return dict of word forms and a set of admissible gold analyses"""
    data = defaultdict(set)

    for testfile in testfiles:
        if not options.quiet:
            print('# reading test data from file:', testfile, file=sys.stderr)
        with codecs.open(testfile, 'r', encoding="utf-8") as f:
            for l in f:
                if l.startswith('#'):
                    continue
                d = l.rstrip().split('\t')
                if options.mode == 'unknown':
                    if int(d[0]) >= UNKNOWNFREQTHRESHOLD:
                        data[d[1]] = set()
                else:
                    if len(d) > 1:
                        if options.ignore:
                            tags = d[1].split('+',1)
                            if tags[0] in IGNOREDPOSTAGS:
                                continue
                        data[d[0]].add(d[1])
                    if len(d) == 1:
                        data[d[0]] = set()
    print('# word forms read in :', len(data), file=sys.stderr)
    print('# total number of analyses:', sum(len(data[a]) for a in data), file=sys.stderr)
    return data


def test_fsm(fsm, data, options=None):
    """Report test results"""

    for wf in data:
        word_results = set()
        result = None
        for result in fsm.apply_up(wf):
            if options.restrict or options.ignore:
                tags = result.split('+')
                if len(tags) > 1:
                    if ((options.ignore and tags[1] in IGNOREDPOSTAGS)
                        or (options.restrict and not tags[1] in RESTRICTEDPOSTAGS)) :
                        continue
                    if options.morph_ignore:
                        if set(tags).intersection(IGNOREMORPHTAGS):
                            continue
            word_results.add(result)

        # False positives
        fp = word_results - data[wf]

        # False negatives
        fn =  data[wf] - word_results

        # True positives
        tp = data[wf].intersection(word_results)

        if options.mode == 'unknown' and not word_results:
            print(wf)
            continue
        if not options.quiet:
            print('# checking wf:', wf, file=sys.stderr)

        if options.mode in {'all'}:
            for a in fp:
                print("FP\t%s\t%s" %(wf, a), file=sys.stdout)
        for a in fn:
            print("FN\t%s\t%s" %(wf, a), file=sys.stdout)
        if not options.quiet:
            for a in tp:
                print("TP\t%s\t%s" %(wf, a), file=sys.stdout)
        if not ( fp or fn) and not options.quiet:
            print('# test ok for wf:', wf, file=sys.stderr)



def process(options=None,args=None):
    """
    Do the processing using foma or xfst by now
    """

    if options.debug:
        print(options, file=sys.stderr)
    if options.tool == "foma":
        import foma


        data = read_testdata(args[1:],options=options)
        fsm = foma.read_binary(args[0])


    if options.tool == "xfst":
        import xfst
        data = read_testdata(args[1:])
        fsm = xfst.read_binary(args[0])

    test_fsm(fsm, data, options=options)




def main():
    """
    Invoke this module as a script
    """
    global UNKNOWNFREQTHRESHOLD, IGNOREDPOSTAGS,RESTRICTEDPOSTAGS
    parser = OptionParser(
        usage = '%prog [OPTIONS] TRANSDUCER TESTFILE ...',
        version='1.00',
        description= ('Test finite state transducer using pyfoma/pyxfst API.'
        'See https://github.com/simon-clematide/foma for foma Cython API.'
        'See for xfst API see https://github.com/vchahun/pyxfst.'
        'Contact simon.clematide@uzh.ch'
        ),
        epilog=(
                'File format of tabulator separated gold files: first column is word form, '
                'second colum is the analysis'
                ' if only the first column is given, this means that the wordform should not be recognized.'

             )
        )
    parser.add_option('-l', '--logfile', dest='logfilename',
                      help='write log to FILE', metavar='FILE')
    parser.add_option('-q', '--quiet',
                      action='store_true', dest='quiet', default=False,
                      help='do not print status messages to stderr')
    parser.add_option('-d', '--debug',
                      action='store_true', dest='debug', default=False,
                      help='print debug information')
    parser.add_option('-t', '--tool',
                      action='store', dest='tool', default="foma",
                      help='use tool for testing: foma or xfst (default %default)')
    parser.add_option('-m', '--mode',
                      action='store', dest='mode', default="all",
                      help='mode of action: coverage, all, unknown (default %default)')
    parser.add_option('-T', '--unknown_threshold',
                      action='store', dest='unknown_threshold', default=1, type=int,
                      help='minimal number of occurrence for unknown word analysis (default %default)')
    parser.add_option('-i', '--ignore',
                      action='store', dest='ignore', default=None,
                      help='plus-separated list of POS tags to ignore')
    parser.add_option('-I', '--morph_ignore',
                      action='store', dest='morph_ignore', default=None,
                      help='plus-separated list of morph tags that result in analyses to be ignored')
    parser.add_option('-r', '--restrict',
                      action='store', dest='restrict', default=None,
                      help='plus-separated list of POS tags to ignore')

    (options, args) = parser.parse_args()
    if options.debug:
        print("options=",options, file=sys.stderr)
    if options.tool not in {"xfst","foma"}:
        print("option -t/--tool must be foma or xfst", file=sys.stderr)
        exit(3)

    if len(args) < 2:
        parser.print_usage(file=sys.stderr)
        exit(1)
    if options.mode == 'unknown':
        UNKNOWNFREQTHRESHOLD = options.unknown_threshold
        print('# info: threshold for unknowns set to', UNKNOWNFREQTHRESHOLD, file=sys.stderr)

    if not options.ignore is None:
        for t in options.ignore.split('+'):
            IGNOREDPOSTAGS.add(t)
    if not options.restrict is None:
        for t in options.restrict.split('+'):
            RESTRICTEDPOSTAGS.add(t)
    if not options.morph_ignore is None:
        for t in options.morph_ignore.split('+'):
            IGNOREMORPHTAGS.add(t)

    process(options=options,args=args)


if __name__ == '__main__':
    main()
