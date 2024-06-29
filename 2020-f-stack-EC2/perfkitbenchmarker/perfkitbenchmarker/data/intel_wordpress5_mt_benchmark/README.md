
## Intel WordPress 5.2 Multi-Instance benchmark guidelines

#### Foreword

oss-performance/WordPress workload as we call it is a collection of scripts and wrappers that allows the user to prepare the workload, run the workload (default or customized using a config file), and collect reports using the opensource benchmark developed by Facebook.
To clarify, the components are as following:
- [oss-performance](https://github.com/hhvm/oss-performance): this is the public workload developed by Facebook. It's actually a harness that is able to run a series of PHP-based workloads (their terminology is 'targets'): WordPress, MediaWiki, Drupal, and others. You can use this to assess the performance of a PHP engine (either PHP Zend or Facebook's HHVM);
- [hhvm-perf](https://github.intel.com/DSLO/hhvm-perf): this is DSLO/HHVM team internal harness that has been developed by Octavian M. and It's basically a wrapper over oss-performance. It is able to run the targets multiple times, compute the average/standard deviation of various metrics like transactions/second, collect emon, and perf data, collect logs and workload artifacts etc. It's mostly adding a friendlier interface to HHVM team existing internal tooling.
The expectations here are to integrate these components into PKB and be able to prepare the a target system, run the workload and collect performance, telemetry and artifacts in a standardized and replicable way. While the intel_wordpress_benchmark runs the workload on a single system, the goal of this workload is to be able the run oss-performance WordPress on three different systems separating the client, server and database components.

## How to run oss-performance/WordPress (WP) with PKB
After PKB is [installed and configured](https://github.intel.com/cspbench/PerfKitBenchmarker#installing-perfkit-benchmarker-and-prerequisites) the user will be able to run WP as following:

```
python pkb.py --cloud=AWS --benchmarks=intel_wordpress5_mt --machine_type=m5.24xlarge
```
additionally some useful flags had been implemented to be used for PKB commandline launch, which are specific to WP workload: \
`--intel_wordpress5_mt_execution_count=<default_value_is_1>`
- if specified, this flag is used to tell the harness how many times to run oss-performance for current a PKB run if is not specified it will use the default value which is 1.

`--intel_wordpress5_mt_server_threads=<default_value_is_dynamic>`
- if specified, this flag will overwrite the default server thread value which is computed based on the number of vCPUs available.

`--intel_wordpress5_mt_client_threads=<default_value_is_200>`
- if specified, this flag will overwrite the default Siege client thread value which is 200 for the current PKB run.

`--intel_wordpress_https_enabled=<default_value_is_False>`
- If True, WordPress will run using HTTPS. The default is False, defaulting to HTTP

`--intel_wordpress_https_tls_version=<default_value_is_TLSv1.3>`
- TLS version to be used by the workload with HTTPS mode. Default is TLSv1.3

`--intel_wordpress_https_cipher=<default_value_is_None>`
- Cipher to be used by the workload with HTTPS mode. Only ciphers in TLSv1.2 can be specified.


## Run WP with PKB on bare-metal
PKB allows passing a configuration file (.yml), in order to be able to run the workload on bare metal an VM needs to be specified as a target. The command will be as following:

```
python pkb.py --benchmark_config_file=wp_config.yml --benchmarks=intel_wordpress5_mt --machine_type=m5.24xlarge
```

Example for wp_config.yml:

```
static_vms:
  - &vm0
    ip_address: <ip_address>
    user_name: pkb
    ssh_private_key: ~/.ssh/id_rsa
    internal_ip: <ip_address>
  - &vm1
    ip_address: <ip_address>
    user_name: pkb
    ssh_private_key: ~/.ssh/id_rsa
    internal_ip: <ip_address>
  - &vm2
    ip_address: <ip_address>
    user_name: pkb
    ssh_private_key: ~/.ssh/id_rsa
    internal_ip: <ip_address>

intel_wordpress5_mt:
  vm_groups:
    server:
      static_vms:
        - *vm0
      vm_count: 1
    client:
      static_vms:
        - *vm1
      vm_count: 1
    database:
      static_vms:
        - *vm2
      vm_count: 1

```
**Note**
Make sure you are using a different user from root.
It is assumed that pkb user already exists on the target machine, if not here are some guidelines to create the user:

**Onboarding of a target system**
SSH to the target system and create a passwordless user:

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

## Integration notes

As a first step a list with generic operations and the order of execution is needed from the workload owner, just listed as if executed by hand, considering that this setup is done on a freshly installed platform.

PKB has predefined "steps" to do the job, a very simplified schema looks like this [from intel_wordpress_benchmark.py](https://github.intel.com/cspbench/PerfKitBenchmarker/blob/master/perfkitbenchmarker/linux_benchmarks/intel_wordpress_benchmark.py):
```
...
#Workload metadata definition section
flags.DEFINE_integer('intel_wordpress5_mt_execution_count', 1,
                    'The number of times to run against chosen target.')
flags.DEFINE_integer('intel_wordpress5_mt_server_threads', None,
                    'The number of threads to execute.')
flags.DEFINE_integer('intel_wordpress5_mt_client_threads', None,
                     'The number of client threads to use to drive load.')
...

#Define workload name and execution orchestration
...

BENCHMARK_NAME = 'intel_wordpress5_mt'
BENCHMARK_CONFIG = """
intel_wordpress5_mt:
  description: >
      Run HHVM's oss-performance harness to drive Siege against
      Nginx, PHP or HHVM, WordPress using MariaDB on the back end 
      separating out the server, database and client on different systems
  vm_groups:
    server:
      os_type: ubuntu1604
      vm_spec: *default_dual_core
      vm_count: 1
    client:
      os_type: ubuntu1604
      vm_spec: *default_dual_core
      vm_count: 1
    database:
      os_type: ubuntu1604
      vm_spec: *default_dual_core
      vm_count: 1
"""
