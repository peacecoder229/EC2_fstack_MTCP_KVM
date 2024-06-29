## Intel Redis benchmark guidelines

#### Foreword

This workload searches for the optimal throughput of redis databases. It increases load 
gradually to exploit all redis instances until maximum throughput is reached for a latency
less than 1ms. It is scalable, it can run multiple redis instances in one server and 
the memtier load can be distributed among many client machines.


## How to run intel_redis on the cloud machines with PKB
After PKB is [cloned](https://gitlab.devtools.intel.com/PerfKitBenchmarker/perfkitbenchmarker) the user will be able to run intel_redis as following:

```
python pkb.py --cloud=AWS --benchmarks=intel_redis --machine_type=m5.xlarge

```
Additionally some useful flags had been implemented to be used for PKB commandline launch, which are specific to redis workload: \
`--intel_redis_numprocesses=<default_value_is_1>`
- Number of Redis processes to spawn per processor.

`--intel_redis_clients=<default_value_is_5>`
- Number of redis loadgen clients.

`--intel_redis_setgetratio=<default_value_is_1:0>`
- Ratio of writes to reads performed by the memtier benchmark, default is 1:0, ie: writes only.

`--intel_redis_datasize=<default_value_is_32>`
- Object data size in Bytes.

`--intel_redis_client_threads_min=<default_value_is_1>`
- Starting thread count of the client process.

`--intel_redis_target_latency_percentile=<default_value_is_50.0>`
- The percentile used to compare against the provided limit.

`--intel_redis_latency_limit=<default_value_is_0.0>`
- Latency threshold in milli-seconds. Stop when threshold met. When zero, the threshold is set to 20 times the latency measured with one thread.

`--intel_redis_pipelined_requests=<default_value_is_1>`
- Number of concurrent pipelined requests.

`--intel_redis_cpu_collect=<default_value_is_False>`
- Collect cpu utilization for each redis process during steady state.

`--intel_redis_version=<default_value_is_5.0.5>`
- Version of redis server to use.

## How to run intel_redis on on-premise machines with PKB
PKB allows passing a configuration file (.yml), in order to be able to run the workload on bare metal. VMs need to be specified as workers hosting redis or clients running memtier. The command will be as following:

```
python pkb.py --benchmark_config_file=perfkitbenchmarker/data/intel_redis_config.yml --benchmarks=intel_redis
```

Example for intel_redis_config.yml:

```
static_vms:
  - &vm0
    ip_address: <ip_address>
    user_name: pkb
    ssh_private_key: ~/.ssh/id_rsa
    internal_ip: <ip_address>
    disk_specs:
      - mount_point: /home/pkb

  - &vm1
    ip_address: <ip_address>
    user_name: pkb
    ssh_private_key: ~/.ssh/id_rsa
    internal_ip: <ip_address>
    disk_specs:
      - mount_point: /home/pkb

  - &vm2
    ip_address: <ip_address>
    user_name: pkb
    ssh_private_key: ~/.ssh/id_rsa
    internal_ip: <ip_address>
    disk_specs:
      - mount_point: /home/pkb

intel_redis: {
    name: intel_redis,
    vm_groups: {
        workers: {static_vms: [*vm0],vm_count: 1
        },
        clients: {static_vms: [*vm1, *vm2]
        }
    }
}
```
**Note**
In the configuration file the `<ip_address>` must be manually replaced with the
IP address of the machine on which the workload or client is to run.

The `<user_name>` must be configured to have passwordless `sudo` privileges.

**Onboarding of a target system**

The following steps will create such a user account. They vary slightly among
Linux distributions. In particular, on Debian-based distributions such as 

0. Log into the destination machine and create a new user account:

    ```sh
    destination$ sudo useradd -m <user_name>
    ```

0. Add the new user to the group of accounts which may use `sudo`:

    ```sh
    destination$ sudo groupadd -aG sudo <user_name>
    ```

    On CentOS the name of the group is `wheel`, not `sudo`.

0. Configure `sudo` to not ask for a password for `<user_name>`

    ```sh
    destination$ sudo echo '<user_name> ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers
    ```

0. Paste the public key corresponding to the private key that `pkb` will use for
    logging into the destination machine (usually `~/.ssh/id_rsa.pub`) at the end
    of `/home/<user_name>/.ssh/authorized_keys` on the destination machine.
    Create `/home/<user_name>.ssh/authorized_keys` with the contents of the file
    if it is not already present.

0. Ensure that `/home/<user_name>/.ssh` has the correct privileges:

    ```sh
    destination$ sudo chown <user_name>:<user_name> /home/<user_name>/.ssh
    destination$ sudo chmod 700 /home/<user_name>/.ssh
    ```

0. Log into the destination machine using the newly created user account:

    ```sh
    source$ ssh <user_name>@<ip_address>
    destination$
    ```

    No password should be required.

## How to benchmark with PMEM

Persistent Memory (PMEM) is currently supported by Redis only in a fork
of Redis (https://github.com/pmem/redis) with binaries published as
container for usage on Kubernetes
(https://hub.docker.com/r/pmem/redis,
https://github.com/intel/pmem-csi/blob/0bf82413ca2aba0ada3db0524cbdd5df47303d79/examples/redis-operator.md).

In that fork, data that is to be cached is placed in PMEM while more
performance critical parts like data management structures are kept in
DRAM. The advantages are:
- a node can cache more data because PMEM NVDIMMs have higher capacity than DRAM DIMMs
- the same amount of data can be cached at less costs because PMEM NVDIMMs are cheaper
  than DRAM DIMMs of the same size

The downside is a certain decrease in performance because PMEM is
slower than DRAM. That difference can be measured with this benchmark
by comparing a hardware configuration with and without PMEM.

The benchmark must be changed to use the different Redis source code with
`--intel_redis_url=https://github.com/pmem/redis/archive/5.0-poc_cow.tar.gz`.

Using PMEM is enabled with `--intel_redis_pmem_size=<size>`,
otherwise the Redis server runs in the normal mode with DRAM. `<size>`
can be specified with `m` or `g` as suffix, e.g. `1g`, and set the
upper limit for PMEM used by each redis-server process. It is okay
to use `0g` to enabled PMEM usage without such a limit.

PMEM is allocated by creating a file the VMs scratch volume and
mapping that file into memory. Therefore the scratch volume must be on
a dax-capable filesystem. On a static VM, that has to be set up
manually and the location must be specified:
```
static_vms:
 - &mymachine
    ip_address: ...
    ssh_port: 22
    internal_ip: ...
    user_name: ...
    os_type: ...
    disk_specs:
      - mount_point: /mnt/pmem/

intel_redis:
  vm_groups:
    workers:
      static_vms:
        - *mymachine
```

On Kubernetes, [PMEM-CSI](https://github.com/intel/pmem-csi/) can be
used with the following user configuration:
```
pmem_disk: &worker_disk
  Kubernetes:
    disk_type: persistentVolumeClaim
    provisioner: pmem-csi.intel.com
    mount_point: /scratch
    disk_size: 200

intel_redis:
  vm_groups:
    workers:
      disk_spec: *pmem_disk
  flags:
    enable_transparent_hugepages:
```

The benchmark automatically scales the data set size based on the
amount of DRAM that the machine has. Therefore the PMEM volume must be
at least as large as main memory.

Note that the PMEM file gets deleted while still in use. To verify
that the `redis-server` uses PMEM, use `lsof`:

``` sh
root@pkb-dea0dfc9-5:~# apt-get install lsof
...
root@pkb-dea0dfc9-5:~# ps -ef | grep redis-server | grep -v grep | tail -1
root     15860     1 42 10:13 ?        00:03:13 /opt/pkb/redis-5.0.5/src/redis-server *:6458
root@pkb-dea0dfc9-5:~# lsof -p 15860 | grep /scratch
redis-ser 15860 root    5u      REG    253,6        0   8257538 /scratch/redis-pmem-6458/memkind.NNPAeZ (deleted)
root@pkb-dea0dfc9-5:~# grep fd:05 /proc/15860/maps
# grep fd:05 /proc/15860/maps
7ff38ad00000-7ff39ad00000 rw-s 57f00000 fd:05 8257538                    /scratch/redis-pmem-6458/memkind.NNPAeZ (deleted)
7ff3a3f00000-7ff3b1f00000 rw-s 49f00000 fd:05 8257538                    /scratch/redis-pmem-6458/memkind.NNPAeZ (deleted)
7ff3b5900000-7ff3c1900000 rw-s 3df00000 fd:05 8257538                    /scratch/redis-pmem-6458/memkind.NNPAeZ (deleted)
...
```

https://github.com/pmem/redis/blob/5.0-poc_cow/src/sds.c#L226 causes
pmem-redis to only store strings in PMEM which are at least 256
bytes long. This is the default for `--intel_redis_datasize`, beware when
making it smaller!

## Host OS configuration

The benchmark by default configures the host such that it uses optimal
settings for Redis (like not using transparent huge pages). This does
not work when using Kubernetes because a container only has read
access to the relevant system
files. `--intel_redis_configure_os=false` disables this aspect of the
benchmark. To get comparable results on the same host with and without
Kubernetes, that flag should be used also when running with bare
metal.

Beware that the benchmark currently doesn't restore the original host
configuration. This means a bare metal host will continue to use the
Redis configuration also for other benchmarks and must be reset
manually.

## Files in this workload

The following files form this workload, relative to the root of the
`perfkitbenchmarker` `git` repository:

0.  `perfkitbenchmarker/linux_benchmarks/intel_redis_benchmark.py` contains 
    the algorithm's implementation that finds the optimal memtier load for 
    which redis throughput is maximum for a latency less than 1ms. The optimal 
    load is distributed between the clients processes and its threads determined 
    at run-time.

0.  `perfkitbenchmarker/linux_packages/intel_redis_server.py` contains the 
    functions to install redis, requirements and configuration.

0.  `perfkitbenchmarker/linux_packages/memtier.py` contains the 
    functions for memtier installation and requirements.

## Notes about cpu usage

The redis cpu is fully utilized for machines having up to 8 vcpus. For 16 vcpus machines,
cpu couldn't be stressed more than 80% due to socket connections bottlenecks that increase
redis latency. For 96 vcpus machines, the cpu usage decreases dramatically to 30%.
