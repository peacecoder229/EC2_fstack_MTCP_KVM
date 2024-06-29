#!/bin/bash
#./amd_redis_core_scale.sh 1048576 127.0.0.1 1:0 3C_wr redis 192-193 /root/redis_memcachd_memtier_benchmark/core_scale 0-2 launchserver
#./amd_redis_core_scale.sh 504857 127.0.0.1 1:4 3C_rd redis 192-255 /root/redis_memcachd_memtier_benchmark/core_scale 0-2
./amd_memcached_core_scale.sh 1048576 127.0.0.1 1:0 write_0-27 redis 28-29 /root/redis_memcachd_memtier_benchmark/core_scale 0-27 9001 launchserver
./amd_memcached_core_scale.sh 504857 127.0.0.1 1:4 4C_rd redis 28-31,84-87  /root/redis_memcachd_memtier_benchmark/core_scale 0-3 9001 &
