#!/bin/bash

noOfServers=2
clientThread=1
noOfConnection=300
portNo=9001
#dataSize=8192


#./run_emon.sh emon_$fileName

	./app/redis-3.2.8/src/redis-server --conf config.ini --proc-type=primary --proc-id=0 redis-1.conf & 
	sleep 5
    #./app/redis-3.2.8/src/redis-server --conf config.ini --proc-type=secondary --proc-id=1 redis-2.conf &
#perf record &
proc_id=1
for i in `seq 2 $noOfServers`;
do
	echo "Starting server $i"
    ./app/redis-3.2.8/src/redis-server --conf config.ini --proc-type=secondary --proc-id=$proc_id redis-$i.conf &
     portNo=$((portNo+1))
    proc_id=$((proc_id+1))
done

#./netspeed.sh $interface > netspeed_${fileName}

#sar 1 > sar_${fileName}

#emon -stop

#mv perf.data perf_${fileName}
