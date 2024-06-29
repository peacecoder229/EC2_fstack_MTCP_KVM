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
./process_stats_of_file.py  --filepattern="*rd_con5_d512.txt" --indexpattern="GET" --statpos=1  --indexpos=0
Script to process min and max for a number of files and summarize them
ToDO -> printing help if args are messed up
Then currently df.query('val == @maxv')['case']
is returning more then one case. Figure out a way to sumarizethem. Only their numbers are being reported now.
Could some pattern matchng a cool idea for specific things in those index names

'''


def get_opts():
    """
    usage ./process_stats_of_file.py  --filepattern="inst[0-1]${core}_con${connections}_d512.txt" --indexpattern="GET" --statpos=1 --indexpos=0 --outfile=testsum
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


if __name__ == "__main__":
    options = get_opts()

    files = options.filepat
    items = options.idxpat
    statpos = int(options.statpos)
    idexpos = int(options.idexpos)
    sumfile = options.out
    if (files is None or items is None or statpos is None or idexpos is None):
        print("options not set right. Please check --help")
        sys.exit(1)

    allfiles = list()
    dir = os.getcwd()
    for path in Path(dir).glob(files):
        # rglob provide recursive file discovery
        allfiles.append(path.name)
    sum = open(sumfile, "w") if sumfile else sys.stdout
    sum.write("filename, min, minindex, max, maxindex, avg, p50, p75, p90\n")
    for f in allfiles:
        #print(f)
        with open(f, "r") as out:
            data = dict()
            data['case']=list()
            data['val']=list()
            for line in out:
                if line.find(items) > -1:
                    val = line.split()[statpos]
                    index = line.split()[idexpos]
                    data['case'].append(index)
                    data['val'].append(val)
                    #print(index)
                    #data[index] = val
                    #print(val)
        #print(data) 
        #df = pd.DataFrame(list(data.items()), columns=['case', 'val'])
        df = pd.DataFrame(data)
        #print(df)
        df[['val']] =  df[['val']].apply(pd.to_numeric)
        #print(df['val'])
        #print(df)
        minv = df['val'].min()
        mincase = df.query('val == @minv')['case'].to_list()
        maxv = df['val'].max()
        maxcase = df.query('val == @maxv')['case'].to_list()
        p_10 = df.val.quantile(0.10)
        p_20 = df.val.quantile(0.20)
        p_30 = df.val.quantile(0.30)
        p_40 = df.val.quantile(0.40)
        p_50 = df.val.quantile(0.50)
        p_60 = df.val.quantile(0.60)
        p_75 = df.val.quantile(0.75)
        p_90 = df.val.quantile(0.90)
        avg = df['val'].mean()
        sum.write(f + ", " + str(minv)  + ", " + str(len(mincase)) + ", " + str(maxv) + ", " + str(len(maxcase)) + ", " + str(avg) + ", "  + str(p_50) + ", "  + str(p_75) + ", " + str(p_90) + ", "  + str(p_10) + ", "  + str(p_20) + ", " + str(p_30) + ", "  + str(p_40) + ", "  + str(p_60) +"\n")








