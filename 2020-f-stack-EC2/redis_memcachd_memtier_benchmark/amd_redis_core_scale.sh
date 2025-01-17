#!/bin/bash
#Launch all servers

num=$1
host=$2
server=$8
ratio=$3
tag=$4
proto=$5
ccore=$6
cdir=$7
curport=$9


sleep 1
export SUT=$host
#below ifcspare used for MTCP DPDK as primary DPDK interface cannot be used to ssh into the server
export ifcspare=192.168.101.200
echo "Launching redis servers"

if [ "${@:$#}" = "launchserver" ]
then
	 		pkill -9 redis-server
			sleep 1
			echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'
                        #./launch_server.py --ratio "1:4"  --scores=${server}  --host=${host}   --port=all  --keymax=10000001 --con_num=10  --pclient=Yes --mtcp='yes'
                        ./launch_server.py --ratio "1:4"  --scores=${server}  --host=${host}   --port=all  --keymax=10000001 --con_num=10 
 sleep 10

 echo "ALL Servers launched about 300 sec passes"
fi

if [ "${@:$#}" = "launchmemcache" ]
then
	 		#pkill -9 memcached
			sleep 1
			echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'
                        #./launch_server.py --ratio "1:4"  --scores=${server}  --host=${host}   --port=all  --keymax=10000001 --con_num=10  --pclient=Yes --mtcp='yes'
			hc=$(echo $server | cut -f2 -d-)
			lc=$(echo $server | cut -f1 -d-)
		        thread=$(( hc-lc+1 ))	
			taskset -c ${server} memcached -d -m 358400 -p $curport -u root -l 127.0.0.1 -t $thread -c 4096 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1 &	
			sleep 10

 echo "ALL Servers launched about 300 sec passes"
fi


for con in "32"
do 
	for d in  "512"
	do
		for p in "8"
		do
rm -rf /root/redis_memcachd_memtier_benchmark/core_scale/ip*prt*.txt
sleep 3
		#for act in "ddio_tx2_rx2" "ddio_tx4_rx2_ex" "ddio_tx7_rx4_ex" "ddio_tx6_rx5_ex"
		for act in "build"
			do
			sleep 2
			#ssh -o ConnectTimeout=10 SUT "/pnpdata/hwpdesire/${act}"
			sleep 2
			#curport=9001
			#for i in {3..11}
			for i in {1..1}
			#for i in {19..19}
				do
				if [  "${proto}" = "memcache_text" ]
				then 
					core="0-0"
				else
					core=$server
				fi

				cd $cdir; ./client_memt.sh ${con} ${d} ${p} ${tag} ${core} $i $curport $num ${host} ${ratio} ${proto} ${ccore} ${cdir}  &> log_err.txt
				sleep 1
				
				echo "Launched Client$i benchmarks"
			done
				
		done



while [ `pgrep -f 'ssh.*-f.*client_memt.sh' | wc -l` -ge 1 ]
 do
	sleep 1
	echo "Client still running"
 done


echo "Starting next Iteration of memtier Runs"
sleep 20 
file=${tag}_con${con}_d${d}.txt
touch $file
grep GET ip127.0.0.1prt900* | sort -nk3  | awk '($3 > 95) && ($3 < 99.9) {print $0}' >> $file
grep SET ip127.0.0.1prt900* | sort -nk3  | awk '($3 > 95) && ($3 < 99.9) {print $0}' >> $file


		done
	done

done

echo "ALL client DONE!!!!"
