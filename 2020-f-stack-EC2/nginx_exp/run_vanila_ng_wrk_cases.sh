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
lc=16 # start cpu
hc=$(( 16+c-1 )) # end cpu
#html_page=$2 #1KB or 256B

# copy the default conf of current dir to $NGX_PREFIX `conf` dir 
cp -f nginx_vanilla.conf.default $NGX_PREFIX/conf/nginx.conf

#use double quote to pass var and preserve white space
# change no of worker processes in nginx.conf (Note: space between key and value should match)
sed -i "s/worker_processes  1/worker_processes  $c/" $NGX_PREFIX/conf/nginx.conf
#sed -i "s#fstack_conf f-stack.conf#fstack_conf $EXP_f-stack.conf#" conf/nginx.conf

pkill -9 nginx
sleep 2

#numactl -N 0 /pnpdata/2020-f-stack-muktadir/nginx_fstack/sbin/nginx -c /pnpdata/2020-f-stack-muktadir/nginx_exp/nginx.conf
$NGX_PREFIX/sbin/nginx -c $NGX_PREFIX/conf/nginx.conf
