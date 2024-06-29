#!/bin/bash
#Launch all servers

			./launch_server.py --ratio "1:4"  --scores=4-9 --mark data_${d}_p${p}_c${con} --host 192.168.5.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 5000000 -p $p -d $d --pclient=Yes
			./launch_server.py --ratio "1:4"  --scores=10-15 --mark data_${d}_p${p}_c${con} --host 192.168.6.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 5000000 -p $p -d $d
			./launch_server.py --ratio "1:4"  --scores=16-21 --mark data_${d}_p${p}_c${con} --host 192.168.7.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 5000000 -p $p -d $d
			./launch_server.py --ratio "1:4"  --scores=22-27 --mark data_${d}_p${p}_c${con} --host 192.168.8.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 5000000 -p $p -d $d
for con in "50" "500" 
do 
	for d in "64"
	do
		for p in "1"
		do
rm -rf ip*prt*.txt
			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=10-15 --mark ip6_${d}_p${p}_c${con} --host 192.168.6.99 --ccores=16-23 --port=all  --keymax=10000001 --con_num=$con -n 5000000 -p $p -d $d &
			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=16-21 --mark ip7_${d}_p${p}_c${con} --host 192.168.7.99 --ccores=8-15 --port=all  --keymax=10000001 --con_num=$con -n 5000000 -p $p -d $d &
			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=22-27 --mark ip8_${d}_p${p}_c${con} --host 192.168.8.99 --ccores=24-31 --port=all  --keymax=10000001 --con_num=$con -n 5000000 -p $p -d $d &
			./run_client_and_server_memtier_r1p1_emon.py --ratio "1:4"  --scores=4-9 --mark ip5_${d}_p${p}_c${con} --host 192.168.5.99 --ccores=0-7 --port=all  --keymax=10000001 --con_num=$con -n 5000000 -p $p -d $d
		done
	done

done
