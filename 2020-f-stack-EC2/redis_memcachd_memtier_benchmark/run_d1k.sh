#!/bin/bash
export runnuma="no"
sleep 2
for i in {1..2}
do
	#podman run --rm  --cpuset-cpus=31-38 --cpuset-mems=0 -e RUNTIME=120  stressapp:latest &
	k=$(( i*12-1 ))
       	./mc_sweep.sh 0-${k} drc_res $i
	sleep 10
done


for i in {1..2}
do
	#podman run --rm  --cpuset-cpus=31-38 --cpuset-mems=0 -e RUNTIME=120  stressapp:latest &
	k=$(( i*14-1 ))
       	./mc_sweep.sh 0-${k} drc_res $i
	sleep 10
done


for i in {1..2}
do
	#podman run --rm  --cpuset-cpus=31-38 --cpuset-mems=0 -e RUNTIME=120  stressapp:latest &
	k=$(( i*16-1 ))
       	./mc_sweep.sh 0-${k} drc_res $i
	sleep 10
done


for i in {1..2}
do
	#podman run --rm  --cpuset-cpus=31-38 --cpuset-mems=0 -e RUNTIME=120  stressapp:latest &
	k=$(( i*9-1 ))
       	./mc_sweep.sh 0-${k} drc_res $i
	sleep 10
done

for i in {1..2}
do
	#podman run --rm  --cpuset-cpus=31-38 --cpuset-mems=0 -e RUNTIME=120  stressapp:latest &
	k=$(( i*10-1 ))
       	./mc_sweep.sh 0-${k} drc_res $i
	sleep 10
done

for i in {1..3}
do
	#podman run --rm  --cpuset-cpus=31-38 --cpuset-mems=0 -e RUNTIME=120  stressapp:latest &
	k=$(( i*6-1 ))
       	./mc_sweep.sh 0-${k} drc_res $i
	sleep 10
done
echo "d1024 stress app on , NUMA OFF 12,9,6 " >> /root/redis_memcachd_memtier_benchmark/drc_res/d1k_instance_run_sweep.txt
