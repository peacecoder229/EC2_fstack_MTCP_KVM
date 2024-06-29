#!/usr/local/bin/python3.5
import os
import csv
import sys
import optparse
import subprocess
import time
emonname = "test" 
emondir = "Test"
emoncmd = "ssh 192.168.5.99 \"/pnpdata/emon/run_emon_sriov.sh 10 " + emonname + " " + emondir + " \""
os.system(emoncmd)
time.sleep(90)
os.system("ssh 192.168.5.99 \"source /opt/sep41/sep_vars.sh ; emon -stop\"")





