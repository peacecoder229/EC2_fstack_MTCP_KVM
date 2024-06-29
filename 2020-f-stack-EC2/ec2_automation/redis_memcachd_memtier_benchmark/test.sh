#!/bin/bash
#Launch all servers

server=0-0
act=vmmtcp
sleep 1


for con in "250" 
do 
	for d in  "2"
	do
		for p in "4"
		do
rm -rf ip*prt*.txt
sleep 3
		#for act in "ddio_tx2_rx2" "ddio_tx4_rx2_ex" "ddio_tx7_rx4_ex" "ddio_tx6_rx5_ex"
			curport=9001
				
			echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'
			sleep 1
			./run_client_and_server_memtier_r1p1_emon.py --ratio "1:4"  --scores=${core} --mark ip6_${act}_d${d} --host 192.168.232.235 --ccores=0-15 --port=all  --keymax=1000001 --con_num=$con -n 15000 -p $p -d $d --sport 9001
mkdir -p mtcp_${act}_d${d}

mv ip192.168.*   memtier_ip* mtcp_${act}_d${d}

		done

echo "Starting next Iteration of memtier Runs"
sleep 60 


		done
	done


echo "ALL client DONE!!!!"
