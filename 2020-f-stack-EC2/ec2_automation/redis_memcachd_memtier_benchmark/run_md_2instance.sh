#!/bin/bash
pkill -9 memcached
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:0 inst1_wr memcache_text 28-29 /root/redis_memcachd_memtier_benchmark/core_scale 1-5 9001 launchmemcache &
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:0 inst2_wr memcache_text 29-30 /root/redis_memcachd_memtier_benchmark/core_scale 6-11 9002 launchmemcache &
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:0 inst3_wr memcache_text 30-31 /root/redis_memcachd_memtier_benchmark/core_scale 12-17 9003 launchmemcache &
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:0 inst4_wr memcache_text 32-33 /root/redis_memcachd_memtier_benchmark/core_scale 18-23 9004 launchmemcache

./amd_redis_core_scale.sh 1048576 127.0.0.1 1:4 inst1_rd memcache_text  28-33,84-89 /root/redis_memcachd_memtier_benchmark/core_scale 0-5  9001 &
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:4 inst2_rd memcache_text 34-39,90-95 /root/redis_memcachd_memtier_benchmark/core_scale 6-11 9002 &
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:4 inst3_rd memcache_text 40-45,96-101 /root/redis_memcachd_memtier_benchmark/core_scale 12-17 9003 &
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:4 inst4_rd memcache_text 46-51,102-107 /root/redis_memcachd_memtier_benchmark/core_scale 18-23 9004
