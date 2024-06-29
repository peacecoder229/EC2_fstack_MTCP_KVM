#!/usr/local/bin/python3.5
import os
import sys
import re

file=sys.argv[1]
outfile = file + "_processed.csv"
out = open(outfile, "w")
all_lines = list()
all_lines = [ line.rstrip() for line in open(file, "r").readlines()]

formatted_list = list()
for i in range(0,len(all_lines)):
	formatted_list.append(all_lines[i])
	out.write(all_lines[i] + ",")
	#if ((i % 3) + 1 == 3):
	#	out.write("\n")
	nxt = (i + 1) % len(all_lines)
	if(re.search(r'(\d+).(\d+)', all_lines[i]) and re.search(r'case',  all_lines[nxt])):
		 out.write("\n") 

out.close()
print(formatted_list)
