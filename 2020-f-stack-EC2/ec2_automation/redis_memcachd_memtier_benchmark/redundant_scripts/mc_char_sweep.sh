#!/bin/bash

#case=( ["8"]="1" ["16"]="2" ["24"]="3"  ["28"]="2")
case=(["28"]="2" ["56"]="4")
#for core in "8" "16" "24"
for core in "28" "56"
do

pkill -9 memcached

i=0
j=56
serv=0
port=9000
perfstep=$(( core/2 ))
perfstep=$(( perfstep-1 ))

ins=${case[${core}]}
cpi=$(( core/ins ))
ht=$(( cpi/2 ))
step=$(( ht-1 ))
ccore=$(( ht*1 ))
cstep=$(( ccore-1 ))
ms=28
me=29

while [ "${serv}" -lt "${ins}" ]
do
#server cores
	stc1=${i}
	stc2=${j}
	edc1=$(( stc1+step ))
	edc2=$(( stc2+step ))
	port=$(( port+1 ))
#client cores


./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 inst${serv}${core} memcache_text ${ms}-${me} /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} launchmemcache &
echo "./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 inst${serv}${core} memcache_text ${ms}-${me} /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} launchmemcache & "
pids[$serv]=$!
serv=$(( serv+1 ))
i=$(( edc1+1 ))
j=$(( edc2+1 ))
ms=$(( ms+2 ))
me=$(( me+2 ))
done

for pid in ${pids[*]}; do
	echo $pid
	wait $pid
done
echo "Loading done"

i=0
j=56
serv=0
port=9000
ci=28
cj=84

while [ "$serv" -lt "${ins}" ]

do
#server cores
	stc1=${i}
	stc2=${j}
	edc1=$(( stc1+step ))
	edc2=$(( stc2+step ))
	port=$(( port+1 ))
#client cores
	cstc1=${ci}
	cstc2=${cj}
	cedc1=$(( cstc1+cstep ))
	cedc2=$(( cstc2+cstep ))
	perfe=$(( 56+perfstep ))
 perf stat -D 10000 -C 0-${perfstep},56-${perfe} -e tsc,r003c,r00c0,cycle_activity.stalls_mem_any -I2000  --interval-count=150 -o runc${core}_${ins}_stat.txt &

./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:4 inst${serv}${core} memcache_text ${cstc1}-${cedc1},${cstc2}-${cedc2}  /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} &
echo "./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:4 inst${serv}${core} memcache_text ${cstc1}-${cedc1},${cstc2}-${cedc2}  /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} &"

pids[$serv]=$!
serv=$(( serv+1 ))
i=$(( edc1+1 ))
j=$(( edc2+1 ))

ci=$(( cedc1+1 ))
cj=$(( cedc2+1 ))

done


for pid in ${pids[*]}; do
	 echo $pid
	 wait $pid
 done
 echo "FUll read/write done"
sleep 1 
echo "processing"
cd /root/redis_memcachd_memtier_benchmark/core_scale
./process_stats_of_file.py  --filepattern="*${core}_con16_d512.txt" --indexpattern="SET" --statpos=1 --indexpos=0 --outfile=testsum
res=$(cat testsum | grep -v "filename" | awk -F, '{sum += $4; sum2 += $6} END {print sum/3 " " sum2/3}')
cd -
echo "${core} ${ins} ${res}" >> memc_scale_sum_halfc.txt
done




