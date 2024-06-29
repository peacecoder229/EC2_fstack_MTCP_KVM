#!/bin/bash

echo "$0 host port tag"
if [ $# -ne 13 ]; then
echo $#
exit
fi

source "/opt/pkb/bashrc"

host=$1
port=$2
tag=$3
install_path=$4

#Change the input format from [50, 100, ...] to (50 100 ...)
thread_start=$5
thread_step=$6
thread_end=$7

testtype=$8
mysql_numa=$(lscpu | grep node0|awk '{print $4}')
sysbench_numa=$(lscpu | grep node1|awk '{print $4}')

if [ -z $sysbench_numa ]
then
  sysbench_numa=$mysql_numa
fi

#parameters of sysbench
tablesize=$9  #default 2000000
tables=${10}    #default 10
pstime=${11}    #default 400 seconds
rwtime=$pstime    #default 400 seconds
lat_percent=${12}  #sysbench latency percent, default 99%
report_interval=${13}  #sysbench_report_interval ,default 10 seconds.

echo "input parameter:host=$host, port=$port, tag=$tag, install_path=$install_path, thread_start=$thread_start, thread_step=$thread_step, thread_end=$thread_end, testtype=$testtype, mysql_numa=$mysql_numa, sysbench_numa=$sysbench_numa, tablesize=$tablesize, tables=$tables, pstime=$pstime"
echo "lat_percent=$lat_percent, report_interval=$report_interval"
mysqlpasswd=123456
sqluser=root
mysqlpath=$install_path/mysql-5.7
mysqlversion=`basename $mysqlpath`
sysbenchpath=$install_path/sysbench

cur_date=`date +'%Y%m%d'`

NOW=`date +'%Y%m%d%H%M'`

echo "ssh $host" "cd $mysqlpath; ps -ef | grep mysqld | grep -v grep | cut -c 9-15 | xargs sudo kill -9; numactl -C $mysql_numa -l  bin/mysqld_safe --defaults-file=$mysqlpath/my.cnf --user=$sqluser & >mysql_safe.log 2>&1 &"
cd $mysqlpath
#kill exist mysql instance
ps -ef | grep mysqld | grep -v grep | cut -c 9-15 | xargs sudo kill -9

#wait for mysql shutdown
for ((a = 1; a <=3 ; a++))
do
        echo -ne " $a[3]\r"
        sleep 1
done
cd $mysqlpath

#start mysql using numactl
numactl -C $mysql_numa -l sudo bin/mysqld_safe --defaults-file=$mysqlpath/my.cnf --user=$sqluser >>mysql_safe.log 2>&1 &

#test if mysql is ready
echo "$mysqlpath/bin/mysql -h$host -u$sqluser -p123456 -P$port -e 'select version();'"
$mysqlpath/bin/mysql -h$host -u$sqluser -p123456 -P$port -e "select version();" &>/dev/null
result=$?
while [ $result -ne 0 ]
do
        echo "Result=$result Waiting for MySQL start up"
        $mysqlpath/bin/mysql -h$host -u$sqluser -p$mysqlpasswd -P$port -e "select version();" &>/dev/null
        result=$?
        sleep 1
done

for((threads=$thread_start,t=0; threads<=$thread_end; threads=threads+$thread_step,t++))  # threads loop
do
        echo "t=$t, testtype=$testtype"
        if [ $t -eq 0 ]
        then
                sudo mkdir -p $sysbenchpath/logs
        fi
        testname=""
        logname=""
        logname=sysbench_${testtype}_threads_${threads}.log
        cd $sysbenchpath
        echo "sudo pkill sysbench"
        sudo pkill sysbench

        testname=$cur_date/$tag-$testtype-$NOW
        if [ "$testtype" == "ps" ]
        then
                cmd="numactl -C $sysbench_numa -l sysbench $sysbenchpath/src/lua/oltp_point_select.lua --tables=$tables --table-size=$tablesize --threads=${threads} --rand-type=uniform --db-driver=mysql --mysql-socket=$mysqlpath/mysqld.sock --mysql-db=sbtest --mysql-user=$sqluser --mysql-password=$mysqlpasswd --point-selects=1 --simple-ranges=0 --sum-ranges=0 --order-ranges=0 --distinct-ranges=0 --report-interval=$report_interval  --percentile=$lat_percent --time=$pstime --events=0 "
        else
          cmd="numactl -C $sysbench_numa -l sysbench $sysbenchpath/src/lua/oltp_read_write.lua   --tables=$tables --table-size=$tablesize --threads=${threads} --rand-type=uniform --db-driver=mysql --mysql-host=$host --mysql-port=$port --mysql-db=sbtest --mysql-user=$sqluser --mysql-password=$mysqlpasswd --point-selects=1 --simple-ranges=0 --sum-ranges=0 --order-ranges=0 --distinct-ranges=0 --report-interval=$report_interval  --percentile=$lat_percent --time=$rwtime --events=0 --secondary=on "
  fi
  echo $cmd

        if [ $t -eq 0 ]
        then
                echo "$cmd cleanup"
                $cmd cleanup
                echo "$cmd prepare"
                $cmd prepare
        fi

        echo "sudo mkdir -p logs/$testname"
        sudo mkdir -p logs/$testname
        echo "$cmd run | tee logs/$testname/$logname"
        $cmd run |sudo tee logs/$testname/$logname
        echo "wait"
done

echo "------------------------------process the test result------------------------------"
max_qps_idx=0
QPS[0]=0

if test -d $sysbenchpath/logs/$testname
then
  log_dir=$sysbenchpath/logs/$testname
  echo $log_dir

  for((threads=$thread_start,t=0; threads<=$thread_end; threads=threads+$thread_step,t++))  # threads loop
  do
      if [ -f "$log_dir/sysbench_${testtype}_threads_${threads}.log" ]; then
              eval TPS[$t]=`grep -rn "transactions:"  $log_dir/sysbench_${testtype}_threads_${threads}.log |awk '{print $4}' |cut -c 2-`
              eval QPS[$t]=`grep -rn "queries:"  $log_dir/sysbench_${testtype}_threads_${threads}.log |awk '{print $4}' |cut -c 2-`
              eval LatMin[$t]=`grep -rn "min:"  $log_dir/sysbench_${testtype}_threads_${threads}.log |awk '{print $3}'`
              eval LatAvg[$t]=`grep -rn "avg:"  $log_dir/sysbench_${testtype}_threads_${threads}.log |awk '{print $3}'`
              eval LatMax[$t]=`grep -rn "max:"  $log_dir/sysbench_${testtype}_threads_${threads}.log |awk '{print $3}'`
              eval LatxPercent[$t]=`grep -rn "percentile:"  $log_dir/sysbench_${testtype}_threads_${threads}.log |awk '{print $4}'`
              if [ `echo "scale=2; ${QPS[$max_qps_idx]} < ${QPS[$t]}" | bc` -eq 1 ]; then
                max_qps_idx=$t
              fi
        echo "maxqps:${QPS[$max_qps_idx]}, curqps:${QPS[$t]}, max_qps_idx:$max_qps_idx, t:$t"
        echo "threads_${threads}: ${TPS[$t]}  ${QPS[$t]}  ${LatMin[$t]} ${LatAvg[$t]} ${LatMax[$t]} ${LatxPercent[$t]} $max_qps_idx"
      fi
  done
fi

echo -e  " Threads: $[$thread_start+$thread_step*$max_qps_idx]\n TPS: ${TPS[$max_qps_idx]}\n QPS: ${QPS[$max_qps_idx]}\n Latency min: ${LatMin[$max_qps_idx]}\n Latency avg: ${LatAvg[$max_qps_idx]}\n Latency max: ${LatMax[$max_qps_idx]}\n Latency percentile: ${LatxPercent[$max_qps_idx]}\n" | sudo tee $sysbenchpath/logs/result.log