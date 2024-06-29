#!/usr/bin/env python3
import os
import csv
import sys
import optparse
import subprocess
import time
import pandas as pd
from pathlib import Path

'''
usage
metric=$(./process_stats_of_perf_r1.py  --filepattern="${perf}${core}_${ins}_${connections}_stat.txt" --indexpattern="tsc,r0300,r00c0,stalls_mem_any" --statpos=1  --indexpos=2 | grep -v "file")

./process_stats_of_file.py  --filepattern="*rd_con5_d512.txt" --indexpattern="GET" --statpos=1  --indexpos=0
Script to process min and max for a number of files and summarize them
ToDO -> printing help if args are messed up
Then currently df.query('val == @maxv')['case']
is returning more then one case. Figure out a way to sumarizethem. Only their numbers are being reported now.
Could some pattern matchng a cool idea for specific things in those index names

Additional notes: THis program will read in line by ine out from say perf and estimate min max avg values of then metrics
Also plots of the metrics can also be created
example CMD
./process_stats_of_file_r1.py  --filepattern="perfstat56_4_16_stat.txt" --indexpattern="tsc,r0300,r00c0,stalls_mem_any" --statpos=1  --indexpos=2

'''




def get_opts():
    """
    read user params
    :return: option object
    """
    parser = optparse.OptionParser()
    parser.add_option("--filepattern", dest="filepat",  help="provide filename rgexp", default=None)
    parser.add_option("--indexpattern", dest="idxpat", help="provide item search rgexp", default=None)
    parser.add_option("--statpos", dest="statpos", help="provide column position for the items for statistical data", default=None)
    parser.add_option("--indexpos", dest="idexpos", help="provide column position for the items for caseitmes.. leftmost is 0.", default=None)
    parser.add_option("--outfile", dest="out", help="provide outfile name", default=None)


    (options, args) = parser.parse_args()
    return options

def checkifanyitemsinline(mylist, lookup):
    for s in lookup:
        n = next((x for x in mylist if x in s),None)
        if n is not None:
            return n

if __name__ == "__main__":
    options = get_opts()
    items = options.idxpat
    items = items.split(',')
    files = options.filepat
    data = dict()
    for itm in items:
        data[itm] = list()
        #items.append(itm)
    statpos = int(options.statpos)
    idexpos = int(options.idexpos)
    sumfile = options.out if options.out else False
    if (files is None or items is None or statpos is None or idexpos is None):
        print("options not set right. Please check --help")
        sys.exit(1)

    allfiles = list()
    dir = os.getcwd()
    for path in Path(dir).glob(files):
        # rglob provide recursive file discovery
        allfiles.append(path.name)
    #print(sumfile)
    sum = open(sumfile, "w") if sumfile  else sys.stdout
    metriccol = ['util', 'ipc', 'scyc']
    sum.write("filename,")
    for c in metriccol:
        sum.write("min_" + c + "," + "max_" + c + "," + "avg_" + c + ",")
    sum.write("\n")

    for f in allfiles:
        with open(f, "r") as out:
            for line in out:
                line = line.split()
                itemfound = checkifanyitemsinline(items, line)
                if itemfound:
                    #print("Match Found " + itemfound)
                    data[itemfound].append(line[statpos].replace(',', ''))
                else:
                    continue
                #print("Idex is " + index + "value is " + val) index is the item

        df = pd.DataFrame.from_dict(data, orient='index').transpose()
        cols = df.columns
        df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
        df['util'] = df['r0300']/df['tsc']
        df['ipc'] = df['r00c0']/df['r0300']
        df['scyc'] = df['stalls_mem_any']/df['r0300']
        #print(df)
        sum.write(f + ",")
        #metriccol = ['util', 'ipc', 'scyc']
        for c in metriccol:

        #df[['val']] =  df[['val']].apply(pd.to_numeric)
            minv = df[c].min()
            #mincase = df.query('val == @minv')['case'].to_list()
            maxv = df[c].max()
            #maxcase = df.query('val == @maxv')['case'].to_list()
            avg = df[c].mean()
            #sum.write(f + "," + str(minv)  + "," + str(len(mincase)) + "," + str(maxv) + "," + str(len(maxcase)) + "," + str(avg) + "\n")
            sum.write(str(minv)  + "," + str(maxv) + "," + str(avg) + ",")
    sum.write("\n")
    if sum is not sys.stdout:
        close(sum)









