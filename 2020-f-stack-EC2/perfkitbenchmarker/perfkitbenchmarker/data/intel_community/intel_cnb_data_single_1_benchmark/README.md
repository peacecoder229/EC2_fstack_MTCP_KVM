# intel_cnb_data_single_1 benchmark

# How to run on OnPrem
## Runing on Ubuntu
   python3 pkb.py --benchmarks=intel_cnb_data_single_1 --data_search_paths=perfkitbenchmarker/data/intel_community/intel_cnb_data_single_1_benchmark --benchmark_config_file=cnb_data.yaml

### Flags:

`--[no]cleanup_setup`: Setting to true to clean up all the dependencies installed during setup
    (default: 'true')

`--[no]install_setup`: Setting to true to install all the dependencies for benchmark to run
    (default: 'true')

## Supported OS
  Ubuntu 18.04 20.04

## Minimum Requirements
   It is highly recommended to run this benchmark on high end servers. While running, the benchmark will scale to utilize all the cores available. However, for functional testing, your physical node or VM must have at least:
	16 logical or virtual CPUs
	8GB Ram
	10GB Disk Space.

## Benchmark inputs
### Benchmark config yaml – cnb_data.yaml

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

### cnb-analytics_config.json
Refer to the following codes and fine tune the best results by modifying the parameters inside cnb-analytics_config.json

```
# best_case_setup(num_cores)
# num_cores=`grep -c ^processor /proc/cpuinfo`
case "$num_cores" in
  16) Lambda=(88 90 92 95 98); vCPU_per_POD=(12);
      # vCPU_per_POD=(12)
      # AWS Lambda=(88); vCPU_per_POD=(12);
      # Azure Lambda=(88); vCPU_per_POD=(12);
      # GCP Lambda=(95); vCPU_per_POD=(12);
      ;;
  32) Lambda=(37 38); vCPU_per_POD=(14);
      # vCPU_per_POD=(14)
      # Azure Lambda=(38); vCPU_per_POD=(14);
      # GCP Lambda=(47); vCPU_per_POD=(14);
      # 4S-CLX8256 Lambda=(43); vCPU_per_POD=(14);
      ;;
  48) Lambda=(31 32 33); vCPU_per_POD=(22);
      # vCPU_per_POD=(22)
      # AWS Lambda=(31); vCPU_per_POD=(22);
      # Azure Lambda=(32); vCPU_per_POD=(22);
      # GCP Lambda=(33); vCPU_per_POD=(22);
      ;;
  64) Lambda=(26 27 28); vCPU_per_POD=(20);
      # AWS Lambda=(28); vCPU_per_POD=(20);
      # Azure Lambda=(27); vCPU_per_POD=(20);
      # GCP Lambda=(31); vCPU_per_POD=(20);
      # BDW-E74809V4 Lambda=(58); vCPU_per_POD=(30);
      ;;
  72) Lambda=(31 32); vCPU_per_POD=(34);
      # vCPU_per_POD=(34 17)
      # HSW-E52699V3 Lambda=(31 32); vCPU_per_POD=(34);
      ;;
  80) Lambda=(24 25); vCPU_per_POD=(25);
      # vCPU_per_POD=(38 19 12)
      # BWD-E52699V4 Lambda=(31 32); vCPU_per_POD=(34);
      # GCP Lambda=(25); vCPU_per_POD=(25);
      ;;
  88) Lambda=(24 25); vCPU_per_POD=(14 18);
      # vCPU_per_POD=(42 21 14)
      # BWD-E52699V4 Lambda=(31 32); vCPU_per_POD=(34);
      ;;
  96) Lambda=(17 18 19 20); vCPU_per_POD=(15);
      # vCPU_per_POD=(46 23 15)
      # CLX-6248R Lambda=(18 19); vCPU_per_POD=(15);
      # CLX-8268 Lambda=(19 20); vCPU_per_POD=(15);
      # Rome-7402 Lambda=(21 22); vCPU_per_POD=(15);
      # ICX-24C Lambda=(17 18); vCPU_per_POD=(15);
      ;;
  112) Lambda=(17 18 19 20); vCPU_per_POD=(15 18);
       # vCPU_per_POD=(54 27 18 13)
       # ICX-28C Lambda=(19 20); vCPU_per_POD=(18);
       # CLX-8280 Lambda=(17 18); vCPU_per_POD=(15);
       # 4S-SKX-5120 Lambda=(29 30); vCPU_per_POD=(27);
       ;;
  128) Lambda=(12 13); vCPU_per_POD=(12 13);
       # vCPU_per_POD=(62 31 20 15 12)
       # ICX-32C Lambda=(12 13); vCPU_per_POD=(13);
       # Rome-7542 Lambda=(17 18); vCPU_per_POD=(20);
       # 4S-CPX-6328HL Lambda=(16); vCPU_per_POD=(15);
       ;;
  144) Lambda=(11 12); vCPU_per_POD=(14);
       # vCPU_per_POD=(70 35 23 17 14)
       # ICX-36C Lambda=(11 12); vCPU_per_POD=(14);
       ;;
  160) Lambda=(12 13); vCPU_per_POD=(19);
       # vCPU_per_POD=(78 39 26 19 15 13)
       # 4S-CPX-8353H Lambda=(12 13); vCPU_per_POD=(19);
       ;;
  192) Lambda=(22 23); vCPU_per_POD=(14)
       # vCPU_per_POD=(94 47 31 23 18 15 13)
       # CLX-6252Nx2 Lambda=(22 23); vCPU_per_POD=(14);
       # 4S-CPX-8353H Lambda=(15 16); vCPU_per_POD=(23);
       # 4S-BDX-6348H  Lambda=(12); vCPU_per_POD=(18);
       ;;
  224) Lambda=(6 7); vCPU_per_POD=(15);
       # vCPU_per_POD=(110 55 36 27 22 18 15)
       # 4S-CPX-8380H Lambda=(6 7); vCPU_per_POD=(15);
       # 4S-CPX-8280 Lambda=(11); vCPU_per_POD=(18);
       ;;
  256) Lambda=(12 13); vCPU_per_POD=(31);
       # vCPU_per_POD=(126 63 42 31 25 21 18)
       # Rome-7742 Lambda=(12 13); vCPU_per_POD=(31);
       ;;
  *) echo "No DataBase Records for $num_cores vCPUs"
     echo "Please edit this line with desired values..."
     Lambda=(20); vCPU_per_POD=(15);
     exit
     ;;
esac
```
