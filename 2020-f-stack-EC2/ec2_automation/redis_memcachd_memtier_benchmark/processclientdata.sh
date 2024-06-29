#!/bin/bash

cd /pnpdata2/redis_sriov/$1
rm -f ${1}_cl${2}.txt
sleep 1
grep Sets ip192.168.232.100* | awk '{print $1 " " $5 "  avg"}' >> ${1}_cl${2}.txt
sleep 1
grep Gets ip192.168.232.100* | awk '{print $1 " " $5 "  avg"}' >> ${1}_cl${2}.txt
sleep 1
grep "GET     " ip192.168.232.100* | grep 95. | sort -nk2 | tail -n 15 >> ${1}_cl${2}.txt
sleep 1
grep "SET     " ip192.168.232.100* | grep 95. | sort -nk2 | tail -n 15 >> ${1}_cl${2}.txt
sleep 1



