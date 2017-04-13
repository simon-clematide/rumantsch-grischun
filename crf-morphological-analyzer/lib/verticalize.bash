#!/bin/bash

perl -ne ' s/(?<=\S)\n$/\x0B/g;print' | perl -ne 'print unless /^\s*$/'
