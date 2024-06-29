To generate html file of different size: 
- ./gen_html.sh 256 K 256K_file
file is created in /usr/local/nginx/html

To run nginx:
- pkill -9 nginx
- numactl --physcpubind=0-7 nginx -c /root/amruta_cdn/nginx_def.conf

To run workload:
- numactl -C 65-73 ./wrk -t 8 -c 10000 -d 10s -L http://localhost:80/2K_file/
