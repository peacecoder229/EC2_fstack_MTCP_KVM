#!/usr/bin/env python3

import subprocess
import sys
import time
import re

'''
arg1: cpus that needs to be moitored
arg2: ts in seconds for mpstat
arg3: no of iterations
arg4: outfile name
'''

def get_cores(c):
    cpu = list()
    seg = c.split(",")
    for s in seg:
        low,high = s.split("-")
        if low == None or high == None:
            cpu.append(s)
        else:
            for i in range(int(low), int(high)+1):
                cpu.append(i)

    return len(cpu)

def execute(cmd):
    cpustat = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    #print(cmd)
    cpustat.wait()

    for l in cpustat.stdout.readlines():
        yield l.decode('utf-8')
        #print(l.decode('utf-8'))

def get_cpu_stat(corestat):
    '''
    arg1: cpus that needs to be moitored
    arg2: ts in seconds for mpstat
    arg3: no of iterations
    arg4: outfile name
    '''
    for i in execute(corestat):
        cpuno = i.split()[1]
        usr = i.split()[3]
        ker = i.split()[5]
        #print("cpuno " + cpuno + " usr " + usr + " ker " + ker) 
        out.write("cpuno " + cpuno + " usr " + usr + " ker " + ker + "\n") 

#with open("metricfile", "r") as out:
#    for l in out:
#        print(l.split())

def get_wrk_stat(cmd):
    '''
    executes CMD and captures buffer
    and processes specific output
    numactl -C 64-71 ./wrk -t 8 -c 8000 -d 10s -L  http://localhost:80
    $1 cores $2 threads $3 con $4 duration $5 server
    '''
    for i in execute(cmd):
        match = re.search(r'(\d+) threads and (\d+) connections', i)
        if(match):
            thread = match.group(1)
            con = match.group(2)
            continue
        else:
            pass
            
        match = re.search(r'50%\s+(\d+.\d+)ms', i)
        if(match):
            p50 = match.group(1)
            continue
        else:
            pass
        match = re.search(r'75%\s+(\d+.\d+)ms', i)
        if(match):
            p75 = match.group(1)
            continue
        else:
            pass
        match = re.search(r'99%\s+(\d+.\d+)ms', i)
        if(match):
            p99 =  match.group(1)
            continue
        else:
            pass
        match = re.search(r'(\d+) requests in', i)
        if(match):
            QPS =  match.group(1)
            continue
        else:
            pass
    #print("Done")
    return (thread, con, p50, p75, p99, QPS)

def get_numa_stat(nstat):
    count = 1
    N0_prev = dict()
    N1_prev = dict()
    N0_cur = dict()
    N1_cur = dict()

    N0_prev['local'] =  0
    N1_prev['local'] =  0
    N0_prev['rem'] = 0
    N1_prev['rem'] =  0

    while(count < iteration):

        G = execute(nstat)
        local=next(G)
        remote=next(G)
        N0_cur['local'] = int(local.split()[1])
        N1_cur['local'] = int(local.split()[2])

        N0_cur['rem'] = int(remote.split()[1])
        N1_cur['rem'] = int(remote.split()[2])

        #print("Socket0 local =" + str(N0_cur['local'] - N0_prev['local']) + "Socket1 local =" + str(N1_cur['local'] - N1_prev['local']))
        out.write("Socket0 local =" + str(N0_cur['local'] - N0_prev['local']) + "  Socket1 local =" + str(N1_cur['local'] - N1_prev['local']) + "\n")
        out.write("Socket0 rem =" + str(N0_cur['rem'] - N0_prev['rem']) + "  Socket1 rem =" + str(N1_cur['rem'] - N1_prev['rem']) + "\n")

        N0_prev['local'] =  N0_cur['local']
        N1_prev['local'] =  N1_cur['local']
        N0_prev['rem'] = N0_cur['rem']
        N1_prev['rem'] =  N1_cur['rem']
        #print(next(G))
        #print(next(G))
        time.sleep(1)
        count+=1
    out.close()    

if __name__ == "__main__":

    if(len(sys.argv) < 5):
        print(get_wrk_stat.__doc__)
    else:
        cores = sys.argv[1]
        threads = sys.argv[2]
        con = sys.argv[3]
        dur = sys.argv[4]
        serv = sys.argv[5]

        cmd = "numactl --membind=1  --physcpubind=" + cores + " ./wrk -t " + threads + " -c " + con + " -d  " + dur + " -L " + serv   

        #cmd = "mpstat  -u -P 0-1,24-25 1 2 | tail -n 4 | awk \'{print $2 " " $3 + $4}\'"
        #print(corestat)
        #out = open("metricfile", "w")
        #cpustat = subprocess.Popen(cmd, stdout=out, shell=True)

        print(get_wrk_stat(cmd))
