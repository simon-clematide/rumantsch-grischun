from __future__ import division
import sys

goldfile = open("dardin-vollanalyse.txt", "r")
gold = goldfile.readlines()

counter = 0
equallines = 0

for line in sys.stdin:
    if line.rstrip() == gold[counter].rstrip():
        equallines += 1
    counter += 1
    
print str(equallines) + "/" + str(counter)
print equallines/counter
