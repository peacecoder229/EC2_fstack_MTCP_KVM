# intel_cnb_web_single_1 benchmark

#How to run on OnPrem
## Runing on Ubuntu
  python3 pkb.py --benchmarks=intel_cnb_web_single_1 --data_search_paths=perfkitbenchmarker/data/intel_community/intel_cnb_web_single_1_benchmark --benchmark_config_file=cnb_web.yaml

### Flags:

`--[no]install_k8s`: Setting to true to install Kubernetes cluster before benchmark run
    (default: 'false')

`--[no]remove_k8s`: Setting to true to remove Kubernetes cluster after benchmark finish
    (default: 'false')

## Supported OS
  Ubuntu 18.04 20.04

## Minimum Requirements
   It is highly recommended to run this benchmark on high end servers. While running, the benchmark will scale to utilize all the cores available. However, for functional testing, your physical node or VM must have at least:
	16 logical or virtual CPUs
	8GB Ram
	10GB Disk Space.

## Benchmark inputs
### Benchmark config yaml – cnb_web.yaml

### cluster_config.json. Example shown below.
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
  ```
