#!/bin/bash

#if [ -z "$1" ]
#then
#  echo "Error: No arguments supplied.
#
#Usage: ./ec2_nginx_exp_script.sh NoOfWorkerProcesses.
#  "
#  exit
#fi

case_no=$1
vm_type=$2
instance_id=$3
run_no=$4
no_of_cores=$5

exp_time=$(date -d 'today' | awk -F ' ' '{print $1$2$3$4$5$6}')
res_dir="/home/ubuntu/drc_res_${case_no}_${vm_type}_${instance_id}"

mon_tool="mpstat"

exp_dur=180

sudo mkdir $res_dir

if [[ $vm_type == "secondary" && $case_no == "case_1" ]]; then
  echo "$run_no,$instance_id,$exp_time,$case_no,$vm_type,0,0,0,0" >> ${res_dir}/result.csv
  sleep ${exp_dur}s
  exit 1
fi

NGX_PREFIX=/home/ubuntu/nginx

nWorkers=$((no_of_cores/2)) #4 # no of nginx worker processes (cores)
server_start_core=0 # start cpu
server_end_core=$((nWorkers-1)) # end cpu
client_start_core=$nWorkers
client_end_core=$(($no_of_cores-1))

echo "Copying config ...."
sudo cp -f /home/ubuntu/ec2_nginx_exp_dir/nginx.conf $NGX_PREFIX/conf
echo "sudo cp -f /home/ubuntu/ec2_nginx_exp_dir/nginx.conf $NGX_PREFIX/conf"

echo "Run nginx ...."
sudo taskset -c ${server_start_core}-${server_end_core} $NGX_PREFIX/sbin/nginx -c $NGX_PREFIX/conf/nginx.conf &
echo "sudo taskset -c ${server_start_core}-${server_end_core} $NGX_PREFIX/sbin/nginx -c $NGX_PREFIX/conf/nginx.conf &"

sleep 5s

if [ "$mon_tool" = "perf" ]; then
  echo "Starting monitoring with perf ..."
  sudo perf stat -C ${server_start_core}-${server_end_core} -e tsc,ref-cycles,instructions -o perf.txt sleep $((exp_dur+1))
elif [ "$mon_tool" = "mpstat" ]; then
  echo "Start monitoring with mpstat ..."
  mpstat -P ${server_start_core}-${server_end_core} -u 1 $((exp_dur+1)) > mpstat.txt &
else
  echo "Unknown monitoring tool. Exiting .."
  exit
fi

echo "Run wrk2 ...."
if [ $no_of_cores -eq 8 ]; then
  sudo taskset -c ${client_start_core}-${client_end_core} /home/ubuntu/wrk2/wrk -t 16 -c 1000 -d ${exp_dur}s --latency -R 165000 http://localhost:80 > ${res_dir}/temp.txt
  echo "sudo taskset -c ${client_start_core}-${client_end_core} /home/ubuntu/wrk2/wrk -t 16 -c 1000 -d ${exp_dur}s --latency -R 165000 http://localhost:80 > ${res_dir}/temp.txt"
elif [ $no_of_cores -eq 18 ]; then
  sudo taskset -c ${client_start_core}-${client_end_core} /home/ubuntu/wrk2/wrk -t 32 -c 2000 -d ${exp_dur}s --latency -R 330000 http://localhost:80 > ${res_dir}/temp.txt
  echo "sudo taskset -c ${client_start_core}-${client_end_core} /home/ubuntu/wrk2/wrk -t 32 -c 2000 -d ${exp_dur}s --latency -R 330000 http://localhost:80 > ${res_dir}/temp.txt"
else
  echo "No of cores not supported.."
  exit
fi
sleep 1s

# retrieve the wrk data
p_50=$(grep "0.500000" ${res_dir}/temp.txt | awk '{print $1}')
p_75=$(grep "0.750000" ${res_dir}/temp.txt | awk '{print $1}')
p_90=$(grep "0.900000" ${res_dir}/temp.txt | awk '{print $1}')
avg_rps=$(grep "Req/Sec" ${res_dir}/temp.txt | awk '{print $2}')

if [ "$mon_tool" = "perf" ]; then
  tsc=$(grep "tsc" perf.txt | awk -F ' ' '{print $1}')
  ref_cycles=$(grep "ref-cycles" perf.txt | awk -F ' ' '{print $1}')
  ins=$(grep "instructions" perf.txt | awk -F ' ' '{print $1}')
  echo "Writing perf output ..."

  echo "$run_no,$instance_id,$exp_time,$case_no,$vm_type,${p_50},${p_75},${p_90},${avg_rps},${tsc},${ref_cycles},${ins}" >> ${res_dir}/result.csv

elif [ "$mon_tool" = "mpstat" ]; then
  echo "Writing mpstat output ..."
  total_line=$((nWorkers * exp_dur))
  avg_usr_util=$(awk -v tl=$total_line -F ' ' '{if (NR>1 && $3 != "%usr") {total += $3}} END {print total/tl}' mpstat.txt)
  avg_sys_util=$(awk -v tl=$total_line -F ' ' '{if (NR>1 && $5 != "%sys") {total += $5}} END {print total/tl}' mpstat.txt) 
  
  echo "$run_no,$instance_id,$exp_time,$case_no,$vm_type,${p_50},${p_75},${p_90},${avg_rps},${avg_usr_util},${avg_sys_util}" >> ${res_dir}/result.csv
else
  echo "Unknown monitoring tool. Exiting ..."
  exit
fi

cp /home/ubuntu/output.log ${res_dir}/
