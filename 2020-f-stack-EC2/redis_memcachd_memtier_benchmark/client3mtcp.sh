#!/bin/bash
#Launch all servers


con=$1
d=$2
p=$3
act=$4
core=$5
ID=$6
servport=$7
n=$8
cd /pnpdata/redis_sriov


			echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'
			sleep 1
			./run_client_and_server_memtier_r1p1.py --ratio "1:4"  --scores=${core} --mark ip6_${act}_d${d}_c${con} --host 192.168.232.235 --ccores=0-15 --port=all  --keymax=1000001 --con_num=$con -n $n -p $p -d $d --sport ${servport}
mkdir -p  vmtcp_${act}_d${d}_c${con}

mv ip192.168.*   memtier_ip*  vmtcp_${act}_d${d}_c${con}

echo "CLINT${ID} DONE!!!!"
