#!/bin/bash
#/pnpdata/change_msr.py 0x199 0x1600 write
#echo "current cpu frequency is:"
#cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_cur_freq

echo "Test case",  "set_qps", "set_lat", "get_qps", "get_lat" >> memtier_total.csv

for ratio in  "1:4"
	do 
	if [ $1 -eq 1 ]; then		
         ./run_memtier_updated.py --ratio $ratio --mark host --host 127.0.0.1
        #do ./run_memtier_updated.py --ratio $ratio --mark VMNopatch$cmd --remote 1
        elif [ $1 -eq 2 ]; then
	./run_memtier_updated.py --ratio $ratio --mark cl29vm1 --host 192.168.5.100 --loop_num 2 &
	./run_memtier_updated.py --ratio $ratio --mark cl29vm2 --host 192.168.6.100 --loop_num 2 &
	./run_memtier_updated.py --ratio $ratio --mark cl29vm3 --host 192.168.7.100 --loop_num 2 &
	./run_memtier_updated_emon.py --ratio $ratio --mark cl29vm4 --host 192.168.8.100 --loop_num 2 &

	elif [ $1 -eq 3 ]; then
	./run_memtier_updated.py --ratio $ratio --mark virtio --host 192.168.122.42
	fi
        done
done
#taskset -c 5 memtier_benchmark -p 6379 --ratio=1:4 --pipeline=20 -d 1024 -c 100 --key-maximum 1000000 --key-pattern G:G -n 1000000

