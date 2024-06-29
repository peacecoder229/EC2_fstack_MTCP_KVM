#!/bin/bash
#Launch all servers

num=$1
host=$2
server="0-3"
ratio=$3
tag=$4

sleep 1
export SUT=$host

for con in "100" 
do 
	for d in  "512"
	do
		for p in "4"
		do
rm -rf ip*prt*.txt
sleep 3
		#for act in "ddio_tx2_rx2" "ddio_tx4_rx2_ex" "ddio_tx7_rx4_ex" "ddio_tx6_rx5_ex"
		for act in "build"
			do
			ssh -o ConnectTimeout=10 $SUT "echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'"
			sleep 5
			#ssh -o ConnectTimeout=10 SUT "/pnpdata/hwpdesire/${act}"
			sleep 2
			curport=9001
			#for i in {3..11}
			for i in {3..3} {5..6} {8..9} {11..11} {13..13} {15..16}
				do
				core=$server
				#ssh -f -o ConnectTimeout=60 client$i "/pnpdata2/redis_sriov/clientxmtcp.sh ${con} ${d} ${p} ${tag} ${core} $i $curport $num ${host} ${ratio} &> log_err.txt"
				sleep 1
				
				echo "Launched Client$i benchmarks"
			done
				
			echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'
			sleep 1
			./run_client_and_server_memtier_r1p1_emon.py --ratio ${ratio}  --scores=${core} --mark ip6_${act}_d${d} --host ${host} --ccores=0-21 --port=all  --keymax=1000001 --con_num=$con -n $num -p $p -d $d --sport 9001 --proto memcache_text
mkdir -p ${tag}_d${d}_c${con}

mv ip192.168.*   memtier_ip* ${tag}_d${d}_c${con}

		done

echo "Starting next Iteration of memtier Runs"
sleep 200 


		done
	done

done

echo "ALL client DONE!!!!"
