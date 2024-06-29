# intel_cnb_data_cloud_benchmark

#How to run on cloud
## Runing on GCP
   python3 pkb.py --cloud=GCP --benchmarks=intel_cnb_data_cloud --machine_type=n2-standard-32 --os_type=ubuntu1804 --zone=us-west1-b

## Supported OS
  Ubuntu 18.04 20.04

## Minimum Requirements
   It is highly recommended to run this benchmark on high end servers. While running, the benchmark will scale to utilize all the cores available. However, for functional testing, your physical node or VM must have at least:
	16 logical or virtual CPUs
	8GB Ram
	10GB Disk Space.

## Benchmark inputs
   Fine tune the final results by modifying the parameters inside cnb-analytics_config.json
