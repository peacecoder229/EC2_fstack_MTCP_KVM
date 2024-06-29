#!/bin/bash
#Launch all servers

			./launch_server.py --ratio "1:4"  --scores=1-4 --mark data_${d}_p${p}_c${con} --host 192.168.5.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 50000000 -p $p -d $d --pclient=Yes
			./launch_server.py --ratio "1:4"  --scores=5-8 --mark data_${d}_p${p}_c${con} --host 192.168.6.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 50000000 -p $p -d $d
			./launch_server.py --ratio "1:4"  --scores=9-12 --mark data_${d}_p${p}_c${con} --host 192.168.7.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 50000000 -p $p -d $d
			./launch_server.py --ratio "1:4"  --scores=13-16 --mark data_${d}_p${p}_c${con} --host 192.168.8.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 50000000 -p $p -d $d

sleep 2

echo "ALL Servers launched"

sleep 2

mv memtier_ip*.csv old_data

sleep 1

for con in "500" 
do 
	for d in  "64" "128"
	do
		for p in "1"
		do
rm -rf ip*prt*.txt
sleep 3
		for act in "ddio_2way" "ddio_6way" "ddio_9way"
		   do
			ssh 192.168.5.99 "echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'"
			sleep 5
			ssh 192.168.5.99 "/pnpdata/hwpdesire/${act}"
			sleep 2

			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=1-4 --mark ip6_${act}_d${d} --host 192.168.6.99 --ccores=20-23 --port=all  --keymax=1000001 --con_num=$con -n 50000 -p $p -d $d &
			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=5-8 --mark ip7_${act}_d${d} --host 192.168.7.99 --ccores=16-19 --port=all  --keymax=1000001 --con_num=$con -n 50000 -p $p -d $d &
			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=9-12 --mark ip8_${act}_d${d} --host 192.168.8.99 --ccores=4-7 --port=all  --keymax=1000001 --con_num=$con -n 50000 -p $p -d $d &
			./run_client_and_server_memtier_r1p1_emon.py --ratio "1:4"  --scores=13-16 --mark ip5_${act}_d${d} --host 192.168.5.99 --ccores=0-3 --port=all  --keymax=1000001 --con_num=$con -n 50000 -p $p -d $d

sleep 100

mkdir -p case_${act}_d${d}

mv ip192.168.*   memtier_ip* case_${act}_d${d}

		done

echo "Starting next Iteration of memtier Runs"
sleep 30 


		done
	done

done

echo "DONE!!!!"
