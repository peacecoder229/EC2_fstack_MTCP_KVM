#!/usr/bin/env python3
import subprocess
import sys
import time
import re


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
    cpustat.wait()

    for l in cpustat.stdout.readlines():
        yield l.decode('utf-8')
        #print(l.decode('utf-8'))





def cpustat(corestat, out):
    for i in execute(corestat):
        cpuno = i.split()[1]
        usr = i.split()[2]
        ker = i.split()[4]
        soft = i.split()[7]
    #print("cpuno " + cpuno + " usr " + usr + " ker " + ker) 
        out.write("cpuno " + cpuno + " usr " + usr + " ker " + ker +  " sirq " + soft + "\n") 


#with open("metricfile", "r") as out:
#    for l in out:
#        print(l.split())
def numastat(nstat, iteration, out):
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
    if(len(sys.argv) >= 5):
        tool=sys.argv[1]
        cores = sys.argv[2]
        ts = sys.argv[3]
        iteration = int(sys.argv[4])
        if(len(sys.argv) == 6):
            outname = sys.argv[5]
        else:
            outname = None
    else:
        print("Options are arg1=cpu or numa arg2=cpu-cores, arg3=timestap, arg4=iteration , arg5=file name\n")
        exit(1)


    out = open(outname, "w") if outname else sys.stdout

#cmd = "mpstat  -u -P 0-1,24-25 1 2 | tail -n 4 | awk \'{print $2 " " $3 + $4}\'"
    cpucount = get_cores(cores)
    corestat = "mpstat  -u -P " + cores + " " + ts +  "  " + str(iteration) +  "  | tail -n " + str(cpucount)
    print(corestat)
#out = open("metricfile", "w")
#cpustat = subprocess.Popen(cmd, stdout=out, shell=True)
#above cpustat does print the last lines which shows avg of the samples data

    nstat = "numastat | tail -n 2"

    if re.match("numa", tool):
        numastat(nstat, iteration, out)
    elif re.match("cpu", tool):
        cpustat(corestat, out)
    else:
        print("Tool option does not match numa or cpu\n")
        print("Options are arg1=cpu or numa arg2=cpu-cores, arg3=timestap, arg4=iteration , arg5=file name\n")






