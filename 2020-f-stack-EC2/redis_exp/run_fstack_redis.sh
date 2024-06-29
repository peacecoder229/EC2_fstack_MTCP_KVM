#!/bin/bash

if [ -z "$1" ]
then
  echo "
        Error: No arguments supplied.
        Usage: ./run_fstack_ng_wrk_cases.sh NoOfSlaveProcesses.

        Note: Make sure to change the FF_PATH, FF_DPDK, and NGX_PREFIX in the script according to your own setup.
        "
  exit
fi

noOfServers=$1
clientThread=1
noOfConnection=300
#dataSize=8192

export FF_PATH=/pnpdata/2020-f-stack-muktadir/f-stack
export FF_DPDK=/pnpdata/2020-f-stack-muktadir/f-stack/dpdk/x86_64-native-linuxapp-gcc

REDIS_BIN=$FF_PATH/app/redis-5.0.5/src/redis-server

cp -f f-stack.conf.default f-stack.conf

bitmask=1
for (( i=1; i < $noOfServers; i++ ))
do
  bitmask=$(( bitmask*10+1 ))
done

# convert the bitmask to corresponding binary
decimal=$((2#$bitmask))
hex=$(printf '%x' $decimal)
echo "Running $noOfServers redis server processes. Hexa bitmask is $hex."

# change lcore mask according to the no of worker processes in f-stack.conf
sed -i "s/lcore_mask=1/lcore_mask=$hex/" f-stack.conf

sudo pkill redis-server
sleep 2

# run primary process first
portNo=9001
cp -f redis.conf redis-1.conf
sed -i "s/port 9001/port $portNo/" redis-1.conf
$REDIS_BIN --conf f-stack.conf --proc-type=primary --proc-id=0 redis-1.conf &
portNo=$((portNo+1))
sleep 5

#perf record &

proc_id=1
for i in `seq 2 $noOfServers`;
do
	echo "Starting server $i"
    cp -f redis.conf redis-$i.conf
    sed -i "s/port 9001/port $portNo/" redis-$i.conf
    $REDIS_BIN --conf f-stack.conf --proc-type=secondary --proc-id=$proc_id redis-$i.conf &
    portNo=$((portNo+1))
    proc_id=$((proc_id+1))
done

#./netspeed.sh $interface > netspeed_${fileName}

#sar 1 > sar_${fileName}

#emon -stop

#mv perf.data perf_${fileName}
