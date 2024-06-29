#!/bin/bash

for dir in "vanlin_con1_d1024"  "vanlin_con1_d2" "vanlin_con50_d1024" "vanlin_con50_d2"  "vanlin_con5_d1024"  "vanlin_con5_d2";
do

for i in {3..16};

do ssh client$i "cd /pnpdata2/redis_sriov ; ./processclientdata.sh $dir $i " ; done

done

echo "Clientside processing Done"
sleep 5

echo "Copying processed files"

mkdir /pnpdata/redis_sriov/all_client_data
for i in {3..16}; do scp root@client$i:/pnpdata2/redis_sriov/$dir/${dir}_cl${i}.txt /pnpdata/redis_sriov/all_client_data; done

sleep 1

cd /pnpdata/redis_sriov/clnt2_files/

for dir in  "vanlin_con1_d1024"  "vanlin_con1_d2" "vanlin_con50_d1024" "vanlin_con50_d2"  "vanlin_con5_d1024" "vanlin_con5_d2";

do
cd $dir
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

