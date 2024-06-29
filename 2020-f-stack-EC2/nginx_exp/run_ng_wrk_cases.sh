#!/bin/bash

c=$1 # no of nginx slave processes (cores)
lc=16 # start cpu
hc=$(( 16+c-1 )) # end cpu
html_page=$2 #1KB or 256B

cp -f /pnpdata/2020-f-stack-muktadir/nginx_vanilla/conf/nginx.conf /pnpdata/2020-f-stack-muktadir/nginx_exp/nginx.conf
#use double quote to pass var and preserve white space
sed -i "s/worker_processes  no/worker_processes  $c/" /pnpdata/2020-f-stack-muktadir/nginx_exp/nginx.conf

if [ ! -f data_sum_nginx.txt ]
then
	touch data_sum_nginx.txt
fi

pkill -9 nginx
sleep 2

numactl -N 0 /pnpdata/2020-f-stack-muktadir/nginx_vanilla/sbin/nginx -c /pnpdata/2020-f-stack-muktadir/nginx_exp/nginx.conf

sleep 2

res=$(./appstatdata.py ${lc}-${hc} $c 25000 120 http://localhost:80/${html_page}/)
echo "$c  $html_page  $res"  >> data_sum_nginx.txt

sleep 20
