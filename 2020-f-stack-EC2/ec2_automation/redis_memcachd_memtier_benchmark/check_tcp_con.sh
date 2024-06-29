#!/bin/bash
#Launch all servers

server="0-15"


			./launch_server.py --ratio "1:4"  --scores=${server}  --host 192.168.232.100  --port=all  --keymax=10000001 --con_num=10  --pclient=Yes
sleep 10

echo "ALL Servers launched about 300 sec passes"


sleep 1
con=50
d=2
act=ddio_tx2_rx2

rm -rf ip*prt*.txt

sleep 3
			ssh -o ConnectTimeout=10 SUT "echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'"
			sleep 5
			ssh -o ConnectTimeout=10 SUT "/pnpdata/hwpdesire/${act}"
			sleep 2
			curport=9001
			for i in {3..16}
				do
				core=$server
				ssh -f -o ConnectTimeout=60 client$i "/pnpdata2/redis_sriov/clientxmtcp.sh ${con} ${d} ${p} ${act} ${core} $i $curport &> log_err.txt"
				sleep 1
				
				echo "Launched Client$i benchmarks"
			done
				
			echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'
			sleep 1
		while  :
		do
			./run_client_and_server_memtier_r1p1_emon.py --ratio "1:4"  --scores=${core} --mark ip6_${act}_d${d} --host 192.168.232.100 --ccores=0-7 --port=all  --keymax=1000001 --con_num=$con -n 50 -p $p -d $d --sport 9001

		done

mkdir -p vanlin_${act}_d${d}

mv ip192.168.*   memtier_ip* case_${act}_d${d}


echo "Starting next Iteration of memtier Runs"
sleep 200 



echo "ALL client DONE!!!!"
