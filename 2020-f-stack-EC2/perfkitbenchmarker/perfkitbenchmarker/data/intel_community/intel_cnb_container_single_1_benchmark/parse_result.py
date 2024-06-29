#!/usr/bin/env python3

import sys
import csv
import glob
from posixpath import join as urljoin


def main(args):
    requests = []
    with open(glob.glob(urljoin("results", "*", "*int8_summary.csv"))[0]) as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')
        next(readCSV)
        for row in readCSV:
            request = row[3]
            requests.append(int(request))

    succ_req_int8 = max(requests)

    print(succ_req_int8)

if __name__ == '__main__':
    main(sys.argv)
