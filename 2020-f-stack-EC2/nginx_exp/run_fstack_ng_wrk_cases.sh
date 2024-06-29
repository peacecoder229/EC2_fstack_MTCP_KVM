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

export FF_PATH=/pnpdata/2020-f-stack-muktadir/f-stack
export FF_DPDK=/pnpdata/2020-f-stack-muktadir/f-stack/dpdk/x86_64-native-linuxapp-gcc

export NGX_PREFIX=/pnpdata/2020-f-stack-muktadir/nginx_fstack

EXP_PATH=/pnpdata/2020-f-stack-muktadir/nginx_exp

c=$1 # no of nginx slave processes (cores)
lc=16 # start cpu
hc=$(( 16+c-1 )) # end cpu
#html_page=$2 #1KB or 256B

# copy the default conf of current dir to $NGX_PREFIX `conf` dir 
cp -f f-stack.conf.default $NGX_PREFIX/conf/f-stack.conf
cp -f nginx-fstack.conf.default $NGX_PREFIX/conf/nginx.conf

# use double quote to pass var and preserve white space
# change no of worker processes in nginx.conf (Note: space between key and value should match)
sed -i "s/worker_processes  1/worker_processes  $c/" $NGX_PREFIX/conf/nginx.conf
#sed -i "s#fstack_conf f-stack.conf#fstack_conf $EXP_f-stack.conf#" conf/nginx.conf

# convert number of cores to binary bitmask
bitmask=1
for (( i=1; i < $c; i++ ))
do
  bitmask=$(( bitmask*10+1 ))
done

# convert the bitmask to corresponding binary
decimal=$((2#$bitmask))
hex=$(printf '%x' $decimal)
echo "Running $c nginx worker processes. Hexa bitmask is $hex."

# change lcore mask according to the no of worker processes in f-stack.conf
sed -i "s/lcore_mask=1/lcore_mask=$hex/" $NGX_PREFIX/conf/f-stack.conf

pkill -9 nginx
sleep 2

#$NGX_PREFIX/sbin/nginx -c $NGX_PREFIX/conf/nginx.conf

#sleep 2

#res=$(./appstatdata.py ${lc}-${hc} $c 25000 120 http://localhost:80/${html_page}/)
#echo "$c  $html_page  $res"  >> data_sum_nginx.txt

#sleep 20
