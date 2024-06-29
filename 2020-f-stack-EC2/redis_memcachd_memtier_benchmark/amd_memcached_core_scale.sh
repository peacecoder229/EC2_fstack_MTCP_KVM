#!/bin/bash
#Launch all servers

#PLASE NOTE CURRENTLY servers are pinned to memory node0 and clienst are pinnned to memory node1

num=$1
host=$2
server=$8
ratio=$3
tag=$4
proto=$5
ccore=$6
cdir=$7
curport=$9
sock=${10}

sleep 1
export SUT=$host
#below ifcspare used for MTCP DPDK as primary DPDK interface cannot be used to ssh into the server
export ifcspare=192.168.101.200

if [ "${@:$#}" = "launchserver" ]
then
	 		pkill -9 redis-server
			sleep 1
			echo 3 > /proc/sys/vm/drop_caches && swapoff -a && swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'
                        #./launch_server.py --ratio "1:4"  --scores=${server}  --host=${host}   --port=all  --keymax=10000001 --con_num=10  --pclient=Yes --mtcp='yes'
			cd ${cdir}
      ./launch_server.py --ratio "1:4"  --scores=${server}  --host=${host}   --port=all  --keymax=10000001 --con_num=10 
			cd -
 sleep 2

 echo "ALL redis Servers launched about 300 sec passes"
fi

if [ "${@:$#}" = "launchmemcache" ]
then
	 		#pkill -9 memcached
			sleep 1
			sudo echo 3 > /proc/sys/vm/drop_caches && sudo swapoff -a && sudo swapon -a && sudo printf '\n%s\n' 'Ram-cache and Swap Cleared'
                        #./launch_server.py --ratio "1:4"  --scores=${server}  --host=${host}   --port=all  --keymax=10000001 --con_num=10  --pclient=Yes --mtcp='yes'
			if [ $hypt = "on" ]
			then
				highg=$(echo $server | cut -f2 -d,)
				lowg=$(echo $server | cut -f1 -d,)
				hc1=$(echo $highg | cut -f2 -d-)
				lc1=$(echo $highg | cut -f1 -d-)
				hc2=$(echo $lowg | cut -f2 -d-)
				lc2=$(echo $lowg | cut -f1 -d-)
				thread=$(( hc1-lc1+hc2-lc2+2 ))
			else
				hc=$(echo $server | cut -f2 -d-)
				lc=$(echo $server | cut -f1 -d-)
		        	thread=$(( hc-lc+1 ))
			fi
			if [ "$runnuma" = "yes" ]
			then
			
      numactl --membind=0 --physcpubind=${server} memcached -d -m 358400 -p $curport -u root -l 127.0.0.1 -t $thread -c 4096 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1 &
			else 

			numactl -N 0 memcached -d -m 358400 -p $curport -u root -l 127.0.0.1 -t $thread -c 4096 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1 &
			fi	
			sleep 2

      echo "ALL memcached Servers launched about 300 sec passes"
fi

crun=0
for con in "${sock}"
do 
	for d in  "256"
	do
		for p in "4"
		do
#rm -rf /root/redis_memcachd_memtier_benchmark/core_scale/ip*prt*.txt
    sleep 4
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

				cd $cdir; 
				./client_memt.sh ${con} ${d} ${p} ${tag} ${core} $i $curport $num ${host} ${ratio} ${proto} ${ccore} ${cdir}  &> log_err_${curport}.txt
				#./client_memt.sh ${con} ${d} ${p} ${tag} ${core} $i $curport $num ${host} ${ratio} ${proto} ${ccore} ${cdir} &
				cid[${crun}]=$!
				sleep 1
				
				echo "started Clients to server at port=${curport}"
				crun=$(( crun+1 ))
			done
				
		done

for runid in ${cid[*]};
do
	echo $runid
	wait $runid
done


sleep 5

echo "processing the ipfile in memtier Runs for ${tag}"
sleep 5 
file=${tag}_con${con}_d${d}.txt
touch $file
#grep GET ip127.0.0.1prt${curport}* | sort -nk3  | awk '($3 > 95) && ($3 < 99.99) {print $0}' >> $file
#grep SET ip127.0.0.1prt${curport}* | sort -nk3  | awk '($3 > 95) && ($3 < 99.99) {print $0}' >> $file
#grep "Totals" ip127.0.0.1prt${curport}* | awk '{print $1 " " $2}' >> $file
#rm -f ip127.0.0.1prt900*
#Adding to get exact port number to be able to write to the accurate file


if [  "${proto}" = "memcache_text" ]
then
	no=$(echo "$tag" | cut -d t -f 2)
	prttag=$(( 9001+no ))*
else
	prttag="90*"
fi

grep GET ip127.0.0.1prt${prttag} | sort -nk3  | awk '($3 > 95) && ($3 < 99.99) {print $0}' >> $file
grep SET ip127.0.0.1prt${prttag} | sort -nk3  | awk '($3 > 95) && ($3 < 99.99) {print $0}' >> $file
grep "Totals" ip127.0.0.1prt${prttag} | awk '{print $1 " " $2}' >> $file

		done
	done

done

echo "ALL client RPOCESSING DONE!!!!"
