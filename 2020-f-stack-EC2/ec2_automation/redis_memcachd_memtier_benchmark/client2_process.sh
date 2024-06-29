#!/bin/bash
#cd /pnpdata/redis_sriov/clnt2_files/

for dir in  "vanlin_con1_d1024"  "vanlin_con1_d2" "vanlin_con50_d1024" "vanlin_con50_d2"  "vanlin_con5_d1024" "vanlin_con5_d2";

do
cd /pnpdata/redis_sriov/clnt2_files/$dir
grep Sets ip192.168.232.100* | awk '{print $1 " " $5 "  avg"}' >> ${dir}_cl2.txt
sleep 1
grep Gets ip192.168.232.100* | awk '{print $1 " " $5 "  avg"}' >> ${dir}_cl2.txt
sleep 1
grep "GET     " ip192.168.232.100* | grep 95. | sort -nk2 | tail -n 15 >> ${dir}_cl2.txt
sleep 1
grep "SET     " ip192.168.232.100* | grep 95. | sort -nk2 | tail -n 15 >> ${dir}_cl2.txt
sleep 1
cp ${dir}_cl2.txt /pnpdata/redis_sriov/all_client_data
done
