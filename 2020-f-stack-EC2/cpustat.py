#!/usr/bin/env python3
import subprocess
import sys
import time




cores = sys.argv[1]
ts = sys.argv[2]
iteration = int(sys.argv[3])
outname = sys.argv[4]

out = open(outname, "w")


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




#cmd = "mpstat  -u -P 0-1,24-25 1 2 | tail -n 4 | awk \'{print $2 " " $3 + $4}\'"
cpucount = get_cores(cores)
corestat = "mpstat  -u -P " + cores + " " + ts +  "  " + str(iteration) +  "  | tail -n " + str(cpucount)
#print(corestat)
#out = open("metricfile", "w")
#cpustat = subprocess.Popen(cmd, stdout=out, shell=True)


def execute(cmd):
    cpustat = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    cpustat.wait()

    for l in cpustat.stdout.readlines():
        yield l.decode('utf-8')
        #print(l.decode('utf-8'))

for i in execute(corestat):
    cpuno = i.split()[1]
    usr = i.split()[3]
    ker = i.split()[5]
    #print("cpuno " + cpuno + " usr " + usr + " ker " + ker) 
    out.write("cpuno " + cpuno + " usr " + usr + " ker " + ker + "\n") 


#with open("metricfile", "r") as out:
#    for l in out:
#        print(l.split())

