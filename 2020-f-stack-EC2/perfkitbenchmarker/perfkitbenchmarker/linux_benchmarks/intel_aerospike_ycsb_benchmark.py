# Copyright 2015 PerfKitBenchmarker Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Runs YCSB against Aerospike.

This benchmark runs two workloads against Aerospike using YCSB (the Yahoo! Cloud
Serving Benchmark).
Aerospike is described in perfkitbenchmarker.linux_packages.aerospike_server
YCSB and workloads described in perfkitbenchmarker.linux_packages.ycsb.
"""

import time
import logging
import functools
import math
import posixpath
from perfkitbenchmarker import errors
from itertools import repeat
from perfkitbenchmarker import configs
from perfkitbenchmarker import disk
from absl import flags
from perfkitbenchmarker import vm_util
from perfkitbenchmarker.linux_packages import aerospike_server
from perfkitbenchmarker.linux_packages import ycsb


flags.DEFINE_integer('intel_aerospike_ycsb_processes', 1,
                     'Number of total ycsb processes across all clients.')

FLAGS = flags.FLAGS


BENCHMARK_NAME = 'intel_aerospike_ycsb'
BENCHMARK_CONFIG = """
intel_aerospike_ycsb:
  description: >
    Run YCSB against an Aerospike
    installation. Specify the number of YCSB VMs with
    --ycsb_client_vms.
  vm_groups:
    workers:
      vm_spec: *default_single_core
      disk_spec: *default_500_gb
      vm_count: null
      disk_count: 0
    clients:
      vm_spec: *default_single_core
  flags:
    ycsb_client_vms: 2
"""
samples = []


def GetConfig(user_config):
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)

  if FLAGS.aerospike_storage_type == aerospike_server.DISK:
    if FLAGS.data_disk_type == disk.LOCAL:
      # Didn't know max number of local disks, decide later.
      config['vm_groups']['workers']['disk_count'] = (
          config['vm_groups']['workers']['disk_count'] or None)
    else:
      config['vm_groups']['workers']['disk_count'] = (
          config['vm_groups']['workers']['disk_count'] or 1)

  if FLAGS['ycsb_client_vms'].present:
    config['vm_groups']['clients']['vm_count'] = FLAGS.ycsb_client_vms

  return config


def CheckPrerequisites(benchmark_config):
  """Verifies that the required resources are present.

  Raises:
    perfkitbenchmarker.data.ResourceNotFound: On missing resource.
  """
  ycsb.CheckPrerequisites()


def Prepare(benchmark_spec):
  """Prepare the virtual machines to run YCSB against Aerospike.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  loaders = benchmark_spec.vm_groups['clients']
  assert loaders, benchmark_spec.vm_groups

  # Aerospike cluster
  aerospike_vms = benchmark_spec.vm_groups['workers']
  assert aerospike_vms, 'No aerospike VMs: {0}'.format(
      benchmark_spec.vm_groups)

  seed_ips = [vm.internal_ip for vm in aerospike_vms]
  aerospike_install_fns = [functools.partial(aerospike_server.ConfigureAndStart,
                                             vm, seed_node_ips=seed_ips)
                           for vm in aerospike_vms]
  ycsb_install_fns = [functools.partial(vm.Install, 'ycsb')
                      for vm in loaders]

  vm_util.RunThreaded(lambda f: f(), aerospike_install_fns + ycsb_install_fns)

  num_ycsb = FLAGS.intel_aerospike_ycsb_processes
  num_server = FLAGS.aerospike_total_num_processes
  if num_ycsb < num_server:
    raise errors.Config.InvalidValue("intel_aerospike_ycsb_processes less than aerospike_total_num_processes")

# Here they used the modulo function to make sure we don't get more YCSB clients than
# Aerospike instances. This is adapted from what was done in their multi-instance cases
# to accomodate the Aerospike port system

  namespace_var = 'test'
  the_clients = benchmark_spec.vm_groups['clients']
  number_of_servers = FLAGS.aerospike_total_num_processes
  the_aerospike_vms = benchmark_spec.vm_groups['workers']
  num_client = FLAGS.ycsb_client_vms

  global samples
  for i in range(number_of_servers):
    namespace_value = namespace_var + str(i)
    iterative_metadata = []
    dict = {}
    port = ((1000 * i) + 3000)
    dict["as.port"] = port
    dict["as.namespace"] = namespace_value
    for j in range(num_ycsb):
      iterative_metadata.append(dict)
    duplicate = int(math.ceil(num_ycsb / float(num_client)))
    client_vms = [vm for item in the_clients for vm in repeat(item, duplicate)][:number_of_servers]
    benchmark_spec.executor = ycsb.YCSBExecutor(
        'aerospike',
        **{'as.host': the_aerospike_vms[0].internal_ip,
           'perclientparam': iterative_metadata})
    samples += list(benchmark_spec.executor.Load(client_vms, load_kwargs={'threads': 4}))


# Modified this to pass multiple ports. Essentially a list of ports.
# When the executor detects this, it will launch each YCSB client after a specific port in the list
# for num_server = num_ycsb = 4, metatadata looks like this [{'as.port': 3000}, {'as.port': 4000}, {'as.port': 5000}, {'as.port': 6000}, {'as.port': 7000}]
# Subsequently this was modified to allow each instance to refer to its own name space. Now we have [{'as.port=3000 -p as.namespace':3000}]

def Run(benchmark_spec):
  """Spawn YCSB and gather the results.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.

  Returns:
    A list of sample.Sample instances.
  """
  loaders = benchmark_spec.vm_groups['clients']
  aerospike_vms = benchmark_spec.vm_groups['workers']
  global samples

  num_ycsb = FLAGS.intel_aerospike_ycsb_processes
  num_server = FLAGS.aerospike_total_num_processes
  num_client = FLAGS.ycsb_client_vms
  metadata = {'ycsb_client_vms': FLAGS.ycsb_client_vms,
              'num_vms': len(aerospike_vms),
              'Storage Type': FLAGS.aerospike_storage_type,
              'aerospike_total_num_processes': num_server}

  namespace_var = 'test'
  server_metadata = []
  for i in range(num_ycsb):
    namespace_value = namespace_var + str(i)
    dict = {}
    port = ((1000 * (i % num_server)) + 3000)
    dict["as.port"] = port
    dict["as.namespace"] = namespace_value
    server_metadata.append(dict)
  benchmark_spec.executor = ycsb.YCSBExecutor(
      'aerospike',
      **{'as.host': aerospike_vms[0].internal_ip,
         'perclientparam': server_metadata})

  # Matching client vms and ycsb processes sequentially:
  # 1st to xth ycsb clients are assigned to client vm 1
  # x+1th to 2xth ycsb clients are assigned to client vm 2, etc.
  # Duplicate VirtualMachine objects passed into YCSBExecutor to match
  # corresponding ycsb clients.
  duplicate = int(math.ceil(num_ycsb / float(num_client)))
  client_vms = [
      vm for item in loaders for vm in repeat(item, duplicate)][:num_ycsb]

  vm_util.StartSimulatedMaintenance()

  samples += list(benchmark_spec.executor.Run(client_vms))
  for sample in samples:
    sample.metadata.update(metadata)

  return samples


def Cleanup(benchmark_spec):
  """Cleanup.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  def StopAerospike(server):
    server.RemoteCommand('cd %s && nohup sudo make stop' %
                         aerospike_server.AEROSPIKE_DIR)
    server.RemoteCommand('sudo rm -rf aerospike*')

  aerospike_vms = benchmark_spec.vm_groups['workers']
  vm_util.RunThreaded(StopAerospike, aerospike_vms)
