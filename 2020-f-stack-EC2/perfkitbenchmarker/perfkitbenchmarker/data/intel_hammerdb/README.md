# Intel HammerDB - Postgres and MySQL

TOPICS :-
1. [Intel HammerDB with Postgres](#intel-hammerdb-with-postgres)
2. [Intel HammerDB with MySQL](#intel-hammerdb-with-mysql)
3. [PostgreSQL Runs on AWS ARM Graviton Instances](#postgresql-runs-on-aws-arm-graviton-instances)
4. [MySQL Runs on AWS ARM Graviton Instances](#mysql-runs-on-aws-arm-graviton-instances)
5. [Downloading Custom Packages for Intel HammerDB](#downloading-custom-packages-for-intel-hammerdb)
6. [Flags for Intel Hammerdb](#flags-for-intel-hammerdb)

##### HammerDB Versions
```
Currently the following version of HammerDB are supported :-

HammerDB v3.2
HammerDB v4.0

There is a flag which enables the user to choose between the two versions :-

intel_hammerdb_version  -Choose values from [3.2 , 4.0]
Default value is 4.0
```

* This application runs directly on the system and is NOT containerized.
* This runs on Ubuntu as well as Cent OS.

##### Databases Supported
```
HammerDB supports MySQL and Postgres databases.

There is a flag which determines which database should be used.

Flag :- --intel_hammerdb_db_type
Default Value is 'pg', which means Postgres database is used. We must change it to 'mysql' to run
MySQL. This must be added in every run.
```

##### Modes Supported
```
MySQL and Postgres can run on single node and multi node setups.

A flag has been created to distinguish between the two modes

FLAG :- intel_hammerdb_run_single_node	

Default Value is True, which means run server and client on the same hosts.
If False, run server and client on different hosts.
```

## Intel HammerDB with Postgres 

HammerDB with Postgres can run in two modes :-
1. Single Host :- HammerDB Server and Client installed on the same node
2. Multi Host :- HammerDB Server and  Client running on two different nodes

### Commands to run Intel HammerDB with Postgres

#### 1. Run on Single Host

AWS Run with HammerDB v4.0 :-
```
./pkb.py --cloud=AWS --benchmarks=intel_hammerdb --os_type=ubuntu2004 --machine_type=c5.24xlarge --zones=us-east-2
```
Bare Metal Run with HammerDB v4.0 :-
```
./pkb.py --benchmarks=intel_hammerdb  --benchmark_config_file=hammerdb_static_ubuntu.yml --os_type=ubuntu2004 --https_proxy='http://proxy-chain.intel.com:912' --intel_hammerdb_tpcc_postgres_hugepages="on"
```

AWS Run with HammerDBv3.2 :-
```
./pkb.py --cloud=AWS --benchmarks=intel_hammerdb --os_type=ubuntu2004 --machine_type=c5.24xlarge --zones=us-east-2  --intel_hammerdb_version='3.2'
```

#### 2. Run on Multiple Hosts ( Client & Server on different machines)
All the commands mentioned below run server and client on different nodes and if they need to run on a single node, add a flag --intel_hammerdb_run_single_node=True to the commands

AWS Run with HammerDB v4.0  :-
```
./pkb.py --cloud=AWS --benchmarks=intel_hammerdb --os_type=ubuntu2004 --machine_type=c5.24xlarge --zones=us-east-2 --intel_hammerdb_run_single_node=False
```

Azure Run with HammerDB v4.0:-
```
./pkb.py --cloud=Azure --benchmarks=intel_hammerdb --os_type=centos7 --machine_type=Standard_HC44rs --zone=westus2 --intel_hammerdb_run_single_node=False
```

GCP Run with HammerDB v4.0:-
```
./pkb.py --cloud=GCP --benchmarks=intel_hammerdb --os_type=centos7 --machine_type=c2-standard-60 --zones=us-central1-c --intel_hammerdb_run_single_node=False
```

GCP Run with HammerDB v3.2 :-
```
./pkb.py --cloud=GCP --benchmarks=intel_hammerdb --os_type=centos7 --machine_type=c2-standard-60 --zones=us-central1-c --intel_hammerdb_run_single_node=False
--intel_hammerdb_version='3.2'
```

Bare Metal Run :-
Run on Ubuntu2004 :-
```
 ./pkb.py --benchmarks=intel_hammerdb  --benchmark_config_file=hammerdb_static_ubuntu.yml --os_type=ubuntu2004 --https_proxy='http://proxy-chain.intel.com:912' --intel_hammerdb_run_single_node=False
```

###### Static Config File :- hammerdb_static_ubuntu.yml
```
static_vms:
    - &vm0
        ip_address: 10.X.X.X
        os_type: ubuntu2004
        user_name: pkb
        ssh_private_key: ~/.ssh/id_rsa
        internal_ip: 10.X.X.X
        disk_specs:
            - mount_point: /scratch
    - &vm1
        os_type: ubuntu2004
        ip_address: 10.X.X.X
        user_name: pkb
        ssh_private_key: ~/.ssh/id_rsa
        internal_ip: 10.X.X.X
 
intel_hammerdb:
    vm_groups:
        workers:
            static_vms:
                - *vm0
            vm_count: 1
        client:
            static_vms:
                - *vm1

flags:
  intel_hammerdb_tpcc_postgres_max_worker_process: 32
  intel_hammerdb_tpcc_postgres_wal_buffers: '-1'
  intel_hammerdb_tpcc_postgres_max_locks_per_transaction: 32
  intel_hammerdb_tpcc_postgres_max_pred_locks_per_transaction: 32
  intel_hammerdb_tpcc_postgres_hugepages: 'on'
  intel_hammerdb_tpcc_postgres_num_hugepages: 35000
```

For Run on Centos,  please replace --os_type=ubuntu2004 to --os_type = centos7 and provide the relevant IP addresses.

Following are the flags the users can modify to change the settings in postgresql.conf and settings for HammerDB 

### HugePages :-
  Setting the huge pages has a significant impact on the performance of the workload.

```
--intel_hammerdb_tpcc_postgres_hugepages	'off', 'on' or 'try'
--intel_hammerdb_tpcc_postgres_num_hugepages	The number of hugepages to be used
```

In the current implementation huge pages is off by default. 

The user must provide the intel_hammerdb_tpcc_postgres_hugepages flag and change it to try or on to enable hugepages.
```
--intel_hammerdb_tpcc_postgres_hugepages	Description
'Off'	Hugepages will not be used
'Try' & User sets the number	Hugepages will be used if it is enabled in the SUT and the number of hugepages will be equal to that set by the user using --intel_hammerdb_tpcc_postgres_num_hugepages
'Try' & User does not mention the number	Hugepages will be used if it is enabled in the SUT and the number will be decided by ( MemoryAllocatedtoProcess / Hugepagesize )
'On' & User sets the number	Hugepages will be used and the number of hugepages will be equal to that set by the user using --intel_hammerdb_tpcc_postgres_num_hugepages
'On' & User does not mention the number	Hugepages will be used and the number will be decided by ( MemoryAllocatedtoProcess / Hugepagesize )
```

Bare Metal Run with Hugepages "On"
(User decides to use 35000 )
```
./pkb.py --benchmarks=intel_hammerdb  --benchmark_config_file=hammerdb_static_ubuntu.yml --os_type=ubuntu2004 --https_proxy='http://proxy-chain.intel.com:912' --intel_hammerdb_tpcc_postgres_hugepages="on" --intel_hammerdb_tpcc_postgres_num_hugepages=35000
```

Bare Metal Run with Hugepages "On"
(User does not mention the number)
```
./pkb.py --benchmarks=intel_hammerdb  --benchmark_config_file=hammerdb_static_ubuntu.yml --os_type=ubuntu2004 --https_proxy='http://proxy-chain.intel.com:912' --intel_hammerdb_tpcc_postgres_hugepages="on"
```

AWS Run with Hugepages "On"
```
./pkb.py --cloud=AWS --benchmarks=intel_hammerdb --os_type=ubuntu2004 --machine_type=c5.24xlarge --zones=us-east-2  --intel_hammerdb_tpcc_postgres_hugepages="on"
```

# Intel HammerDB with MySQL
- This application runs directly on the system and is NOT containerized.
- This has been tested on Ubuntu ( Ubuntu 18.04 and Ubuntu 20.04 ) as well as Cent OS.

MySQL can run on single node and multinode

MySQL runs on single node :-

#### Single Host :- HammerDB Server and Client installed on the same node .

1. Run on AWS

AWS Run on Ubuntu2004 with HammerDB v4.0 :-
```
./pkb.py --cloud=AWS --benchmarks=intel_hammerdb --intel_hammerdb_db_type=mysql --machine_type=c5.24xlarge --zones=us-east-1a --os_type=ubuntu2004 --svrinfo --collectd --kafka_publish
```

AWS Run on Ubuntu2004 with HammerDB v3.2 :-
```
./pkb.py --cloud=AWS --benchmarks=intel_hammerdb --intel_hammerdb_db_type=mysql --machine_type=c5.24xlarge --zones=us-east-1a --os_type=ubuntu2004 --svrinfo --collectd --kafka_publish  --intel_hammerdb_version='3.2'
```

AWS Run on CentOs with HammerDB v4.0 :-
```
./pkb.py --cloud=AWS --benchmarks=intel_hammerdb --intel_hammerdb_db_type=mysql --machine_type=c5.24xlarge --zones=us-east-1a --os_type=centos7 --svrinfo --collectd --kafka_publish
```

2. Run on Azure
Azure Run on Ubuntu2004 with HammerDB v4.0 :-
```
./pkb.py --cloud=Azure --benchmarks=intel_hammerdb --machine_type=Standard_E16s_v3  --zones=westus2 --intel_hammerdb_db_type='mysql' --intel_hammerdb_tpcc_mysql_hugepages='on'   --os_type=ubuntu2004
```

Azure Run on Ubuntu2004 with HammerDB v3.2 :-
```
./pkb.py --cloud=Azure --benchmarks=intel_hammerdb --machine_type=Standard_E16s_v3  --zones=westus2 --intel_hammerdb_db_type='mysql' --intel_hammerdb_tpcc_mysql_hugepages='on'   --os_type=ubuntu2004 --intel_hammerdb_version='3.2'
```

Azure Run on CentOS with HammerDB v4.0 :-
```
./pkb.py --cloud=Azure --benchmarks=intel_hammerdb --machine_type=Standard_E16s_v3  --zones=westus2 --intel_hammerdb_db_type='mysql' --intel_hammerdb_tpcc_mysql_hugepages='on'   --os_type=centos7
```

3. Run on Bare Metal

Bare Metal Run with HammerDBv4.0 :-
```
./pkb.py --benchmarks=intel_hammerdb  --intel_hammerdb_db_type=mysql --benchmark_config_file=hammerdb_static_ubuntu.yml --os_type=ubuntu2004 --https_proxy='http://proxy-chain.intel.com:912'
```

#### MySQL runs on multi node :-

#### Multiple Hosts :- HammerDB Server and Client installed on different nodes.

1. Run on AWS
AWS Run on Ubuntu2004 with HammerDB v4.0:-
```
./pkb.py --cloud=AWS --benchmarks=intel_hammerdb --intel_hammerdb_db_type=mysql  --intel_hammerdb_run_single_node=False --machine_type=c5.24xlarge --zones=us-east-1a --os_type=ubuntu2004 --svrinfo --collectd --kafka_publish
```

AWS Run on Ubuntu2004 with HammerDB v3.2:-
```
./pkb.py --cloud=AWS --benchmarks=intel_hammerdb --intel_hammerdb_db_type=mysql  --intel_hammerdb_run_single_node=False --machine_type=c5.24xlarge --zones=us-east-1a --os_type=ubuntu2004 --svrinfo --collectd --kafka_publish --intel_hammerdb_version='3.2'
```

AWS Run on CentOs with HammerDB v4.0:-
```
./pkb.py --cloud=AWS --benchmarks=intel_hammerdb --intel_hammerdb_db_type=mysql --intel_hammerdb_run_single_node=False --machine_type=c5.24xlarge --zones=us-east-1a --os_type=centos7 --svrinfo --collectd --kafka_publish
```

2. Run on Azure
Azure Run on Ubuntu2004  with HammerDB v4.0:-
```
./pkb.py --cloud=Azure --benchmarks=intel_hammerdb --machine_type=Standard_E16s_v3  --zones=westus2 --intel_hammerdb_db_type='mysql' --intel_hammerdb_tpcc_mysql_hugepages='on'   --os_type=ubuntu2004 --intel_hammerdb_run_single_node=False
```

Azure Run on CentOS with HammerDB v4.0:-
```
./pkb.py --cloud=Azure --benchmarks=intel_hammerdb --machine_type=Standard_E16s_v3  --zones=westus2 --intel_hammerdb_db_type='mysql' --intel_hammerdb_tpcc_mysql_hugepages='on'    --os_type=centos7  --intel_hammerdb_run_single_node=False
```

3. Run on Bare Metal

Bare Metal Run with HammerDB v4.0:-
```
./pkb.py --benchmarks=intel_hammerdb  --intel_hammerdb_db_type=mysql --benchmark_config_file=hammerdb_static_ubuntu.yml --os_type=ubuntu2004 --https_proxy='http://proxy-chain.intel.com:912' --intel_hammerdb_run_single_node=False
```

###### hammerdb_static_ubuntu.yml
```
static_vms:
    - &vm0
        ip_address: 10.X.X.X
        os_type: ubuntu2004
        user_name: pkb
        ssh_private_key: ~/.ssh/id_rsa
        internal_ip: 10.X.X.X
        disk_specs:
            - mount_point: /scratch
    - &vm1
        os_type: ubuntu2004
        ip_address: 10.X.X.X
        user_name: pkb
        ssh_private_key: ~/.ssh/id_rsa
        internal_ip: 10.X.X.X
 
intel_hammerdb:
    vm_groups:
        workers:
            static_vms:
                - *vm0
            vm_count: 1
        client:
            static_vms:
                - *vm1

```
## PostgreSQL Runs on AWS ARM Graviton Instances

##### HammerDB Package does not run on ARM platform. Hence to support the run, we are running the PostgreSQL database on ARM and running hammerdb on an IA platform.
##### Please make sure you choose ARM as server and IA as client using the config file mentioned below.

```
In order to run on ARM platform we use this flag:-

--intel_hammerdb_platform - Choose from [ARM, None]

Default value is 'None' which supports IA and AMD.

```

AWS ARM Run on Ubuntu2004 with HammerDBv4.0

```
 python3 pkb.py  --cloud=AWS --benchmarks=intel_hammerdb   --benchmark_config_file=arm_aws_pg_hdb.yml  --intel_hammerdb_run_single_node=False  --intel_hammerdb_tpcc_postgres_hugepages=on --intel_hammerdb_platform=ARM  --os_type=ubuntu2004 --zone=us-east-1c --svrinfo --collectd --kafka_publish
```

AWS ARM Run on Ubuntu2004 with HammerDBv3.2
```
 python3 pkb.py  --cloud=AWS --benchmarks=intel_hammerdb   --benchmark_config_file=arm_aws_pg_hdb.yml  --intel_hammerdb_run_single_node=False  --intel_hammerdb_tpcc_postgres_hugepages=on --intel_hammerdb_platform=ARM  --os_type=ubuntu2004 --zone=us-east-1c --svrinfo --collectd --kafka_publish --intel_hammerdb_version='3.2'
```

###### arm_aws_pg_hdb_u2004.yml - Sample configuration file for ARM runs on AWS
```
###############################################################################
generic_executor_server: &generic_executor_server
  AWS:
    machine_type: m6g.16xlarge
    zone: us-east-1
    boot_disk_size: 200
    image: ami-02fb3fbca2bb793f1

generic_executor_server_disk: &generic_executor_server_disk
  AWS:
    disk_type: standard
    disk_size: 500
    mount_point: /scratch

generic_executor_client: &generic_executor_client
  AWS:
    machine_type: c5.18xlarge
    zone: us-east-1
    boot_disk_size: 200

## benchmark
###############################################################################
intel_hammerdb: {description: Running HammerDB_V2 (postgres) in AWS,
                 name: intel_hammerdb,
                 description: Run HammerDB against Postgres ,
                 vm_groups: {workers: {vm_spec: *generic_executor_server,
                                       disk_spec: *generic_executor_server_disk,
                                       vm_count: 1},
                             client: {vm_spec: *generic_executor_client}},
                 flags: {aws_provisioned_iops: 32000,
                         intel_hammerdb_tpcc_postgres_hugepages: 'on'}}

flags: {os_type: ubuntu2004}
```

## MySQL Runs on AWS ARM Graviton Instances

##### HammerDB Package does not run on ARM platform. Hence to support the run, we are running the MySQL database on ARM and running hammerdb on an IA platform.
##### Please make sure you choose ARM as server and IA as client using the config file mentioned below.

```
In order to run on ARM platform we use this flag:-

--intel_hammerdb_platform - Choose from [ARM, None]

Default value is 'None' which supports IA and AMD.

```

AWS ARM Run on Ubuntu2004 with HammerDBv4.0

```
 python3 pkb.py  --cloud=AWS --benchmarks=intel_hammerdb   --benchmark_config_file=arm_aws_mysql_hdb.yml  --intel_hammerdb_run_single_node=False  --intel_hammerdb_db_type=mysql --intel_hammerdb_tpcc_mysql_hugepages=on --intel_hammerdb_platform=ARM  --os_type=ubuntu2004 --zone=us-east-1c --svrinfo --collectd --kafka_publish
```

AWS ARM Run on Ubuntu2004 with HammerDBv3.2
```
 python3 pkb.py  --cloud=AWS --benchmarks=intel_hammerdb   --benchmark_config_file=arm_aws_mysql_hdb.yml  --intel_hammerdb_run_single_node=False  --intel_hammerdb_db_type=mysql --intel_hammerdb_tpcc_mysql_hugepages=on --intel_hammerdb_platform=ARM  --os_type=ubuntu2004 --zone=us-east-1c --svrinfo --collectd --kafka_publish --intel_hammerdb_version='3.2'
```

###### arm_aws_mysql_hdb_u2004.yml - Sample configuration file for ARM runs on AWS
```
###############################################################################
generic_executor_server: &generic_executor_server
  AWS:
    machine_type: m6g.16xlarge
    zone: us-east-1
    boot_disk_size: 200
    image: ami-02fb3fbca2bb793f1

generic_executor_server_disk: &generic_executor_server_disk
  AWS:
    disk_type: standard
    disk_size: 500
    mount_point: /scratch

generic_executor_client: &generic_executor_client
  AWS:
    machine_type: c5.18xlarge
    zone: us-east-1
    boot_disk_size: 200

## benchmark
###############################################################################
intel_hammerdb: {description: Running HammerDB_V2 (mysql) in AWS,
                 name: intel_hammerdb,
                 description: Run HammerDB against MySQL ,
                 vm_groups: {workers: {vm_spec: *generic_executor_server,
                                       disk_spec: *generic_executor_server_disk,
                                       vm_count: 1},
                             client: {vm_spec: *generic_executor_client}},
                 flags: {aws_provisioned_iops: 32000,
                         intel_hammerdb_db_type: 'mysql',
                         intel_hammerdb_tpcc_mysql_hugepages: 'on'}}

flags: {os_type: ubuntu2004}

```

## HugePages

Setting the huge pages has a significant impact on the performance of the workload.

```
--intel_hammerdb_tpcc_mysql_hugepages	'off' or 'on'
--intel_hammerdb_tpcc_mysql_num_hugepages	The number of hugepages to be used
```

In the current implementation huge pages is off by default.
The user must provide the intel_hammerdb_tpcc_mysql_hugepages flag and change it to on to enable hugepages.

```
--intel_hammerdb_tpcc_mysql_hugepages

'Off'	Hugepages will not be used
'On' & User sets the number	Hugepages will be used and the number of hugepages will be equal to that set by the user using --intel_hammerdb_tpcc_mysql_num_hugepages
'On' & User does not mention the number	Hugepages will be used and the number will be decided by memory allocated .
```

Bare Metal Run with Hugepages "On"
(User decides to use 35000 )
```
./pkb.py --benchmarks=intel_hammerdb  --benchmark_config_file=hammerdb_static_ubuntu.yml  --intel_hammerdb_db_type=mysql --os_type=ubuntu2004 --https_proxy='http://proxy-chain.intel.com:912' --intel_hammerdb_tpcc_mysql_hugepages="on" --intel_hammerdb_tpcc_mysql_num_hugepages=35000
```

Bare Metal Run with Hugepages "On"
(User does not mention the number)
```
./pkb.py --benchmarks=intel_hammerdb  --benchmark_config_file=hammerdb_static_ubuntu.yml --intel_hammerdb_db_type=mysql --os_type=ubuntu2004 --https_proxy='http://proxy-chain.intel.com:912' --intel_hammerdb_tpcc_mysql_hugepages='on'
```

#### Innodb Buffer Pool Size

Setting the Innodb buffer pool size
If the user wants to set the paramter, please make enter the value in **Bytes**

The hugepages settings and memory settings will need to be calculated based on this.

```
--intel_hammerdb_tpcc_mysql_innodb_buffer_pool_size
```

## Downloading Custom Packages for Intel HammerDB

If the user wishes to run a different version of HammerDB/MySQL/Postgres from what has been mentioned, he can do so with the help of the flags provided.

#### 1) HammerDB
  --intel_hammerdb_version: Custom HammerDB Version
  --intel_hammerdb_package_url: Hammerdb package source

If you are going to use a custom package, please make sure you fill in the right version in intel_hammerdb_version  flag above
as this will be captured in the metadata

#### 2) MySQL

If you are going to use a custom package, please make sure you fill in the right version in intel_hammerdb_mysql_version flag
as this will be captured in the metadata

 --intel_hammerdb_mysql_url: Custom Ubuntu MySQL Tar
 --intel_hammerdb_mysql_version: Custom MySQL Version

These are centos libs needed by HammerDB

 --intel_hammerdb_mysql_centos_community_common_url: MySQL community common to support HammerDB
 --intel_hammerdb_mysql_centos_lib_url: Custom MySQL community libs to support HammerDB

These are debian libs needed by HammerDB

  --intel_hammerdb_mysql_deb_lib_url: Ubuntu 1804 MySQL Debian Libs for HammerDB3.2


This is the flag to use if you want to mention an unique password for MySQL
  --intel_hammerdb_mysql_password: MySQL Password


#### 3) Postgres

If you are going to use a custom package, please make sure you fill in the right version in intel_hammerdb_postgres_version flag
as this will be captured in the metadata

  --intel_hammerdb_postgres_url: Custom Postgres Tar
  --intel_hammerdb_postgres_version: Custom Postgres Version


There are two ways in which the user can achieve this :-

1) Download the package from the source manually onto the PKB host. Place it in default_paths of PKB.

./pkb.py --benchmarks=intel_hammerdb --cloud=AWS  --intel_hammerdb_db_type='mysql'  --os_type=centos7  --preprovision_ignore_checksum=True

2) Provide the URL of the source of the package

```
./pkb.py --benchmarks=intel_hammerdb --cloud=AWS  --intel_hammerdb_db_type='mysql'  --os_type=centos7 --intel_hammerdb_package_url="https://sourceforge.net/projects/hammerdb/files/HammerDB/HammerDB-3.2/HammerDB-3.2-Linux.tar.gz" --preprovision_ignore_checksum=True
```

Please note that in both the cases it is the responsibilty of the user to verify the checksum for these packages.
PKB does the checksum verification for the packages which are available by default.
This is why you have to provide the flag --preprovision_ignore_checksum=True if you want to use a custom package.

## Flags for Intel HammerDB

For more details for Postgres configuration options, please refer to 
https://www.postgresql.org/docs/11/runtime-config.html](https://www.postgresql.org/docs/11/runtime-config.html) 

For more details on MySQL configuration  options, please refer to 
https://dev.mysql.com/doc/refman/8.0/en/innodb-parameters.html](https://dev.mysql.com/doc/refman/8.0/en/innodb-parameters.html)

```
Please note that for these two flags, the user must input them in bytes.

If you want to mention 100M please convert it to bytes and enter 102400.
--intel_hammerdb_tpcc_postgres_shared_buffers
--intel_hammerdb_tpcc_mysql_innodb_buffer_pool_size
```

```
perfkitbenchmarker.linux_benchmarks.intel_hammerdb_benchmark:
  --intel_hammerdb_benchmark_type: benchmark type
    (default: 'TPC-C')
  --intel_hammerdb_db_type: db type is pg or mysql
    (default: 'pg')
  --[no]intel_hammerdb_enable_timeprofile: time profile logs
    (default: 'false')
  --intel_hammerdb_enable_timestamps: Write timestamps to log file
    (default: '1')
    (an integer)
  --intel_hammerdb_platform: Mention if its an ARM platform or None for others
    (default: 'None')
  --intel_hammerdb_port: port at which the db is up and listening
    (default: '5432')
    (an integer)
  --[no]intel_hammerdb_run_single_node: Run Server & Client on samemachine or different machines
    (default: 'true')
  --intel_hammerdb_tpcc_hammer_num_virtual_users: num of virtual users for running hammerdb
    (default: '16')
  --intel_hammerdb_tpcc_mysql_hugepages: hugepage settings can be on or off
    (default: 'off')
  --intel_hammerdb_tpcc_mysql_innodb_adaptive_flushing: Specifies whether to dynamically adjust the rate of flushing
    dirty pages in the buffer pool  to avoid bursts of I/O activity.
    (default: '1')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_adaptive_hash_index: Enable/Disable  adaptive hash indexing to improve query
    performance
    (default: '0')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_buffer_pool_instances: Instances of buffer pool
    (default: '16')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_buffer_pool_size: buffer pool size
    (default: '6400M')
  --intel_hammerdb_tpcc_mysql_innodb_buffers_ratio: Amount of memory to be used for mysql
    (default: '0.75')
    (a number)
  --intel_hammerdb_tpcc_mysql_innodb_change_buffering: Whether InnoDB  performs change buffering, an optimization that
    delays write operations  to secondary indexes so that the I/O operations can be performed sequentially
    (default: 'none')
  --intel_hammerdb_tpcc_mysql_innodb_checksum_algorithm: Specifies how  to generate and verify the checksum stored in the
    disk blocks of InnoDB tablespaces.
    (default: 'none')
  --intel_hammerdb_tpcc_mysql_innodb_doublewrite: Stores data twice to the buffer and to actual data files
    (default: '0')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_flush_log_at_trx_commit: Determines how logs are written and flush to disk
    (default: '0')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_flush_method: Defines the method used to flush data to InnoDB data files and log
    files, which can affect I/O throughput.
    (default: 'O_DIRECT_NO_FSYNC')
  --intel_hammerdb_tpcc_mysql_innodb_flush_neighbors:  Specifies whether  flushing a page from the InnoDB buffer pool
    also flushes other dirty  pages in the same extent
    (default: '0')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_io_capacity: number of I/O operations per second (IOPS) available to InnoDB
    background tasks. Min Val 100,  Max Val (2^64)-1
    (default: '4000')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_io_capacity_max: A maximum number  of IOPS performed by InnoDB background task
    (default: '20000')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_log_buffer_size: size of log buffer
    (default: '64M')
  --intel_hammerdb_tpcc_mysql_innodb_lru_scan_depth:  It specifies, per  buffer pool instance, how far down the buffer
    pool LRU page list the page  cleaner thread scans looking for dirty pages to flush.
    (default: '9000')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_max_dirty_pages_pct: Limit for % of dirty pages which is maintained by Innodb by
    flushing data from the buffer pool
    (default: '90')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_max_dirty_pages_pct_lwm: Defines a low water mark representing the percentage of
    dirty pages at which preflushingis enabled to control the dirty page ratio
    (default: '10')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_max_purge_lag: If this value is exceeded, a delay is imposed on INSERT, UPDATE, and
    DELETE operations to allow time for purge to catch up
    (default: '0')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_max_purge_lag_delay: Specifies the  maximum delay in microseconds for the delay
    imposed when the  innodb_max_purge_lag threshold is exceeded
    (default: '300000')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_page_cleaners: The number of page cleaner threads that flush dirty pages from buffer
    pool instances. Min Val 1,  Max Val 64
    (default: '4')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_purge_threads: The number of background  threads devoted to the InnoDB purge
    operation. Min Val 1, Max Val 32
    (default: '4')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_read_io_threads: The number of I/O  threads for read operations in InnoDB. Min Val
    1, Max Val 64
    (default: '16')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_read_only: Starts Innodb in read-only  mode
    (default: '0')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_spin_wait_delay: The maximum delay between polls for a spin lock. Min Val 0, Max Val
    (2^32)-1
    (default: '6')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_stats_persistent: Specifies if InnoDB index statistics are persisted to disk
    (default: '1')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_thread_concurrency: Limit for OS threads running concurrently inside InnoDB
    (default: '0')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_undo_log_truncate: When enabled, undo tablespaces that exceed the threshold value
    defined by  innodb_max_undo_log_size are marked for truncation.
    (default: 'off')
  --intel_hammerdb_tpcc_mysql_innodb_use_native_aio: Indicates if Linux asynchronous I/O subsytem should be used. On by
    default
    (default: '1')
    (an integer)
  --intel_hammerdb_tpcc_mysql_innodb_write_io_threads: The number of I/O  threads for write operations in InnoDB. Min Val
    1, Max Val 64
    (default: '16')
    (an integer)
  --intel_hammerdb_tpcc_mysql_join_buffer_size: The minimum size of the  buffer that is used for plain index scans, range
    index scans, and joins  that do not use indexes and thus perform full table scans.
    (default: '32K')
  --intel_hammerdb_tpcc_mysql_num_hugepages: Number of huge pages for mysql
    (default: '100')
    (an integer)
  --intel_hammerdb_tpcc_mysql_num_warehouse: num of warehouses
    (default: '256')
    (an integer)
  --intel_hammerdb_tpcc_mysql_sort_buffer_size: Each session that must  perform a sort allocates a buffer of this size
    (default: '32K')
  --intel_hammerdb_tpcc_postgres_allwarehouse: use all warehouses or not
    (default: 'false')
  --intel_hammerdb_tpcc_postgres_autovacuum_work_mem: min 1MB, or -1 to use maintenance_work_mem
    (default: '-1')
  --intel_hammerdb_tpcc_postgres_dynamic_shared_memory_type: posix,sysv,windows,mmap or none to disable it
    (default: 'posix')
  --intel_hammerdb_tpcc_postgres_hugepages: hugepage settings can be on, off, or try
    (default: 'off')
  --intel_hammerdb_tpcc_postgres_io_concur: 1-1000; 0 disables prefetching
    (default: '32')
    (an integer)
  --intel_hammerdb_tpcc_postgres_log_timezone: timezone for the logs
    (default: 'UTC')
  --intel_hammerdb_tpcc_postgres_maintenance_work_mem: Maximum amount of memory to be used by maintenance operations,min
    1MB
    (default: '512MB')
  --intel_hammerdb_tpcc_postgres_max_connections: number of max connections
    (default: '256')
    (an integer)
  --intel_hammerdb_tpcc_postgres_max_files_per_process: maximum number of simultaneously open files allowed to each
    server subprocess min 25
    (default: '4000')
    (an integer)
  --intel_hammerdb_tpcc_postgres_max_locks_per_transaction: Controls the numberof shared locks allocated for each
    transaction, min 10
    (default: '64')
    (an integer)
  --intel_hammerdb_tpcc_postgres_max_pred_locks_per_transaction: Controls the number of shared predicate locks allocated
    for each transaction, min 10
    (default: '64')
    (an integer)
  --intel_hammerdb_tpcc_postgres_max_stack_depth: maximum safe depth of theserver execution stack, min 100kB
    (default: '7MB')
  --intel_hammerdb_tpcc_postgres_max_wal_senders: maximum number of concurrentconnections from standby servers
    (default: '0')
    (an integer)
  --intel_hammerdb_tpcc_postgres_max_wal_size: Maximum size to let the WALgrow to between automatic WAL checkpoints
    (default: '524288')
    (an integer)
  --intel_hammerdb_tpcc_postgres_max_worker_process: max # of worker processes
    (default: '72')
    (an integer)
  --intel_hammerdb_tpcc_postgres_memlock_ratio: Amount of memory to lock for pkb user
    (default: '0.8')
    (a number)
  --intel_hammerdb_tpcc_postgres_min_wal_size: If WAL disk usage stays below this setting, old WAL files are always
    recycled for future use at a checkpoint
    (default: '262144')
    (an integer)
  --intel_hammerdb_tpcc_postgres_num_hugepages: Number of huge pages for postgres
    (default: '100')
    (an integer)
  --intel_hammerdb_tpcc_postgres_num_warehouse: num of warehouses
    (default: '256')
    (an integer)
  --intel_hammerdb_tpcc_postgres_shared_buffers: Default size for memory
    (default: '6400MB')
  --intel_hammerdb_tpcc_postgres_shared_buffers_ratio: Amount of memory to be used for shared buffers for postgres
    (default: '0.75')
    (a number)
  --intel_hammerdb_tpcc_postgres_syn_commit: synchronization level, can be  off, local, remote_write, remote_apply, or on
    (default: 'off')
  --intel_hammerdb_tpcc_postgres_temp_buffers: Sets the maximum number oftemporary buffers used by each database
    session,min 800kB
    (default: '4096MB')
  --intel_hammerdb_tpcc_postgres_timezone: timezone
    (default: 'UTC')
  --intel_hammerdb_tpcc_postgres_wal_buffers: mount of shared memory usedfor WAL data that has not yet been written to
    disk,min 32kB, -1 sets based on shared_buffers
    (default: '-1')
  --intel_hammerdb_tpcc_postgres_wal_level: can be minimal, replica, or logical
    (default: 'minimal')
  --intel_hammerdb_tpcc_postgres_work_mem: Memory to be used by internalsort operations and hash tables before writing to
    temporary disk files,min 64kB
    (default: '4096MB')
  --intel_hammerdb_tpcc_rampup: ramp up time of the workload
    (default: '2')
    (an integer)
  --intel_hammerdb_tpcc_runtime: run time of the workload
    (default: '5')
    (an integer)
  --intel_hammerdb_tpcc_threads_build_schema: num of threads used for building dataset
    (default: '16')
    (an integer)

perfkitbenchmarker.linux_packages.intel_hammerdb:
  --intel_hammerdb_arm_compile_flags: Compile Flags For ARM
    (default: '--march=armv8.2-a+crc -O2')
  --intel_hammerdb_mysql_centos_community_common_url: MySQL community common to support HammerDB
    (default: 'None')
  --intel_hammerdb_mysql_centos_lib_url: Custom MySQL community libs to support HammerDB
    (default: 'None')
  --intel_hammerdb_mysql_deb_lib_url: Ubuntu 1804 MySQL Debian Libs for HammerDB3.2
    (default: 'None')
  --intel_hammerdb_mysql_password: MySQL Password
    (default: 'Mysql@123')
  --intel_hammerdb_mysql_url: Custom Ubuntu MySQL Tar
    (default: 'None')
  --intel_hammerdb_mysql_version: Custom MySQL Version
    (default: 'None')
  --intel_hammerdb_package_url: Hammerdb package source
    (default: 'None')
  --intel_hammerdb_postgres_url: Custom Postgres Tar
    (default: 'None')
  --intel_hammerdb_postgres_version: Custom Postgres Version
    (default: 'None')
  --intel_hammerdb_version: <3.2|4.0>: Custom HammerDB Version
    (default: '4.0')

```
