#!/bin/bash
#pkill -9 memcached

i=0
j=56
serv=0
port=9000

core=$1
ins=$2
cpi=$(( core/ins ))
ht=$(( cpi/2 ))
step=$(( ht-1 ))
ccore=$(( ht*2 ))
cstep=$(( ccore/2-1 ))
# using  cores from the other socket to launch memtier_benchmark strats with 28-29.. then 30-31 etc.
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


#echo "./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 inst${serv}${3} memcache_text ${ms}-${me} /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} launchmemcache & "
#./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 inst${serv}${3} memcache_text ${ms}-${me} /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} launchmemcache &
if [ "$4" == "ht" ]
then

	echo "./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 inst${serv}${3} memcache_text ${ms}-${me} /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} "2"  launchmemcache &"
	./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 inst${serv}${3} memcache_text ${ms}-${me} /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} "2"  launchmemcache &
else

	echo "./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 inst${serv}${3} memcache_text ${ms}-${me} /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1} ${port} "2"  launchmemcache &"
	./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 inst${serv}${3} memcache_text ${ms}-${me} /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1} ${port} "2"  launchmemcache &
fi

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


#echo "./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:4 inst${serv}${3} memcache_text ${cstc1}-${cedc1},${cstc2}-${cedc2}  /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} &"
#./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:4 inst${serv}${3} memcache_text ${cstc1}-${cedc1},${cstc2}-${cedc2}  /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} &
if [ "$4" == "ht" ]
then
	echo "./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:4 inst${serv}${3} memcache_text ${cstc1}-${cedc1},${cstc2}-${cedc2}  /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} "8" &"
	./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:4 inst${serv}${3} memcache_text ${cstc1}-${cedc1},${cstc2}-${cedc2}  /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1},${stc2}-${edc2} ${port} "8" &
else


	echo "./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:4 inst${serv}${3} memcache_text ${cstc1}-${cedc1},${cstc2}-${cedc2}  /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1} ${port} "8" &"
	./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:4 inst${serv}${3} memcache_text ${cstc1}-${cedc1},${cstc2}-${cedc2}  /root/redis_memcachd_memtier_benchmark/core_scale ${stc1}-${edc1} ${port} "8" &

fi

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
#cd /root/redis_memcachd_memtier_benchmark/core_scale
#./process_stats_of_file.py  --filepattern="*${1}_con32_d512.txt" --indexpattern="SET" --statpos=1 --indexpos=0 --outfile=testsum
#res=$(cat testsum | grep -v "filename" | awk -F, '{sum += $4; sum2 += $6} END {print sum/3 " " sum2/3}')
#echo "Results are ${res}"
#cd -




