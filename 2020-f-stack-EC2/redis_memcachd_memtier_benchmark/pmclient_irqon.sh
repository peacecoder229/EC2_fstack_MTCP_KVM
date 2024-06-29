#!/bin/bash
#Launch all servers

			./launch_server.py --ratio "1:4"  --scores=6-7 --mark data_${d}_p${p}_c${con} --host 192.168.5.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 50000 -p $p -d $d --pclient=Yes
			./launch_server.py --ratio "1:4"  --scores=2-3 --mark data_${d}_p${p}_c${con} --host 192.168.6.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 50000 -p $p -d $d
			./launch_server.py --ratio "1:4"  --scores=4-5 --mark data_${d}_p${p}_c${con} --host 192.168.6.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 50000 -p $p -d $d
			./launch_server.py --ratio "1:4"  --scores=8-9 --mark data_${d}_p${p}_c${con} --host 192.168.6.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 50000 -p $p -d $d
			./launch_server.py --ratio "1:4"  --scores=10-11 --mark data_${d}_p${p}_c${con} --host 192.168.7.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 50000 -p $p -d $d
			./launch_server.py --ratio "1:4"  --scores=12-13 --mark data_${d}_p${p}_c${con} --host 192.168.1.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 50000 -p $p -d $d
			./launch_server.py --ratio "1:4"  --scores=14-15 --mark data_${d}_p${p}_c${con} --host 192.168.2.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 50000 -p $p -d $d
			./launch_server.py --ratio "1:4"  --scores=16-17 --mark data_${d}_p${p}_c${con} --host 192.168.3.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 50000 -p $p -d $d
sleep 2

echo "ALL Servers launched"


sleep 1


for con in "320" 
do 
	for d in  "2"
	do
		for p in "1"
		do
rm -rf ip*prt*.txt
sleep 3
		#for act in "ddio_tx2_rx2" "ddio_tx4_rx2_ex" "ddio_tx7_rx4_ex" "ddio_tx6_rx5_ex"
		for act in "turbo_c6_on"
		   do
			ssh 192.168.5.99 "echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'"
			sleep 5
			ssh 192.168.5.99 "/pnpdata/hwpdesire/${act}"
			sleep 2
			echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'
			sleep 1
			ssh -f 10.242.51.161 "/pnpdata/redis_sriov/client_irqon.sh ${con} ${d} ${p} ${act}"
			sleep 1
			echo "Launched Client32 benchmarks"

			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=2-3 --mark ip1_${act}_d${d} --host 192.168.5.99 --ccores=17-18 --port=all  --keymax=1000001 --con_num=$con -n 50000 -p $p -d $d &
			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=6-7 --mark ip1_${act}_d${d} --host 192.168.5.99 --ccores=1-2 --port=all  --keymax=1000001 --con_num=$con -n 50000 -p $p -d $d &
			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=8-9 --mark ip2_${act}_d${d} --host 192.168.6.99 --ccores=3-4 --port=all  --keymax=1000001 --con_num=$con -n 50000 -p $p -d $d &
			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=10-11 --mark ip3_${act}_d${d} --host 192.168.7.99 --ccores=5-6 --port=all  --keymax=1000001 --con_num=$con -n 50000 -p $p -d $d &

			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=2-3 --mark ip4_${act}_d${d} --host 192.168.5.99 --ccores=19-20 --port=all  --keymax=1000001 --con_num=$con -n 50000 -p $p -d $d &
			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=6-7 --mark ip4_${act}_d${d} --host 192.168.5.99 --ccores=9-10 --port=all  --keymax=1000001 --con_num=$con -n 50000 -p $p -d $d &
			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=8-9 --mark ip5_${act}_d${d} --host 192.168.6.99 --ccores=11-12 --port=all  --keymax=1000001 --con_num=$con -n 50000 -p $p -d $d &
			./run_client_and_server_memtier_r1p1_emon.py --ratio "1:4"  --scores=10-11 --mark ip6_${act}_d${d} --host 192.168.7.99 --ccores=13-14 --port=all  --keymax=1000001 --con_num=$con -n 50000 -p $p -d $d

mkdir -p case_${act}_d${d}

mv ip192.168.*   memtier_ip* case_${act}_d${d}

		done

echo "Starting next Iteration of memtier Runs"
sleep 10 


		done
	done

done

echo "ALL client DONE!!!!"
