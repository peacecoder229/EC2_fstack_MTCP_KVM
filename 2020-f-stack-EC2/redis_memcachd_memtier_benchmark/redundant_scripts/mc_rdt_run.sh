#!/bin/bash
pkill -9 memcached
./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 inst1${1} memcache_text 28-29 /root/redis_memcachd_memtier_benchmark/core_scale 2-5,58-61 9001 launchmemcache &
pids["1"]=$!
./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 inst2${1} memcache_text 30-31 /root/redis_memcachd_memtier_benchmark/core_scale 6-9,62-65 9002 launchmemcache &
pids["2"]=$!
./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 inst3${1} memcache_text 32-33 /root/redis_memcachd_memtier_benchmark/core_scale 10-13,66-69 9003 launchmemcache &
pids["3"]=$!

for pid in ${pids[*]}; do
	echo $pid
	wait $pid
done
echo "Loading done"

./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:4 inst1${1} memcache_text 28-45,84-91 /root/redis_memcachd_memtier_benchmark/core_scale 2-5,58-61 9001  &
pids["1"]=$!

./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:4 inst2${1} memcache_text 46-53,91-98 /root/redis_memcachd_memtier_benchmark/core_scale 6-9,62-65 9002  &
pids["2"]=$!
./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:4 inst3${1} memcache_text 54-61,99-106 /root/redis_memcachd_memtier_benchmark/core_scale 10-13,66-69 9003 &

pids["3"]=$!
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




