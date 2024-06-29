
# [Node-DC-EIS][] Workload

## Foreword

Part of the Node.js Datacenter series of workloads, this workload simulates the
behavior of an employee information system. It populates a [MongoDB][] database,
and uses a Node.js server, the performance of which is recorded, to access the
database in response to incoming client requests. The client, written in Python,
is also provided.

## How to run Node-DC-EIS with PKB

`pkb` uses two different command lines, depending on whether its destination is
a cloud environment or a specific (set of) machine(s).

### In a cloud environment such as AWS:
After PKB is [installed and configured][] the user will be able to run WP as
follows:

```
python pkb.py --cloud=AWS --benchmarks=node_dc_eis --machine_type=m5.24xlarge
```

### On a specific machine (virtual, containerized, or bare metal):
PKB accepts a YAML configuration file containing the details, such as IP
address and user name of the target(s) on which it is to run the workload:

```
python pkb.py \
  --benchmark_config_file=config.yml \
  --benchmarks=node_dc_eis
```

An example configuration file might look like this:

```
static_vms:
  - &vm0
    ip_address: <ip_address>
    user_name: <user_name>
    ssh_private_key: ~/.ssh/id_rsa
    internal_ip: <ip_address>

node_dc_eis:
  vm_groups:
    target:
      static_vms:
        - *vm0
```

In the configuration file the `<ip_address>` must be manually replaced with the
IP address of the machine on which the workload is to run.

The `<user_name>` must be configured to have passwordless `sudo` privileges.

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

## Files in this workload

The following files form this workload, relative to the root of the
`perfkitbenchmarker` `git` repository:

0.  `perfkitbenchmarker/linux_benchmarks/node_dc_eis_benchmark.py` contains the
    definition of the benchmark.

0.  The directory `perfkitbenchmarker/data/node_dc_eis_benchmark/` contains
    files used by the functions defined in the benchmark definition.

[Node-DC-EIS]: https://github.com/Node-DC/Node-DC-EIS
[MongoDB]: https://mongodb.org/
[installed and configured]: https://gitlab.intel.com/PerfKitBenchmarker/perfkitbenchmarker/#installing-perfkit-benchmarker-and-prerequisites

## Packages difference between Debian, Rhel and Clear Linux

0. Clear linux is not supporting mongodb as a bundle. Mongodb binary is downloaded from http://downloads.mongodb.org/linux/mongodb-linux-x86_64-4.1.6.tgz
Ubuntu and Clear linux have support for mongodb in their package manager.

0. For Clear linux, Nodejs is installed as the bundle 'nodejs-basic'. 
   For Ubuntu and Centos, nvm is used for Nodejs installation.  
