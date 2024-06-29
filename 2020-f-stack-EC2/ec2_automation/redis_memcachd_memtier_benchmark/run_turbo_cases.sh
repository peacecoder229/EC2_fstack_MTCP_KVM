#!/bin/bash
#Launch all servers

			./launch_server.py --ratio "1:4"  --scores=8-12 --mark data_${d}_p${p}_c${con} --host 192.168.5.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 50000000 -p $p -d $d --pclient=Yes
			./launch_server.py --ratio "1:4"  --scores=13-17 --mark data_${d}_p${p}_c${con} --host 192.168.6.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 50000000 -p $p -d $d
			./launch_server.py --ratio "1:4"  --scores=18-22 --mark data_${d}_p${p}_c${con} --host 192.168.7.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 50000000 -p $p -d $d
			./launch_server.py --ratio "1:4"  --scores=23-27 --mark data_${d}_p${p}_c${con} --host 192.168.8.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 50000000 -p $p -d $d

sleep 2

echo "ALL Servers launched"

sleep 2

mv memtier_ip*.csv old_data

sleep 1

for con in "500" 
do 
	for d in "64"
	do
		for p in "1"
		do
rm -rf ip*prt*.txt
sleep 3

		 for act in "2p1_c6_off"  "2p1_c6_on" "2p1_c6_off_r2" "2p1_c6_on_r2" "2p1_c6_off_r3" "2p1_c6_on_r3" "2p4_c6_off" "2p4_c6_on" "2p4_c6_off_r2" "2p4_c6_on_r2" "2p4_c6_off_r3" "2p4_c6_on_r3" "turbo_c6_off_r3"  "turbo_c6_on_r3" "turbo_c6_off_r2"  "turbo_c6_on_r2" "turbo_c6_off"  "turbo_c6_on" 
		   do
			ssh 192.168.5.99 "echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'"
			sleep 5
			ssh 192.168.5.99 "/pnpdata/hwpdesire/${act}"
			sleep 2

			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=8-12 --mark ip6_${act} --host 192.168.6.99 --ccores=16-23 --port=all  --keymax=1000001 --con_num=$con -n 50000 -p $p -d $d &
			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=13-17 --mark ip7_${act} --host 192.168.7.99 --ccores=8-15 --port=all  --keymax=1000001 --con_num=$con -n 50000 -p $p -d $d &
			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=18-22 --mark ip8_${act} --host 192.168.8.99 --ccores=24-31 --port=all  --keymax=1000001 --con_num=$con -n 50000 -p $p -d $d &
			./run_client_and_server_memtier_r1p1_emon.py --ratio "1:4"  --scores=23-27 --mark ip5_${act} --host 192.168.5.99 --ccores=0-7 --port=all  --keymax=1000001 --con_num=$con -n 50000 -p $p -d $d

sleep 100

mkdir -p case_${act}

mv ip192.168.*   memtier_ip* case_${act}

		done

echo "Starting next Iteration of memtier Runs"
sleep 30 


		done
	done

done

echo "DONE!!!!"
