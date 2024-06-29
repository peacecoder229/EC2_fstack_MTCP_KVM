#!/bin/bash
#Launch all servers


con=$1
d=$2
p=$3
act=$4
core=$5
ID=$6
servport=$7
cd /pnpdata/redis_sriov


			echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'
			sleep 1
			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=${core} --mark ip6_${act}_d${d} --host 192.168.232.100 --ccores=1-2 --port=all  --keymax=1000001 --con_num=$con -n 500000 -p $p -d $d --sport ${servport} &
			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=${core} --mark ip6_${act}_d${d} --host 192.168.232.100 --ccores=3-4 --port=all  --keymax=1000001 --con_num=$con -n 500000 -p $p -d $d --sport ${servport} &
			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=${core} --mark ip6_${act}_d${d} --host 192.168.232.100 --ccores=5-6 --port=all  --keymax=1000001 --con_num=$con -n 500000 -p $p -d $d --sport ${servport}
mkdir -p case_${act}_d${d}

mv ip192.168.*   memtier_ip* case_${act}_d${d}

echo "CLINT${ID} DONE!!!!"
