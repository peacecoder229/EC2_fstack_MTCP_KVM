#!/bin/bash
./mc_or_redis_sweep.sh 0-13 drc_res 1 "memcached"
./mc_or_redis_sweep.sh 0-27 drc_res 2 "memcached"
./mc_or_redis_sweep.sh 0-35 drc_res 3 "memcached"
./mc_or_redis_sweep.sh 0-13 drc_res 1 "redis"
./mc_or_redis_sweep.sh 0-27 drc_res 1 "redis"
./mc_or_redis_sweep.sh 0-35 drc_res 1 "redis"
