
## Intel HiBench benchmark guidelines

#### Foreword

[HiBench](https://github.com/Intel-bigdata/HiBench) is a collection of big data workloads running on top of the Hadoop or Spark frameworks (or both).

Although HiBench contains >20 workloads, the PKB integration at the moment is only functional and fully tested for:
* Spark/Terasort
  Sorting micro benchmark running on top of the Apache Spark and Apache Hadoop frameworks (600GB data set size).
* Spark/K-means
  K-means clustering benchmark running on top of the Apache Spark and Apache Hadoop frameworks (240GB data set size).

Both Terasort and K-means are distributed workloads and require at least 2 nodes (1 master and 1 data node). All the nodes (master and data nodes) need to have at least 600GB of free storage space. If no mountpoints are specified in the configuration (see example below), /tmp will be used for storing the necessary data. If mountpoints are specified, all nodes (master and data nodes) need to the same storage configuration (same number and location for the mountpoints).

For AWS, the disks will be automatically attached based on the number of mountpoints and disk size specified in the config below. For bare-metal, the mountpoints need to exist prior to running PKB (all disks need to be already formatted as ext4, mounted in the mountpoints and readable/writable by the pkb user). Details on how to format and mount disks for bare-metal can be found below.


## How to run Intel HiBench with PKB in AWS
After PKB is [installed and configured](https://github.intel.com/cspbench/PerfKitBenchmarker#installing-perfkit-benchmarker-and-prerequisites), the user will be able to run HiBench as following:

```
# K-means is run by default
python pkb.py --cloud=AWS --benchmarks=intel_hibench

# Terasort needs to be explicitly specified
python pkb.py --cloud=AWS --benchmarks=intel_hibench --intel_hibench_workloads=terasort
```

A benchmark config file can be provided, in order to control disk and instance types:
```
python pkb.py --cloud=AWS --benchmarks=intel_hibench --benchmark_config_file=./pkbconfig_hibench_cloud.py

cat ./pkbconfig_hibench_cloud.py
server_disk: &server_disk
  GCP:
    disk_type: pd-ssd
    disk_size: 300
    mount_point: /scratch
  Azure:
    disk_type: Premium_LRS
    disk_size: 300
    mount_point: /scratch
  AWS:
    disk_type: io1
    disk_size: 300
    iops: 15000
    mount_point: /scratch
 
intel_hibench:
  description: Build hibench workloads
  vm_groups:
    target:
      os_type: centos7
      disk_spec: *server_disk
      disk_count: 6
      vm_count: 5
      vm_spec:
        GCP:
            machine_type: n2-standard-80
            zone: us-central1-a
            image: null
        Azure:
            machine_type: Standard_D64s_v3
            zone: eastus2
            image: null
        AWS:
            machine_type: m5.24xlarge
            zone: us-east-2
            image: null
```

On AWS, a default setup of 5 m5.24xlarge instances (1 master node + 4 data nodes), running CentOS 7, each with 6 300GB storage SSDs will be used. A custom configuration can be specified via HiBench-specific command line flags, as well as configurations available in [perfkitbenchmarker/data/intel_hibench_benchmark/config.yml](https://gitlab.devtools.intel.com/PerfKitBenchmarker/perfkitbenchmarker/tree/master/perfkitbenchmarker/data/intel_hibench_benchmark/config.yml):
* __HiBench specific command line flags__

    * `intel_hibench_spark_version=<default_value_is_2.2.2>`

      if specified, this flag will install a specific version of Spark.
    * `intel_hibench_scala_version=<default_value_is_2.11.0>`

      if specified, this flag will install a specific version of Scala.
    * `intel_hibench_hadoop_version=<default_value_is_2.9.1>`

      if specified, this flag will install a specific version of Hadoop.
    * `intel_hibench_framework=<default_value_is_spark>`

      can be either `hadoop` or `spark`. HiBench provides either a pure Hadoop implementation for workloads, as well as a Spark implementation (which still uses Hadoop for distributed storage). Only the Spark implementation was tested.
    * `intel_hibench_workloads=<default_value_is_kmeans>`

      can be either `kmeans` or `terasort` at this point. Other Hibench workloads might work, but they were not tested.
    * `intel_hibench_maven_version=<default_value_is_3.6.0>`

      if specified, this flag will install a specific version of Maven.

* __PKB specific command line flags__

    * `--machine-type=<default_value_depends_on_cloud_provider>`

      if specified, this flag will determine the instance type to be used instead of the default

* __[perfkitbenchmarker/data/intel_hibench_benchmark/config.yml](https://gitlab.devtools.intel.com/PerfKitBenchmarker/perfkitbenchmarker/tree/master/perfkitbenchmarker/data/intel_hibench_benchmark/config.yml)__

```
# The values that are commented out below are dynamically computed by the workload to
# provide optimal performance on any system. Please de-comment if you want to experiment
# with different values.

hibench:
# hibench.scale.profile: bigdata  # Automatically calculated by default. Available values: tiny, small, large, huge, gigantic, bigdata
# hibench.default.map.parallelism: 280
# hibench.default.shuffle.parallelism: 280
spark:
  hibench.spark.master: yarn-client  # Available values: spark, yarn-client
# hibench.yarn.executor.num: 56
# hibench.yarn.executor.cores: 5
# spark.executor.memory: 8g
  spark.driver.memory: 4g
scratch_disks:
    mountpoints: # Ignore for cloud runs. The mountpoints are specified via user configs.
      - /data/data0
      - /data/data1
      - /data/data2
      - /data/data3
      - /data/data4
      - /data/data5
# Kmeans presets
kmeans:
  tiny:
      kmeans_num_of_clusters: 5
      kmeans_dimensions: 10
      kmeans_num_of_samples: 300000000
      kmeans_samples_per_inputfile: 5000000
      kmeans_max_iteration: 5
      kmeans_k: 10
      kmeans_convergedist: 0.5
  small:
      kmeans_num_of_clusters: 5
      kmeans_dimensions: 10
      kmeans_num_of_samples: 1200000000
      kmeans_samples_per_inputfile: 10000000
      kmeans_max_iteration: 5
      kmeans_k: 10
      kmeans_convergedist: 0.5
  large:
      kmeans_num_of_clusters: 5
      kmeans_dimensions: 20
      kmeans_num_of_samples: 600000000
      kmeans_samples_per_inputfile: 4000000
      kmeans_max_iteration: 5
      kmeans_k: 20
      kmeans_convergedist: 0.5
  huge:
      kmeans_num_of_clusters: 5
      kmeans_dimensions: 20
      kmeans_num_of_samples: 1000000000
      kmeans_samples_per_inputfile: 20000000
      kmeans_max_iteration: 5
      kmeans_k: 20
      kmeans_convergedist: 0.5
  gigantic:
      kmeans_num_of_clusters: 5
      kmeans_dimensions: 20
      kmeans_num_of_samples: 1200000000
      kmeans_samples_per_inputfile: 40000000
      kmeans_max_iteration: 5
      kmeans_k: 20
      kmeans_convergedist: 0.5
  bigdata:
      kmeans_num_of_clusters: 5
      kmeans_dimensions: 20
      kmeans_num_of_samples: 2000000000
      kmeans_samples_per_inputfile: 40000000
      kmeans_max_iteration: 5
      kmeans_k: 40
      kmeans_convergedist: 0.5
```


## How to run HiBench with PKB on bare-metal
PKB allows passing a configuration file (.yml), in order to be able to run the workload on bare metal. The command will be as following:

```
# K-means is run by default
./pkb.py --benchmarks=intel_hibench --benchmark_config_file=./pkbconfig_hibench.yml

# Terasort needs to be explicitly specified
./pkb.py --benchmarks=intel_hibench --benchmark_config_file=./pkbconfig_hibench.yml --intel_hibench_workloads=terasort
```

Example for pkbconfig_hibench.yml:
```
static_vms:
  - &vm0
    ip_address: <master_ip_address>
    user_name: pkb
    os_type: rhel
    ssh_private_key: ~/.ssh/id_rsa
    internal_ip: <master_ip_address>
  - &vm1
    ip_address: <data_node_1_ip_address>
    user_name: pkb
    os_type: rhel
    ssh_private_key: ~/.ssh/id_rsa
    internal_ip: <data_node_1_ip_address>
  - &vm2
    ip_address: <data_node_2_ip_address>
    user_name: pkb
    os_type: rhel
    ssh_private_key: ~/.ssh/id_rsa
    internal_ip: <data_node_2_ip_address>
  - &vm3
    ip_address: <data_node_3_ip_address>
    user_name: pkb
    os_type: rhel
    ssh_private_key: ~/.ssh/id_rsa
    internal_ip: <data_node_3_ip_address>
intel_hibench:
  vm_groups:
    target:
      static_vms:
        - *vm0
        - *vm1
        - *vm2
        - *vm3
```

Additionally, similarly to AWS, the bare metal setup can be customized via HiBench-specific command line flags, as well as configurations available in [perfkitbenchmarker/data/intel_hibench_benchmark/config.yml](https://gitlab.devtools.intel.com/PerfKitBenchmarker/perfkitbenchmarker/tree/master/perfkitbenchmarker/data/intel_hibench_benchmark/config.yml):
* __[perfkitbenchmarker/data/intel_hibench_benchmark/config.yml](https://gitlab.devtools.intel.com/PerfKitBenchmarker/perfkitbenchmarker/tree/master/perfkitbenchmarker/data/intel_hibench_benchmark/config.yml)__

```
# The values that are commented out below are dynamically computed by the workload to
# provide optimal performance on any system. Please de-comment if you want to experiment
# with different values.

hibench:
  hibench.scale.profile: bigdata  # Available values: tiny, small, large, huge, gigantic, bigdata
# hibench.default.map.parallelism: 280
# hibench.default.shuffle.parallelism: 280
spark:
  hibench.spark.master: yarn-client  # Available values: spark, yarn-client
# hibench.yarn.executor.num: 56
# hibench.yarn.executor.cores: 5
# spark.executor.memory: 8g
  spark.driver.memory: 4g
scratch_disks:
    mountpoints: # These need to be already mounted on all machines prior to running HiBench
      - /data/data0
      - /data/data1
      - /data/data2
      - /data/data3
      - /data/data4
      - /data/data5
```


## Onboarding of a target system
SSH to the target systems and create a passwordless user:

`sudo useradd -m <username>`

Make it sudoer:

`sudo usermod -aG sudo <username>` \
Note: wheel group for Centos

Configure the user to not ask for the password, ssh keys will be used for authentication:

`sudo visudo` \
In nano editor, look for following lines:

>Allow members of group sudo to execute any command \
>%sudo ALL=(ALL:ALL) ALL

right below add the following:

>\<username> ALL=(ALL:ALL) NOPASSWD:ALL

save and exit.

Copy your key to the target system:

Copy your workstation identity (~/.ssh/id_rsa.pub) to target system user authorized keys file (/home/<username>/.ssh/authorized_keys) Make sure ansible user owns the .ssh folder and it's content on the target system.

`cat ~/.ssh/id_rsa.pub | ssh <username>@<hostname> 'cat >> .ssh/authorized_keys'`
Now trying to ssh into <username>@<hostname> should not require a password.

Format and mount __all__ data disks on the target systems (leave the boot disk alone). Only do this once:
* Create data partition and format the disks (if not done already)
```
# create partition
sudo fdisk /dev/sdX
  type 'n' to create a new partition
  specify where you want the partition to start and end (use default values - entire disk size)
  type 'w' to save the partition

# format the partition as ext4
sudo mkfs.ext4 /dev/sdX
```
* Create the mountpoints
```
sudo mkdir -p /data/data0

# then add the mountpoints to /etc/fstab
cat /etc/fstab
...
/dev/sdb             /data/data0       ext4    defaults,noatime        0       0
...

# finally, mount the drives and change permissions
sudo mount -a
sudo chown -R pkb:pkb /data/data0

# check that you can create a file on the new mount point, as pkb user
touch /data/data0/a.out
```

## Integration notes

At this time, Spark/K-means and Spark/Terasort are the only 2 HiBench workloads that were thoroughly tested for functionality and performance. They work on CentOS 7, on bare metal and on AWS (using the image ID specified above).
