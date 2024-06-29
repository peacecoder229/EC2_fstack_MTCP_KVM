#!/bin/bash
#Launch all servers

num=$1
host=$2
server="0-63"
ratio=$3
tag=$4
proto=$5
ccore=$6
cdir=$7

sleep 1
export SUT=$host
#below ifcspare used for MTCP DPDK as primary DPDK interface cannot be used to ssh into the server
export ifcspare=192.168.101.200
echo "Launching redis servers"

if [ "${@:$#}" = "launchserver" ]
 then

                        #./launch_server.py --ratio "1:4"  --scores=${server}  --host=${host}   --port=all  --keymax=10000001 --con_num=10  --pclient=Yes --mtcp='yes'
                        ./launch_server.py --ratio "1:4"  --scores=${server}  --host=${host}   --port=all  --keymax=10000001 --con_num=10  --pclient=Yes
 sleep 10

 echo "ALL Servers launched about 300 sec passes"
fi



for con in "2"
do 
	for d in  "1024"
	do
		for p in "12"
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
			for i in {6..7} {11..13} {15..17} {19..19}
			#for i in {19..19}
				do
				core=$server
				ssh -f -o ConnectTimeout=60 192.168.100.$((200+i)) "cd $cdir; ./client_memt.sh ${con} ${d} ${p} ${tag} ${core} $i $curport $num ${host} ${ratio} ${proto} ${ccore} ${cdir}  &> log_err.txt"
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
#sleep 200 


		done
	done

done

echo "ALL client DONE!!!!"
