#!/bin/bash
echo "d128 stress app on , NUMA ON 12,9,6 " >> /root/redis_memcachd_memtier_benchmark/drc_res/instance_run_sweep.txt
export runnuma="yes"
sleep 2
for i in {0..8}
do
	stc=$i
	edc=$(( i+7 ))
       	./mc_sweep.sh ${stc}-${edc} drc_res 1
	sleep 10
done




for i in {0..16}
do
	stc=$i
	edc=$(( i+15 ))
       	./mc_sweep.sh ${stc}-${edc} drc_res 1
	sleep 10
done
