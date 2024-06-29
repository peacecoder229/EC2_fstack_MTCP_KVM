#!/bin/bash
#Launch all servers

			./launch_server.py --ratio "1:4"  --scores=0-17 --mark data_${d}_p${p}_c${con} --host 192.168.232.100 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 50000 -p $p -d $d --pclient=Yes
sleep 2

echo "ALL Servers launched"


sleep 1


for con in  "300" 
do 
	for d in  "2"
	do
		for p in "1"
		do
rm -rf ip*prt*.txt
sleep 3
		#for act in "ddio_tx2_rx2" "ddio_tx4_rx2_ex" "ddio_tx7_rx4_ex" "ddio_tx6_rx5_ex"
		for act in "nic_opt_set"
			do
			ssh -o ConnectTimeout=10 SUT "echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'"
			sleep 5
			ssh -o ConnectTimeout=10 SUT "/pnpdata/hwpdesire/${act}"
			sleep 2
			k=0
			curport=9002
			for i in {3..16}
				do
				curport=$((curport+1))
				core=$(($i-1))-$(($i-1))
				ssh -f -o ConnectTimeout=60 client$i "/pnpdata/redis_sriov/client_drc.sh ${con} ${d} ${p} ${act} ${core} $i $curport &> log_err.txt"
				sleep 1
				
				echo "Launched Client$i benchmarks"
			done
				
			echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'
			sleep 1
			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=0-0 --mark ip6_${act}_d${d}_c${con} --host 192.168.232.100 --ccores=1-1 --port=all  --keymax=1000001 --con_num=$con -n 500000 -p $p -d $d --sport 9001 &
			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=1-1 --mark ip6_${act}_d${d}_c${con} --host 192.168.232.100 --ccores=2-2 --port=all  --keymax=1000001 --con_num=$con -n 500000 -p $p -d $d --sport 9002 &
			./run_client_and_server_memtier_r1p1_emon.py --ratio "1:4"  --scores=16-16 --mark ip6_${act}_d${d}_c${con} --host 192.168.232.100 --ccores=3-3 --port=all  --keymax=1000001 --con_num=$con -n 500000 -p $p -d $d --sport 9017
mkdir -p case_${act}_d${d}_c${con}

mv ip192.168.*   memtier_ip* case_${act}_d${d}_c${con}

		done

echo "Starting next Iteration of memtier Runs"
sleep 200 


		done
	done

done

echo "ALL client DONE!!!!"
