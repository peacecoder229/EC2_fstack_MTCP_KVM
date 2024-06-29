#!/bin/bash
c=$1
lc=38
hc=$(( 38+c-1 ))
cp -f /root/nginx_and_wrk/amruta_cdn/nginx_def.conf /root/nginx_and_wrk/amruta_cdn/nginx_tmp.conf
#use duble quote to pass var and preserve white space
sed -i "s/worker_processes  no/worker_processes  $c/" /root/nginx_and_wrk/amruta_cdn/nginx_tmp.conf

if [ ! -f data_sum_nginx.txt ]
then
	touch data_sum_nginx.txt
fi

pkill -9 nginx
sleep 2

numactl -N 0  nginx -c  /root/nginx_and_wrk/amruta_cdn/nginx_tmp.conf &

sleep 2

res=$(./appstatdata.py ${lc}-${hc} $c 25000 120 http://localhost:80/${2}/)
echo "$1  $2  $res"  >> data_sum_nginx.txt

sleep 20




