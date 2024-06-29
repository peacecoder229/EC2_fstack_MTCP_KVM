# intel_cnb_container_single_1 benchmark

#How to run on OnPrem
## Runing on Ubuntu
  python3 pkb.py --benchmarks=intel_cnb_container_single_1 --data_search_paths=path/to/ISOs/tars/yaml/and/script --benchmark_config_file=cnb_container.yaml
## Runing on Centos
  Not supported
## Supported OS
  Ubuntu 18.04

## Minimum Requirements
   It is highly recommended to run this benchmark on high end servers. While running, the benchmark will scale to utilize all the cores available. However, for functional testing, your physical node or VM must have at least:
	16 logical or virtual CPUs
	8GB Ram
	10GB Disk Space.
Benchmark inputs
Benchmark config yaml – cluster_config.json. Example shown below.
Example configuration for a three node cluster:
  ```
 "nodes": [
        {
            "ip_address": "192.168.0.11",
            "hostname": "master"
        },
        {
            "ip_address": "192.168.0.12",
            "hostname": "worker1"
        },
        {
            "ip_address": "192.168.0.13",
            "hostname": "worker2"
        }
    ],


