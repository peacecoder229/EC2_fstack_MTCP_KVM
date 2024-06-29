#!/usr/local/bin/python3.5
import os
import csv
import sys
import optparse
import subprocess
import time
#from pexpect import pxssh

def get_opts():
    """
    read user params
    :return: option object
    """
    parser = optparse.OptionParser()
    parser.add_option("--host", dest="host_ip",
                      help="host ip that redie server run", default="127.0.0.1")

    parser.add_option("--cores", dest="corestolaunch",
                      help="host ip that redie server run", default=None)


    parser.add_option("-l", "--loop_num", dest="loop",
                      help="redis-benchmark request number", default="8")


    parser.add_option("--ratio", dest="ratio",
                      help="write and read ratio", default="1")

    (options, args) = parser.parse_args()

    return options

def get_core_list(corecount=8, cores=None):
    corelist=list()
    if cores:
      core_slices=cores.split(",")
      for i in core_slices:
        (start,end)=i.split("-")
        k = int(start)
        while(k <= int(end)):
          corelist.append(k)
          k=k+1
      return corelist
    else:
      k = 1
      while(k <= int(corecount)):
        corelist.append(k)
        k=k+1
      return corelist

def run_redis_server(options):
    """
    start redis server on the host
    """
    cores = get_core_list(corecount=options.loop, cores=options.corestolaunch)
    corenum = len(cores)
    if(options.ratio=="1:4" or options.ratio=="1:0"):
        if(options.host_ip == "127.0.0.1"):
            os.system("pkill redis")
        else:
           pass 
    time.sleep(3)
    for port in range(9001, 9001+corenum):
        core=str(cores.pop())
        cmd = "taskset -c %s redis-server --bind %s --port %s --save "" &"  % (core,options.host_ip,port)
        print ("CMD is  " + cmd)

if __name__ == "__main__": 
    options = get_opts()
    if(options.ratio!="0:1"):
        run_redis_server(options)





