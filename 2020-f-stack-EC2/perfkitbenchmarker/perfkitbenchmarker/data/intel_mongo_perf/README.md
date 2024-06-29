# Intel Mongo-perf Benchmark

## Foreword
This client-server workload requires exactly one client and one worker machine. Recommend at least a 10Gb network connection between the client and worker. One MongoDB instances is started in a Docker container for every twelve vCPUs on the worker machine. The Mongo Shell is run via Docker on the client machine. One instance per MongoDB instance. The Mongo Shell is the load generator running a javascript program that makes calls to the MongoDB servers. 

Although MongoDB utilizes the WiredTiger engine, the database is small and will typically fit in the WT cache and/or the system cache. Disk I/O should be minimal.

In contrast to other MongoDB workload (e.g. MongoDB stress), the purpose of this workload is to demonstrate architectural (CPU) differences, e.g. gen-2-gen and competitive.

## Running intel_mongo_perf with PKB
### Sample benchmark configuration files 
* intel_mongo_perf_cloud.yaml
* intel_mongo_perf_static.yaml

### Command line
```
./pkb.py --cloud=AWS --benchmarks=intel_mongo_perf --benchmark_config_file=../intel_mongo_perf_cloud.yaml
```

### Performance Metric
- Maximum Throughput - The maximum transactions/sec observed from in all iterations.

### Configuration

### Workload behavior options

  --mongo_perf_client_thread_count: The number of threads each client will use to drive load. When not set, the thread count will be set to the
    number of vCPUs on the server.
    (an integer in the range [1, 128])

  --mongo_perf_vcpus_per_mongodb_instance: The number of vCPUs per MongoDB instance. Controls the number of MongoDB instances used in the
    benchmark.
    (default: '12')
    (a positive integer)

  --mongo_perf_iteration_count: The number of times to measure performance. The best result will be reported.
    (default: '5')
    (a positive integer)

  --mongo_perf_duration: The number of seconds to run in each iteration.
    (default: '60')
    (a positive integer)

  --mongo_perf_mongodb_docker_image: Docker image for MongoDB that will be used.
    (default: 'harppdx/mongo-enterprise:4.4')

### Crypto options

  --[no]mongo_perf_require_tls: Use TLS secure communications between Mongo client and database server.
    (default: 'true')

  --mongo_perf_tls_key_type: Specify the key type to use for TLS.
    (default: 'rsa')

  --mongo_perf_tls_key_size: Specify the key size for TLS...typically 2048 or 4096.
    (default: '2048')
    (an integer)
