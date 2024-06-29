#!/bin/bash
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:0 3C_wr redis 192-193 /root/redis_memcachd_memtier_benchmark/core_scale 0-2 launchserver
./amd_redis_core_scale.sh 504857 127.0.0.1 1:4 3C_rd redis 192-255 /root/redis_memcachd_memtier_benchmark/core_scale 0-2
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:0 4C_wr redis 192-193 /root/redis_memcachd_memtier_benchmark/core_scale 0-3 launchserver
./amd_redis_core_scale.sh 504857 127.0.0.1 1:4 4C_rd redis 192-255 /root/redis_memcachd_memtier_benchmark/core_scale 0-3
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:0 5C_wr redis 192-193 /root/redis_memcachd_memtier_benchmark/core_scale 0-4 launchserver
./amd_redis_core_scale.sh 504857 127.0.0.1 1:4 5C_rd redis 192-255 /root/redis_memcachd_memtier_benchmark/core_scale 0-4
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:0 6C_wr redis 192-193 /root/redis_memcachd_memtier_benchmark/core_scale 0-5 launchserver
./amd_redis_core_scale.sh 504857 127.0.0.1 1:4 6C_rd redis 192-255 /root/redis_memcachd_memtier_benchmark/core_scale 0-5
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:0 7C_wr redis 192-193 /root/redis_memcachd_memtier_benchmark/core_scale 0-6 launchserver
./amd_redis_core_scale.sh 504857 127.0.0.1 1:4 7C_rd redis 192-255 /root/redis_memcachd_memtier_benchmark/core_scale 0-6
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:0 8C_wr redis 192-193 /root/redis_memcachd_memtier_benchmark/core_scale 0-7 launchserver
./amd_redis_core_scale.sh 504857 127.0.0.1 1:4 8C_rd redis 192-255 /root/redis_memcachd_memtier_benchmark/core_scale 0-7
