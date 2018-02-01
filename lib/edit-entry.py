#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
from optparse import OptionParser
import os
import sys
import codecs
import os.path
from collections import defaultdict

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


def output_entries(entries,args,options):
    entries.sort()

    existing_entries = []
    with codecs.open(args[2],'r',encoding="utf-8") as f:
        for l in f:
            entry = l.rstrip()
            if entry != '':
                existing_entries.append(entry)
    print('#INFO-NUMBER-OF-EXISTING-ENTRIES',len(existing_entries),file=sys.stderr)
    print('#INFO-NUMBER-OF-CURRENT-ENTRIES ',len(entries),file=sys.stderr)


    if existing_entries == entries:
        print('#INFO-FILE-NEEDED-NO-CHANGE',args[2],file=sys.stderr)
        return
    with codecs.open(args[2],'w',encoding="utf-8") as f:
        for e in entries:
            print(e,file=f)
    print('#INFO-FILE-CHANGED',args[2],file=sys.stderr)


def process(options=None,args=None):
    """
    Do the processing
    """
    if options.debug:
        print >>sys.stderr, options
    entries = []
    entry_to_delete = entry_to_add =  None
    entry_found = False
    if args[0] == 'DEL':
        entry_to_delete = args[1]
    if args[0] == 'ADD':
        entry_to_add = args[1]
    with codecs.open(args[2],'r',encoding="utf-8") as f:
        for i,l in enumerate(f):
            entry = l.rstrip()
            if entry != '':
                if entry_to_delete:
                    if entry_to_delete != entry:
                        entries.append(entry)
                    else:
                        entry_found = True
                else:
                    entries.append(entry)
    if entry_to_add and entry_to_add not in entries:
        entries.append(entry_to_add)

    if entry_to_delete and not entry_found:
        print('#WARNING-ENTRY-TO-DELETE-NOT-FOUND',entry_to_delete,file=sys.stderr)
        print('#INFO-FILE-NEEDED-NO-CHANGE',args[2],file=sys.stderr)
        return

    output_entries(entries, args, options)



def main():
    """
    Invoke this module as a script
    """
# global options
    parser = OptionParser(
        usage = '%prog [ADD|DEL] ENTRY FILE',
        version='%prog 0.99', #
        description='Add or delete one ENTRY from a wordlist FILE destructively and sort the file',
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

    if len(args) != 3:
        print('WRONG ARGUMENTS',file=sys.stderr)
        exit(1)
    if args[0] not in ['ADD','DEL']:
        print('WRONG COMMAND',file=sys.stderr)
        exit(2)
    if not os.path.isfile(args[2])  :
        print('LEXICON FILE MUST EXIST',file=sys.stderr)
        exit(3)
#    print(args[1],type(args[1]))
#    exit(0)
    process(options=options,args=args)


if __name__ == '__main__':
    main()
