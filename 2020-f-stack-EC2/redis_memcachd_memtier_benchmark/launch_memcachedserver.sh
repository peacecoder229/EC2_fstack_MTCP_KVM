#!/bin/bash

########################################################################################################
# find_max_clients_multi_server.sh: Script to perform memcached performance benchmarking using YCSB
# USAGE: ./find_max_clients_multi_server.sh clients_file min_clients max_clients increment #repetitions
# Eg: ./find_max_clients_multi_server.sh clients.log 150 250 10 5
# (SSG/CCE) - Cloud computing and Engineering group
# Intel Confidential
########################################################################################################

# File with the client IPs
HOSTS_FILE=$1
IFS=',' read -ra CLIENTS <<< `cat $HOSTS_FILE`
SPACE="_"
TIME=$(date +%Y%m%d_%H%M%S)

#!!!!!!!!!!!  EDIT REQUIRED WHEN SERVER IS CHANGED !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

# Server configurations
SERVER=192.168.100.190	# IP of server
USERNAME=root   	# Username on server and clients
SERVER_THREADS=128	# Set the no: of CPUs on server
CLIENT_THREADS=4	# Set to a low value <=4
NUM_SERVERS=3		# Ignore if using only a single server instance
INIT_VALUE=$2		# Minimum no: of client instances
MAX_CLIENTS=$3		# Maximum no: of client instances
INCREMENT=$4		# Increment value for client connections
MAX_TRIALS=$5		# No: of repetitions for the experiment
j=$NUM_SERVERS
# Server File Paths
MEMCACHED_SCRIPT_PATH="/root/memcached-1.5.16/Benchmarking_Scripts/Memcached_Server_Machine"
YCSB_PATH="/root/YCSB/"
EMON_PATH="/root/emon"
EMON_FLAG=1
PAT_PATH="/root/PAT-master/PAT-collecting-data"
PAT_FLAG=0

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

# Create a result directory
ssh $USERNAME@$SERVER "pkill -15 memcached; sudo /sbin/sysctl vm.drop_caches=3; ./set_irq_affinity -x 0-31,64-95 enp49s0f0 "
#HOSTS_FILE=clients"$j"_mod.log
./changeOpsInClients.sh clients1.log g "pkill java"
echo " the file being used is $HOSTS_FILE"
echo "./record_modification_epyc.sh clients1.log 1 1000 $((100000000/j)) 0.8 0.2"
./record_modification_epyc.sh clients1.log 1 1000 $((100000000/j)) 0.8 0.2


RESULT_DIR="result_maxClients_multiServer_epyc_3S_run"$TIME
mkdir -p $RESULT_DIR
resFile=$RESULT_DIR"/result_maxClients_multiServer_epyc_3S_run"$TIME".txt"

# Get Ethernet Port Name
eth_data=`ssh $USERNAME@$SERVER "/usr/sbin/ifconfig | grep -B1 "$SERVER""`
eth_data=`echo $eth_data | grep -B1 "inet $SERVER" | awk '$1!="inet" && $1!="--" {print $1}'`
ETH_NAME=`echo ${eth_data::-1}`

####Shifting Server DB loding here as we are doing Rean-Only########
# Memcached server ports
declare -a ports=("11211" "11212" "11213" "11214" "11215" "11216" "11217" "11218" "11219" "11220" "11221" "11222" "11223" "11224" "11225" "11226" "11227" "11228" "11229" "11230")

# Memcached server IPs
declare -a servers=("192.168.100.190" "192.168.100.190" "192.168.100.190")

# Set the CPU Governor to performance mode
ssh $USERNAME@$SERVER "cpupower frequency-set -g performance"
echo "Set Cores to performance mode!!"

# Start memcached with the required threads
ssh $USERNAME@$SERVER "cd $MEMCACHED_SCRIPT_PATH; ./kill_mchd_servers.sh" # First kill any existing instances
if [ $? -eq 1 ]; then

        sleep 10
	for (( i=0; i<$NUM_SERVERS; i++ ));
	do
		echo "Pass server creation"
        	#echo "Lunch server instance: ssh $USERNAME@$SERVER "numactl -N $((i%2)) memcached -d -m 358400 -p ${ports[i]} -u $USERNAME -l ${servers[i]} -t $SERVER_THREADS -c 2048 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1""
		#ssh $USERNAME@$SERVER "numactl -N $((i%2)) memcached -d -m 358400 -p ${ports[i]} -u $USERNAME -l ${servers[i]} -t $SERVER_THREADS -c 2048 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1"
		#echo "Lunch server instance: ssh $USERNAME@$SERVER "numactl --interleave=all memcached -d -m 358400 -p ${ports[i]} -u $USERNAME -l ${servers[i]} -t $SERVER_THREADS -c 2048 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1""
		#ssh $USERNAME@$SERVER "numactl --interleave=all memcached -d -m 358400 -p ${ports[i]} -u $USERNAME -l ${servers[i]} -t $SERVER_THREADS -c 2048 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1"
		if [ $i -eq 0 ]; then
                        echo "Launch server instance: ssh $USERNAME@$SERVER "numactl -N 0,3 -m 0,3 -C 0-7,24-26,64-71,88-90 memcached -d -m $((358400/j)) -p ${ports[i]} -u $USERNAME -l ${servers[i]} -t $SERVER_THREADS -c 2048 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1""
			ssh $USERNAME@$SERVER "numactl -N 0,3 -m 0,3 -C 0-7,24-26,64-71,88-90 memcached -d -m $((358400/j)) -p ${ports[i]} -u $USERNAME -l ${servers[i]} -t $SERVER_THREADS -c 2048 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1"
		#echo "Lunch server instance: ssh $USERNAME@$SERVER "memcached -d -m 300000 -p ${ports[i]} -u memuser -l ${servers[i]} -t $SERVER_THREADS -c 2048 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1""
		#ssh $USERNAME@$SERVER "memcached -d -m 300000 -p ${ports[i]} -u memuser -l ${servers[i]} -t $SERVER_THREADS -c 2048 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1"
		#ssh $USERNAME@$SERVER "numactl -N 0 memcached -d -m 10000 -p ${ports[i]} -u $USERNAME -l 0.0.0.0 -t $SERVER_THREADS -c 2048"
        	#ssh $USERNAME@$SERVER "memcached -d -m 90000 -p ${ports[i]} -u $USERNAME -l 0.0.0.0 -t $SERVER_THREADS -c 4096 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1"
                
                	current_server=${servers[i]} #i/0
                	eth_data=`ssh $USERNAME@$current_server "/usr/sbin/ifconfig | grep -B1 "$current_server""`
                	eth_data=`echo $eth_data | grep -B1 "inet $current_server" | awk '$1!="inet" && $1!="--" {print $1}'`
                	ETH_NAME=`echo ${eth_data::-1}`
		fi
		if [ $i -eq 1 ]; then
			echo "Launch server instance: ssh $USERNAME@$SERVER "numactl -N 1,3 -m 1,3 -C 8-15,27-29,72-79,91-93 memcached -d -m $((358400/j)) -p ${ports[i]} -u $USERNAME -l ${servers[i]} -t $SERVER_THREADS -c 2048 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1""
                        ssh $USERNAME@$SERVER "numactl -N 1,3 -m 1,3 -C 8-15,27-29,72-79,91-93  memcached -d -m $((358400/j)) -p ${ports[i]} -u $USERNAME -l ${servers[i]} -t $SERVER_THREADS -c 2048 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1"
                #echo "Lunch server instance: ssh $USERNAME@$SERVER "memcached -d -m 300000 -p ${ports[i]} -u memuser -l ${servers[i]} -t $SERVER_THREADS -c 2048 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1""
                #ssh $USERNAME@$SERVER "memcached -d -m 300000 -p ${ports[i]} -u memuser -l ${servers[i]} -t $SERVER_THREADS -c 2048 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1"
                #ssh $USERNAME@$SERVER "numactl -N 0 memcached -d -m 10000 -p ${ports[i]} -u $USERNAME -l 0.0.0.0 -t $SERVER_THREADS -c 2048"
                #ssh $USERNAME@$SERVER "memcached -d -m 90000 -p ${ports[i]} -u $USERNAME -l 0.0.0.0 -t $SERVER_THREADS -c 4096 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1"

                        current_server=${servers[i]} #i/0
                        eth_data=`ssh $USERNAME@$current_server "/usr/sbin/ifconfig | grep -B1 "$current_server""`
                        eth_data=`echo $eth_data | grep -B1 "inet $current_server" | awk '$1!="inet" && $1!="--" {print $1}'`
                        ETH_NAME=`echo ${eth_data::-1}`
		fi
		if [ $i -eq 2 ]; then
			echo "Launch server instance: ssh $USERNAME@$SERVER "numactl -N 2,3 -m 2,3 -C 16-23,30-31,80-87,94-95 memcached -d -m $((358400/j)) -p ${ports[i]} -u $USERNAME -l ${servers[i]} -t $SERVER_THREADS -c 2048 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1""
			ssh $USERNAME@$SERVER "numactl -N 2,3 -m 2,3 -C 16-23,30-31,80-87,94-95 memcached -d -m $((358400/j)) -p ${ports[i]} -u $USERNAME -l ${servers[i]} -t $SERVER_THREADS -c 2048 -o lru_maintainer,lru_crawler,hot_lru_pct=78,warm_lru_pct=1"
			current_server=${servers[i]} #i/0
                        eth_data=`ssh $USERNAME@$current_server "/usr/sbin/ifconfig | grep -B1 "$current_server""`
                        eth_data=`echo $eth_data | grep -B1 "inet $current_server" | awk '$1!="inet" && $1!="--" {print $1}'`
                        ETH_NAME=`echo ${eth_data::-1}`

		fi
                #ssh $USERNAME@$SERVER "cd $MEMCACHED_SCRIPT_PATH; ./set_irq_affinity -x local $ETH_NAME"
	done
else
        echo "Unable to kill memcached server at $SERVER"
        exit 0
fi

# Load memcached server
for (( i=0; i<$NUM_SERVERS; i++ ));
do
	echo "Server Load: ssh $USERNAME@$SERVER cd $YCSB_PATH; source /etc/profile.d/maven.sh; ./bin/ycsb load memcached -s -threads $SERVER_THREADS -P workloads/workloadc_8020 -p \"memcached.hosts=${servers[i]}:${ports[i]}\" > /dev/null 2>&1"
	ssh $USERNAME@$SERVER "cd $YCSB_PATH; source /etc/profile.d/maven.sh; ./bin/ycsb load memcached -s -threads $SERVER_THREADS -P workloads/workloadc_8020 -p \"memcached.hosts=${servers[i]}:${ports[i]}\" > /dev/null 2>&1"
        #ssh $USERNAME@$SERVER "cd $YCSB_PATH; source /etc/profile.d/maven.sh; ./bin/ycsb load memcached -s -threads $SERVER_THREADS -P workloads/workloadc -p \"memcached.hosts=localhost:${ports[i]}\" > /dev/null 2>&1"
	#echo "Server Load: ssh $USERNAME@$SERVER "cd $YCSB_PATH; source /etc/profile.d/maven.sh; ./bin/ycsb load memcached -s -threads $SERVER_THREADS -P workloads/workloadc -p \"memcached.hosts=${servers[i]}:${ports[i]}\" > /dev/null 2>&1""
	echo "Pass Loading"
	sleep 1
done

echo "Done Loading. Starting YCSB workload"



############# Finding the max clients ###########
for (( nClients=$INIT_VALUE; nClients<=$MAX_CLIENTS; nClients+=$INCREMENT ));
do
	BASE_DIR=$RESULT_DIR"/clients_$nClients"
	mkdir $BASE_DIR

	echo "Run command: ./get_tp_multi_sc_oneLoding_epyc.sh $HOSTS_FILE $ETH_NAME $SERVER $MAX_TRIALS $MEMCACHED_SCRIPT_PATH $YCSB_PATH $USERNAME $SERVER_THREADS $CLIENT_THREADS $NUM_SERVERS $nClients $BASE_DIR $EMON_PATH $EMON_FLAG $PAT_PATH $PAT_FLAG"
	TP=`./get_tp_multi_sc_oneLoding_epyc.sh $HOSTS_FILE $ETH_NAME $SERVER $MAX_TRIALS $MEMCACHED_SCRIPT_PATH $YCSB_PATH $USERNAME $SERVER_THREADS $CLIENT_THREADS $NUM_SERVERS $nClients $BASE_DIR $EMON_PATH $EMON_FLAG $PAT_PATH $PAT_FLAG`
	echo $threads $TP >> $resFile	

	sleep 60
done
############# Done finding max clients ##########

