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
host=$9
ratio=${10}
proto=${11}
ccore=${12}
dir=${13}
cd $dir

rm -rf ip192*prt*.txt

			echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'
			sleep 1
			#below port all for memcached
			if [ "$proto" = "memcache_text" ]
			then
				./run_client_and_server_memtier_r1p1_emon.py --ratio ${ratio}  --scores=${core} --mark ip6_${act}_d${d}_c${con} --host ${host} --ccores=${ccore} --port=all  --keymax=1500001 --con_num=$con -n $n -p $p -d $d --sport ${servport} --proto ${proto}
			else
				./run_client_and_server_memtier_r1p1_emon.py --ratio ${ratio}  --scores=${core} --mark ip6_${act}_d${d}_c${con} --host ${host} --ccores=${ccore} --port="onecperserv"  --keymax=1500001 --con_num=$con -n $n -p $p -d $d --sport ${servport} --proto ${proto}
			fi

mkdir -p  ${act}_d${d}_c${con}


#mv ip192.168.*   memtier_ip*  ${act}_d${d}_c${con}

echo "CLINT${ID} DONE!!!!"
