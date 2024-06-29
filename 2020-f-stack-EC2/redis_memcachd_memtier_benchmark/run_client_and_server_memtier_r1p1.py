#!/usr/local/bin/python3.5
import os
import csv
import sys
import optparse
import subprocess
import time
#from pexpect import pxssh
fd = open('Log.txt', "w")
def get_opts():
    """
    read user params
    :return: option object
    """
    parser = optparse.OptionParser()
    parser.add_option("--keypattern", dest="keys_pat",
                      help="read and write key pattern", default="S:S")
    parser.add_option("--keymin", dest="key_min",
                      help="minimum key number", default="1")
    parser.add_option("--ratio", dest="ratio",
                      help="write and read ratio", default="1")
    parser.add_option("--keymax", dest="key_max",
                      help="maximum key number", default="100000000")

    parser.add_option("--host", dest="host_ip",
                      help="host ip that redie server run", default="127.0.0.1")

    parser.add_option("--scores", dest="servercores",
                      help="server cores to run redis server example 0-7,14-21", default=None)

    parser.add_option("--ccores", dest="clientcores",
                      help="client cores to launch clients example 0-7,14-21", default=None)

    parser.add_option("-n", "--request_num", dest="num",
                      help="redis-benchmark request number", default="100000")

    parser.add_option("-l", "--loop_num", dest="loop",
                      help="ifserver cores are not specified than no of servers to launch starting from core=1 number", default="8")

    parser.add_option("--mark",  dest="mark_name",
                      help="save report name", default="memtier")

    parser.add_option("-d","--datasize", dest="data",
                      help="datasize of packets", default="1024")

    parser.add_option("-p","--pipeline", dest="pipeline",
                      help="pipelins in request", default=16)
 
    parser.add_option("-c", "--con_num", dest="connection",
                      help="redis-benchmark request number", default="50")

    parser.add_option("--pclient",  dest="primeclient",
                      help="example Yes", default=None)

    parser.add_option("--sport",  dest="serverport",
                      help="provide starting port of the server core group", default=9001)
 
    parser.add_option("--port",  dest="percentport",
                      help="percentage of ports to launch clients example half_top or half_bottom", default="half_top")
    (options, args) = parser.parse_args()

    return options

from memtier_client_server_modules import *

if __name__ == "__main__": 
    options = get_opts()
    #if(options.ratio!="0:1"):
        #run_redis_server(options)
    #emondir = options.mark_name
    #emonname = "run_" + options.ratio
    #emoncmd = "ssh 192.168.5.99 \"/pnpdata/emon/run_emon_sriov.sh 10 " + emonname + " " + emondir + " \""
    #os.system(emoncmd)
    run_memtier(options)
    #os.system("sleep 15")
    #generate_report(process, options)
    #os.system("ssh 192.168.5.99 \"source /opt/sep41/sep_vars.sh ; emon -stop\"")





