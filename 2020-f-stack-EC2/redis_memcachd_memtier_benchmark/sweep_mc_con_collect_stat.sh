#!/bin/bash

#case=( ["8"]="1" ["16"]="2" ["24"]="3"  ["28"]="2")
case=(["28"]="2" ["56"]="4" ["32"]="2")
#for core in "8" "16" "24"
hypt=${1}

for core in "28"
do

pkill -9 memcached

# Need to update start of physical core i and start of HT cores j 
# if a system with different number of cores are used

i=0
j=56
serv=0
port=9000
#below for taking core boundaryies for collecting perf stat 
perfstep=$(( core/2 ))
perfstep=$(( perfstep-1 ))

ins=${case[${core}]}
cpi=$(( core/ins ))
#Please note without HT ON actual no of cores per instance is ht or cpi/2
ht=$(( cpi/2 ))
step=$(( ht-1 ))
#ccore change multiplier from 1 to 2 for ht runs
#ccore=$(( ht*1 ))
ccore=$(( ht*2 ))
cstep=$(( ccore/2-1 ))
#below cores on the socket 1 are used for metier_bench launch

ms=28
me=29

# Starting of the load phase

while [ "${serv}" -lt "${ins}" ]
do
#server cores
	stc1=${i}
	stc2=${j}
	edc1=$(( stc1+step ))
	edc2=$(( stc2+step ))
	port=$(( port+1 ))
#client cores
#each amd_mem instance is run with a specific port no  and /run_client_and_server_memtier_r1p1_emon.py uses that port no only to launch all clients.

#echo "./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 inst${serv}${core} memcache_text ${ms}-${me} /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1} ${port} "4" launchmemcache & "
if [ "$hypt" == "on" ]
then

	export hypt="on"
	echo "./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 inst${serv}${core} memcache_text ${ms}-${me} /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} "4" launchmemcache &"
	./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 inst${serv}${core} memcache_text ${ms}-${me} /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} "4" launchmemcache &

else
	 export hypt="off"

	echo "./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 inst${serv}${core} memcache_text ${ms}-${me} /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1} ${port} "4" launchmemcache &"
	./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 inst${serv}${core} memcache_text ${ms}-${me} /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1} ${port} "4" launchmemcache &
fi
#echo "./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 inst${serv}${core} memcache_text ${ms}-${me} /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} "4" launchmemcache &"
#./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 inst${serv}${core} memcache_text ${ms}-${me} /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} "4" launchmemcache &
wrpids[$serv]=$!
serv=$(( serv+1 ))
i=$(( edc1+1 ))
j=$(( edc2+1 ))
ms=$(( ms+2 ))
me=$(( me+2 ))
done

for pid in ${wrpids[*]}; do
	echo $pid
	wait $pid
done
echo "End of Loading phase"

sleep 5


# for each core config run three connection experiments

#for connections in "2" "4" "8" "16"
for connections in "16"
do

i=0
j=56
serv=0
port=9000
ci=28
cj=84
perfend=$(( 56+perfstep ))
if [ "$hypt" == "on" ]
then
	perf="phton"
 	echo "perf stat -D 10000 -C 0-${perfstep},56-${perfend} -e tsc,r0300,r00c0,cycle_activity.stalls_mem_any -I2000  --interval-count=60 -o ${perf}${core}_${ins}_${connections}_stat.txt &"
 #	perf stat -D 10000 -C 0-${perfstep},56-${perfend} -e tsc,r0300,r00c0,cycle_activity.stalls_mem_any -I2000  --interval-count=60 -o ${perf}${core}_${ins}_${connections}_stat.txt &

else
	perf="phtoff"
 	echo "perf stat -D 30000 -C 0-${perfstep} -e tsc,r0300,r00c0,cycle_activity.stalls_mem_any -I2000  --interval-count=60 -o ${perf}${core}_${ins}_${connections}_stat.txt &"
 #	perf stat -D 30000 -C 0-${perfstep} -e tsc,r0300,r00c0,cycle_activity.stalls_mem_any -I2000  --interval-count=60 -o ${perf}${core}_${ins}_${connections}_stat.txt &

fi

 sleep 1

cd /root/redis_memcachd_memtier_benchmark/core_scale;  rm -rf inst*; sleep 1;
rm -f ip127.0.0.1prt900*
sleep 1
echo "All previous inst files being  removed"
cd -
sleep 5

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
#003c is  thread cycles when thread is not in halt state and 013c core crystal clocks when thread is unhalted
#CPU_CLK_UNHALTED.REF_TSC EV=x00 UMASK=0x03 so r0300
#CPU_CLK_UNHALTED.REF_XCLK r013c crystal clock
if [ "$hypt" == "on" ]
then

	echo "./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:4 inst${serv}${core} memcache_text ${cstc1}-${cedc1},${cstc2}-${cedc2}  /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} ${connections} &"
	./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:4 inst${serv}${core} memcache_text ${cstc1}-${cedc1},${cstc2}-${cedc2}  /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} ${connections} &

else

	echo "./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:4 inst${serv}${core} memcache_text ${cstc1}-${cedc1},${cstc2}-${cedc2}  /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1} ${port} ${connections} &"
	./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:4 inst${serv}${core} memcache_text ${cstc1}-${cedc1},${cstc2}-${cedc2}  /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1} ${port} ${connections} &

fi


#echo "./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:4 inst${serv}${core} memcache_text ${cstc1}-${cedc1},${cstc2}-${cedc2}  /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} ${connections} &"
#./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:4 inst${serv}${core} memcache_text ${cstc1}-${cedc1},${cstc2}-${cedc2}  /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} ${connections} &


#mapping of ports.. port(sweep)->curport-(amd_mem)>servport( client_memt)->memtier_client_server_modules

ldpids[$serv]=$!
serv=$(( serv+1 ))
i=$(( edc1+1 ))
j=$(( edc2+1 ))

ci=$(( cedc1+1 ))
cj=$(( cedc2+1 ))

done


for pid in ${ldpids[*]}; do
	 echo $pid
	 wait $pid
 done
 sleep 2

 echo "FUll read/write done"
sleep 1 
echo "processing"
cd /root/redis_memcachd_memtier_benchmark/core_scale
#./process_stats_of_file.py  --filepattern="inst*${core}_con${connections}_d512.txt" --indexpattern="GET" --statpos=1 --indexpos=0 --outfile=testsum
./process_stats_of_file.py  --filepattern="inst[0-1]${core}_con${connections}_d512.txt" --indexpattern="GET" --statpos=1 --indexpos=0 --outfile=testsum
reshp=$(cat testsum | grep -v "filename" | awk -F, '{sum += $4; sum2 += $6} END {print sum/3 " " sum2/3}')

hpthrput=$(cat inst0${core}_con${connections}_d512.txt inst1${core}_con${connections}_d512.txt | grep "Totals" | awk '{sumt += $2} END {print sumt}')

./process_stats_of_file.py  --filepattern="inst[2-3]${core}_con${connections}_d512.txt" --indexpattern="GET" --statpos=1 --indexpos=0 --outfile=testsumlp
reslp=$(cat testsumlp | grep -v "filename" | awk -F, '{sum += $4; sum2 += $6} END {print sum/3 " " sum2/3}')

sleep 1

#rm -f ip127.0.0.1prt900*

cd -
metric=$(./process_stats_of_perf_r1.py  --filepattern="${perf}${core}_${ins}_${connections}_stat.txt" --indexpattern="tsc,r0300,r00c0,stalls_mem_any" --statpos=1  --indexpos=2 | grep -v "file")
sleep 1
#echo "${core} ${ins} ${connections} ${res}  ${metric}" >> memc_scale_sum_halfc_HT_july5th_lphp.txt
echo "${LPMB} ${LPW} ${core} ${connections} ${ins} ${connections} ${reshp} ${hpthrput} ${reslp}  ${metric} ${hypt}" >> memc_hp_lp_mix_ht_impact.txt

sleep 1
#deleting all files with SET / GET processed data cannot be done from amd_mem script as multiple of them are running in parallel
#rm -f ip127.0.0.1prt900*

done

done


