## Kafka Autoscaling Benchmark

## Foreword
The workload gradually increases the number of producer and consumer instances until the maximum throughput of the Kafka cluster is determined.

## Running Kafka with PKB
### Sample configuration files 
* kafka_cloud.yaml
* kafka_static.yaml

### Command line
```
./pkb.py --cloud=AWS --benchmarks=kafka --benchmark_config_file=./kafka_cloud.yaml
```

### Details
Download or clone the repo. Checkout branch if not merged into master. If setting up PKB from scratch, please check https://gitlab.devtools.intel.com/PerfKitBenchmarker/perfkitbenchmarker/-/blob/master/README.md for instructions. If you need to configure PKB to run on AWS, please follow the wiki https://wiki.ith.intel.com/display/cloudperf/How+to+run+PKB+on+AWS. The following sections will cover how to setup and run Kafka in baremetal.

### Baremetal setup
Kafka needs a minimum of two client nodes (producer and consumer) and 1 server node (broker) to be setup. For ideal scaling, the two client nodes should be connected to the server through a fast network. It is also recommended to use NVMe SSDs(2-4) in the broker as the workload is network and disk throughput sensitive. If setting up a software disk array, the mdadm linux tool can be used to create a RAID0 array. It is recommended to eliminate defunct Java processes on the broker and reset the disk array after every run.

Passwordless login using SSH keys needs to be setup between the nodes and the gateway (if using a separate launch host for PKB). Please follow the instructions to enable passwordless login between the PKB host and the SUT https://wiki.ith.intel.com/display/cloudperf/How+to+run+PKB+On-Prem
   

### Required Configuration
* kafka_consumer_vms: The number of vms for consumer, use a minimum of 2 vms for best results
* kafka_producer_vms: The number of vms for producer, use a minumum of 2 vms for best results

### Example Output
```
-------------------------PerfKitBenchmarker Results Summary-------------------------
  Maximum Throughput                 1162.580000 MB/s
  Maximum Throughput for Latency SLA      190.640000 MB/s
```

## Tuning Notes
Network and storage throughput are typically the bottleneck. But if the workload is not saturating the network, and disk throughput is not a bottleneck then tuning the following parameters will increase CPU utilization and optimize the overall throughput and throughput under sla.
1)num.network.threads : 3 (default)
Increase this value based on the number of producers, and consumers that are connected to the server. 
2)num.io.threads: 8 (default) 
Sets the number of threads spawned for IO operations. This should be set to a multiple of the number of disks present in the system.
