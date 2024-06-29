# Intel Memcached Benchmark

## Foreword
The workload gradually increases the number of YCSB client processes until the maximum throughput of Memcached is determined.

## Running intel_memcached with PKB
### Sample benchmark configuration files 
* intel_memcached_cloud.yaml
* intel_memcached_static.yaml

### Command line
```
./pkb.py --cloud=AWS --benchmarks=intel_memcached --benchmark_config_file=../intel_memcached_cloud.yaml
```

### Required Configuration
* ycsb_client_vms: The number of client machines to use during the execution of the workload. For best results, at least 4 client machines are needed to drive load. If using less-capable clients, more may be needed.

### Example Output
```
-------------------------PerfKitBenchmarker Results Summary-------------------------
  Maximum Throughput                    1249924.148871 ops/sec
  Maximum Throughput for Latency SLA    942903.381829 ops/sec
```

## Tuning Notes
Network is typically the primary bottleneck. To increase CPU utilization on the server: 1) ensure best performing network; 2) if clients are saturated, increase client VM count.

### Workload files
* benchmark file in linux_benchmark => intel_memcached_benchmark.py
* module files in linux_packages    => intel_memcached_server.py, ycsb.py
