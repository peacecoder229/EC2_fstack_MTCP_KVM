# MongoDB Stress Benchmark

## Foreword
The workload gradually increases the number of MongoDB instances and number of YCSB client processes until the maximum throughput is determined.

## Running mongodb_stess with PKB
### Sample benchmark configuration files 
* mongodb_stress_cloud.yaml
* mongodb_stress_static.yaml

### Command line
```
./pkb.py --cloud=AWS --benchmarks=mongodb_stress --benchmark_config_file=../mongodb_stress_cloud.yaml
```

### Required Configuration
* ycsb_client_vms: The number of client machines to use during the execution of the workload. For best results, at least 2 client machines are needed to drive load. If using less-capable clients, more may be needed.

### Example Output
```
-------------------------PerfKitBenchmarker Results Summary-------------------------
  Maximum Throughput                    49924.148871 ops/sec
  Maximum Throughput for Latency SLA    42903.381829 ops/sec
```

### Tuning Notes
The workload is highly dependent on network and storage subsystem performance. If CPU utilization on server is not >90%, determine if network or storage bandwidth is saturated. If neither, consider need to increase number of clients.

### Workload files
* benchmark file in linux_benchmarks =>  mongodb_stress_benchmark.py
* module files in linux_packages    =>  mongodb.py, ycsb.py

### On bare metal
If you encounter an error "Error: Could not find or load main class org.HdrHistogram.HistogramLogProcessor" while running the mongodb_stress workload in baremetal setting, then specify pkb proxy flag on the command line
```
--http_proxy=http://proxy-chain.intel.com:911 
--https_proxy=https://proxy-chain.intel.com:912
```

## How it works (details)
The Maximum Throughput metric refers to the number of database operations (reads and updates) that occur per second.

MongoDB does not scale well across many cores/threads, so to stress a large system we must run multiple instances. In addition, we’ve made a choice to force MongoDB to use the storage subsystem to be more real-world realistic by limiting the amount of memory available to each MongoDB instance. Note: older versions of this workload allowed the entire database to reside in memory and/or file cache. We use stress-ng to allocate memory in a way that makes it unavailable to MongoDB and the file cache.

The workload starts with one instance of MongoDB and one instance of YCSB (client). The load that the YCSB client puts on MongoDB is fixed, by default, at 25000 ops/sec. We found this rate easily achievable on most systems, although this may not be true on systems with limited network and/or storage throughput.

The workload loads each database with a number of records relative to the amount of memory and vcpus available on the system.

The workload repeatedly loads database(s), measures read/update throughput and latency for 3 minutes, and then cleans up. For each iteration, an additional MongoDB instance and YCSB instance are added. It will continue in this loop until the throughput goes down for two successive iterations. At that point the best results are records -- Maximum Throughput and Maximum Throughput that met the prescribed SLA (by default p99 read latency less than 3ms).
