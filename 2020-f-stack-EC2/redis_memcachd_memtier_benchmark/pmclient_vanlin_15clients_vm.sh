#!/bin/bash
#Launch all servers

num=$1
host=$2
server="0-3"
ratio=$3
tag=$4

#			./launch_server.py --ratio ${ratio}  --scores=${server}  --host ${host}  --port=all  --keymax=10000001 --con_num=10  --pclient=Yes
sleep 10

echo "ALL Servers launched about 300 sec passes"


sleep 1


for con in "50" 
do 
	for d in  "10"
	do
		for p in "4"
		do
rm -rf ip*prt*.txt
sleep 3
		#for act in "ddio_tx2_rx2" "ddio_tx4_rx2_ex" "ddio_tx7_rx4_ex" "ddio_tx6_rx5_ex"
		for act in "build"
			do
			#ssh -o ConnectTimeout=10 192.168.100.200 "echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'"
			sleep 5
			#ssh -o ConnectTimeout=10 SUT "/pnpdata/hwpdesire/${act}"
			sleep 2
			curport=9001
			for i in {3..11}
				do
				core=$server
				#ssh -f -o ConnectTimeout=60 client$i "/pnpdata2/redis_sriov/clientxmtcp.sh ${con} ${d} ${p} ${act} ${core} $i $curport $num ${host} ${ratio} &> log_err.txt"
				sleep 1
				
				echo "Launched Client$i benchmarks"
			done
				
			echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'
			sleep 1
			./run_client_and_server_memtier_r1p1_emon.py --ratio ${ratio}  --scores=${core} --mark ip6_${act}_d${d} --host ${host} --ccores=0-7 --port=all  --keymax=1000001 --con_num=$con -n $num -p $p -d $d --sport 9001 --proto memcache_text
mkdir -p ${tag}_d${d}_c{con}

mv ip192.168.*   memtier_ip* ${tag}_d${d}_c{con}

		done

echo "Starting next Iteration of memtier Runs"
sleep 200 


		done
	done

done

echo "ALL client DONE!!!!"
