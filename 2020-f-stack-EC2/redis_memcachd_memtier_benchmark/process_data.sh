#!/bin/bash
cd /pnpdata/redis_sriov
grep 99.99 ${1}/ip192.168.232.100* | sort -nk2 | awk  '{print $1 " "  $2 "   " $3" "}' | tail -n 30 > /pnpdata/cl${2}.txt
sleep 2
grep Sets ${1}/ip192.168.232.100* | awk '{print $1 " " $5 "  avg"}' >> /pnpdata/cl${2}.txt
#scp cl${2}.txt root@client2:/pnpdata/
