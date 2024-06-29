#!/bin/bash

ulimit -n 65535
nohup ./web_ats_gen.py --host localhost --port 8888 --obj-dist fixed &
#http_proxy= https_proxy= /usr/local/nginx/sbin/nginx &
