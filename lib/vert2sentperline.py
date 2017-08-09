#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from optparse import OptionParser
import os
import sys
import codecs
"""
Module for XXX

"""

sys.stdout = codecs.getwriter('utf-8')(sys.__stdout__)
sys.stderr = codecs.getwriter('utf-8')(sys.__stderr__)
sys.stdin = codecs.getreader('utf-8')(sys.__stdin__)

SENTFINAL = set(".!?")

def process(options=None,args=None):
    """
    Do the processing
    """
    if options.debug:
        print >>sys.stderr, options


    sent = ""
    for l in sys.stdin:
        l = l.rstrip()
        if l in SENTFINAL:
            print sent + " " + l
            sent = ""
        elif sent == "":
            sent = l
        else:
            sent +=  " " + l
    if sent != "":
        print sent

def main():
    """
    Invoke this module as a script
    """
# global options
    parser = OptionParser(
        usage = '%prog [OPTIONS] [ARGS...]',
        version='%prog 0.99', #
        description='Calculate something',
        epilog='Contact simon.clematide@uzh.ch'
        )
    parser.add_option('-l', '--logfile', dest='logfilename',
                      help='write log to FILE', metavar='FILE')
    parser.add_option('-q', '--quiet',
                      action='store_true', dest='quiet', default=False,
                      help='do not print status messages to stderr')
    parser.add_option('-d', '--debug',
                      action='store_true', dest='debug', default=False,
                      help='print debug information')

    (options, args) = parser.parse_args()
    if options.debug:
        print >> sys.stderr, "options=",options


    process(options=options,args=args)


if __name__ == '__main__':
    main()
