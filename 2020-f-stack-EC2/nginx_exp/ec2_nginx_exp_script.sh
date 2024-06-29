#!/bin/bash

if [ -z "$1" ]
then
  echo "Error: No arguments supplied.

Usage: ./run_fstack_ng_wrk_cases.sh NoOfSlaveProcesses.
  "
  exit
fi

export NGX_PREFIX=/pnpdata/2020-f-stack-muktadir/nginx_vanilla

EXP_PATH=/pnpdata/2020-f-stack-muktadir/nginx_exp

c=$1 # no of nginx slave processes (cores)
server_start_core=0 # start cpu
server_end_core=11 # end cpu
client_start_core=12
client_end_core=23
#html_page=$2 #1KB or 256B

# copy the default conf to current dir
cp -f /usr/local/nginx.conf /home/ubuntu/

#use double quote to pass var and preserve white space
# change no of worker processes in nginx.conf (Note: space between key and value should match)
sed -i "s/worker_processes  1/worker_processes  $c/" nginx.conf
#sed -i "s#fstack_conf f-stack.conf#fstack_conf $EXP_f-stack.conf#" conf/nginx.conf

pkill -9 nginx
sleep 2

#numactl -N 0 /pnpdata/2020-f-stack-muktadir/nginx_fstack/sbin/nginx -c /pnpdata/2020-f-stack-muktadir/nginx_exp/nginx.conf
taskset -c ${server_start_core}-${server_end_core} nginx -c nginx.conf
