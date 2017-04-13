#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
compute mean and stddev from wapiti
"""

import codecs
import re
import sys

import numpy as np

sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
sys.stdin = codecs.getreader("utf-8")(sys.stdin.detach())



data = []
accuracy = []
for a in sys.argv[1:]:
    if not a.endswith('eval.err'):
        continue
    print('#reading', a, file=sys.stderr)
    with open(a, 'r', encoding='utf-8') as f:
        for l in f:
            #     Sequence error: 12.12%
            if 'Token error' in l:
                m = re.search(r'(\d+\.\d+)%', l)
                if m:
                    data.append(float(m.group(1)))
                    accuracy.append(100 - float(m.group(1)))
print(data, file=sys.stderr)
print("{0:05.3f}\t{1:06.3f}\t{2:06.3f}".format(np.mean(accuracy), np.std(accuracy), np.mean(data)), sep="\t")
