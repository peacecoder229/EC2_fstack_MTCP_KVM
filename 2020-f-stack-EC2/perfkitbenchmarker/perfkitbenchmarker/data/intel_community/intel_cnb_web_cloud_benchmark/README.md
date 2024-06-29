# intel_cnb_web_cloud benchmark

# How to run on On CSP

## Run on AWS
python3 pkb.py --cloud=AWS --benchmarks=intel_cnb_web_cloud --machine_type=m5.4xlarge --os_type=ubuntu1804  --zone=us-east-2c

## Run on GCP
python3 pkb.py --cloud=GCP --benchmarks=intel_cnb_web_cloud --machine_type=n2-standard-32 --os_type=ubuntu1804 --zone=us-west1-b

## Run on Azure
python3 pkb.py --cloud=Azure --benchmarks=intel_cnb_web_cloud --machine_type=Standard_D16as_v4 --os_type=ubuntu1804  --zone=eastus
