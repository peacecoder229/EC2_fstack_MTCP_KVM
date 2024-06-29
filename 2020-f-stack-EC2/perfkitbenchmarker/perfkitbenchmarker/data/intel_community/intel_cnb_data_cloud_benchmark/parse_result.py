#!/usr/bin/env python3

import sys
import csv
import glob


def main(args):
    requests = []
    with open(glob.glob("result*.csv")[0]) as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')
        next(readCSV)
        for row in readCSV:
            request = row[12]
            requests.append(request)

    succ_req = max(requests)
    print(succ_req)

if __name__ == '__main__':
    main(sys.argv)
