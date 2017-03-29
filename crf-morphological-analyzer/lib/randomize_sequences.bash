#!/bin/bash

perl -ne ' s/(?<=\S)\n$/\x0B/g;print' | perl -ne 'print unless /^\s*$/'|paste $1 - | LC_ALL=C sort -k1,1| perl -ne 's/^\d+\t//;s/\x0B/\n/g; print '
