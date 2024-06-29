#!/bin/bash

exp_time=$(date -d 'today' | awk -F ' ' '{print $1$2$3$4$5$6}')
file_name=${exp_time}.csv
echo "RunNo,InstanceId,Time,Exp Scenario,VM Type,Avg Latency,Avg Throughput" > $file_name
cat drc_res_case_* >> $file_name
