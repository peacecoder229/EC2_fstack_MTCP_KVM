#!/bin/bash
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:0 mc3C_wr memcache_text 192-193 /root/redis_memcachd_memtier_benchmark/core_scale 0-2 launchmemcache
./amd_redis_core_scale.sh 504857 127.0.0.1 1:4 mc3C_rd memcache_text 192-215 /root/redis_memcachd_memtier_benchmark/core_scale 0-2
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:0 mc4C_wr memcache_text 192-193 /root/redis_memcachd_memtier_benchmark/core_scale 0-3 launchmemcache
./amd_redis_core_scale.sh 504857 127.0.0.1 1:4 mc4C_rd memcache_text 192-223 /root/redis_memcachd_memtier_benchmark/core_scale 0-3
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:0 mc5C_wr memcache_text 192-193 /root/redis_memcachd_memtier_benchmark/core_scale 0-4 launchmemcache
./amd_redis_core_scale.sh 504857 127.0.0.1 1:4 mc5C_rd memcache_text 192-231 /root/redis_memcachd_memtier_benchmark/core_scale 0-4
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:0 mc6C_wr memcache_text 192-193 /root/redis_memcachd_memtier_benchmark/core_scale 0-5 launchmemcache
./amd_redis_core_scale.sh 504857 127.0.0.1 1:4 mc6C_rd memcache_text 192-239 /root/redis_memcachd_memtier_benchmark/core_scale 0-5
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:0 mc7C_wr memcache_text 192-193 /root/redis_memcachd_memtier_benchmark/core_scale 0-6 launchmemcache
./amd_redis_core_scale.sh 504857 127.0.0.1 1:4 mc7C_rd memcache_text 192-247 /root/redis_memcachd_memtier_benchmark/core_scale 0-6
./amd_redis_core_scale.sh 1048576 127.0.0.1 1:0 mc8C_wr memcache_text 192-193 /root/redis_memcachd_memtier_benchmark/core_scale 0-7 launchmemcache
./amd_redis_core_scale.sh 504857 127.0.0.1 1:4 mc8C_rd memcache_text 192-255 /root/redis_memcachd_memtier_benchmark/core_scale 0-7
