#!/usr/local/bin/python3.5
import os
import csv
import sys
import optparse
import subprocess
import time
#from pexpect import pxssh
emonname = "test_sar"
sarcmd = "ssh -f SUT \"cd /pnpdata/emon/results/Twitter; ./run_sar.sh  " + emonname + "_net.txt" + " \"" 
    #os.system( pqoscmd)
os.system(sarcmd)
