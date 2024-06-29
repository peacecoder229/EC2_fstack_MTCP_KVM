# Copyright 2017 PerfKitBenchmarker Authors. All rights reserved.
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

"""Runs YCSB against different memcached-like offerings.

This benchmark runs two workloads against memcached using YCSB (the Yahoo! Cloud
Serving Benchmark).
memcached is described in perfkitbenchmarker.linux_packages.intel_memcached_server
YCSB and workloads described in perfkitbenchmarker.linux_packages.ycsb.
"""

import functools
import logging
import math
import copy
from itertools import repeat

from perfkitbenchmarker import configs
from absl import flags
from perfkitbenchmarker import providers
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import autoscale_util
from perfkitbenchmarker import sample
from perfkitbenchmarker.linux_packages import intel_memcached_server as memcached_server
from perfkitbenchmarker.linux_packages import ycsb

FLAGS = flags.FLAGS

flags.DEFINE_integer('intel_memcached_record_count', 0,
                     'The number of records inserted into memcached.'
                     ' Set to zero to allow benchmark to choose based on memory'
                     ' available.',
                     lower_bound=0)
flags.DEFINE_integer('intel_memcached_load_threads', 10,
                     'Number of threads used per YCSB instance in load phase.')
flags.DEFINE_integer('intel_memcached_target_rate', 50000,
                     'The target number of operations per second per YCSB process. '
                     'Set to zero to run as fast as possible.')
flags.DEFINE_float('intel_memcached_sla_p99latency', 1.0,
                   'p99 latency in ms')

BENCHMARK_NAME = 'intel_memcached'
BENCHMARK_CONFIG = """
intel_memcached:
  description: Run YCSB against a single instance of memcached.
  vm_groups:
    servers:
      vm_spec: *default_dual_core
      os_type: ubuntu2004
      vm_count: 1
    clients:
      vm_spec: *default_dual_core
      os_type: ubuntu2004
  flags:
    publish_after_run: true
    intel_memcached_max_client_connections: 4096
    intel_memcached_size_mb: 0                  # zero sets it to use 80 percent of available memory for cache
    intel_memcached_record_count: 0             # zero means workload calculate based on cache size
    intel_memcached_num_threads: 0              # zero sets it to the number of vCPUS of target
    ycsb_workload_files: 'workloadc'
    ycsb_threads_per_client: '10'
    ycsb_client_vms: 1                    # use this number of client vms/machines
    ycsb_measurement_type: hdrhistogram
    ycsb_operation_count: 100000000       # very large number, iteration run time limited by ycsb_timelimit
    ycsb_timelimit: 60                    # limit iteration to this number of seconds
    ycsb_field_count: 10
    ycsb_field_length: 100
"""

B_PER_KB = 1024
KB_PER_MB = 1024
MB_PER_GB = 1024
KB_PER_GB = KB_PER_MB * MB_PER_GB


def GetConfig(user_config):
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)

  if FLAGS['ycsb_client_vms'].present:
    config['vm_groups']['clients']['vm_count'] = FLAGS.ycsb_client_vms

  return config


def CheckPrerequisites(benchmark_config):
  """Verifies that the required resources are present.

  Raises:
    perfkitbenchmarker.data.ResourceNotFound: On missing resource.
  """
  ycsb.CheckPrerequisites()


def _GetRecordCount(vm):
  """ returns the number of records that will be inserted into
      memcached, scaled to available memory """
  if FLAGS.intel_memcached_record_count:
    return FLAGS.intel_memcached_record_count
  cache_size_b = memcached_server.GetConfiguredCacheSizeMb(vm) * B_PER_KB * KB_PER_MB
  logging.info("memcached cache size in bytes: {0}".format(cache_size_b))
  record_size_b = FLAGS.ycsb_field_count * FLAGS.ycsb_field_length
  # use 80% of cache
  num_records = int(round((cache_size_b / record_size_b) * .80))
  logging.info("using 80 percent of cache for {0} records".format(num_records))
  return num_records


def _GetClientVms(benchmark_spec, num_client_vms, num_ycsb_processes):
  ycsb_vms = benchmark_spec.vm_groups['clients']
  num_ycsb = num_ycsb_processes
  num_client = num_client_vms
  # Matching client vms and ycsb processes sequentially:
  # 1st to xth ycsb clients are assigned to client vm 1
  # x+1th to 2xth ycsb clients are assigned to client vm 2, etc.
  # Duplicate VirtualMachine objects passed into YCSBExecutor to match
  # corresponding ycsb clients.
  duplicate = int(math.ceil(num_ycsb / float(num_client)))
  client_vms = [
      vm for item in ycsb_vms for vm in repeat(item, duplicate)][:num_ycsb]
  return client_vms


def _PrepareServer(vm):
  # Install and start memcached on the server
  vm.Install('intel_memcached_server')
  memcached_server.Configure(vm)
  memcached_server.StartMemcached(vm)


def _PrepareClient(vm):
  # Install YCSB on client vm
  vm.Install('ycsb')


def Prepare(benchmark_spec):
  """Prepare the virtual machines to run YCSB against memcached.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  benchmark_spec.always_call_cleanup = True
  server = benchmark_spec.vm_groups['servers'][0]
  clients = benchmark_spec.vm_groups['clients']
  benchmark_spec.metadata = {'client_vms': len(clients),
                             'cache_size': FLAGS.memcached_size_mb}

  server_partials = [functools.partial(_PrepareServer, server)]
  client_partials = [functools.partial(_PrepareClient, client)
                     for client in clients]
  vm_util.RunThreaded((lambda f: f()), server_partials + client_partials)


def _LoadWorkload(benchmark_spec, num_ycsb_processes):
  server = benchmark_spec.vm_groups['servers'][0]
  clients = benchmark_spec.vm_groups['clients']

  # (re)create the ycsb executor
  server_ips = autoscale_util.GetInternalIpAddresses(server)
  server_metadata = [
      {'memcached.hosts': '{}:{}'.format(server_ips[i % len(server_ips)],
                                         memcached_server.MEMCACHED_PORT)}
      for i in range(num_ycsb_processes)]

  benchmark_spec.executor = ycsb.YCSBExecutor('memcached',
                                              **{'perclientparam': server_metadata})

  # Execute YCSB load
  ycsb_clients = _GetClientVms(benchmark_spec, len(clients), num_ycsb_processes)
  benchmark_spec.executor.Load(ycsb_clients,
                               load_kwargs={'threads': FLAGS.intel_memcached_load_threads})


def _RunWorkload(benchmark_spec, num_ycsb_processes):
  server = benchmark_spec.vm_groups['servers'][0]
  clients = benchmark_spec.vm_groups['clients']

  memcached_server.FlushMemcachedServer(server)
  _LoadWorkload(benchmark_spec, num_ycsb_processes)

  # Execute YCSB run
  if FLAGS.intel_memcached_target_rate:
    ycsb_target_rate_value = FLAGS.intel_memcached_target_rate * num_ycsb_processes
  else:
    ycsb_target_rate_value = None
  samples = list(benchmark_spec.executor.Run(_GetClientVms(benchmark_spec,
                                                           len(clients),
                                                           num_ycsb_processes),
                                             run_kwargs={'target': ycsb_target_rate_value}))
  return samples


def _MeetsExitCriteria(samples):
  throughputs = [s.value for s in samples if s.metric == 'overall Throughput']
  return autoscale_util.MeetsExitCriteria(throughputs)


def _GetMaxThroughput(iteration_data, metadata):
  """ returns a Sample object containing the maximum throughput found in samples """
  max_throughput = 0
  max_throughput_iteration = -1
  for iteration, data in enumerate(iteration_data):
    # throughput is the first item in the data tuple
    assert data[0].metric == 'overall Throughput'
    assert data[1].metric == 'read p99 latency'
    if data[2]:
      assert data[2].metric == 'update p99 latency'
    if data[0].value > max_throughput:
      max_throughput = data[0].value
      max_throughput_iteration = iteration
  assert max_throughput_iteration >= 0
  if max_throughput_iteration == len(iteration_data) - 1:
    logging.warn("Maximum throughput was found on the last iteration. "
                 "System may have more capacity.")
  sample_metadata = copy.deepcopy(metadata)
  sample_metadata['p99ReadLatency'] = iteration_data[max_throughput_iteration][1].value
  sample_metadata['iteration'] = max_throughput_iteration + 1
  if iteration_data[max_throughput_iteration][2]:
    sample_metadata['p99UpdateLatency'] = iteration_data[max_throughput_iteration][2].value
  else:
    sample_metadata['p99UpdateLatency'] = 'None'
  return sample.Sample('Maximum Throughput',
                       iteration_data[max_throughput_iteration][0].value,
                       iteration_data[max_throughput_iteration][0].unit,
                       metadata=sample_metadata)


def _GetMaxThroughputForLatencySLA(iteration_data, metadata):
  """ returns a Sample object containing the throughput achieved under maximum latency """
  max_throughput = 0
  max_throughput_iteration = -1
  for iteration, data in enumerate(iteration_data):
    # throughput is the first item in the data tuple
    # p99read is the 2nd item, p99update is 3rd
    assert data[0].metric == 'overall Throughput'
    assert data[1].metric == 'read p99 latency'
    if data[2]:
      assert data[2].metric == 'update p99 latency'
    if data[0].value > max_throughput and data[1].value <= FLAGS.intel_memcached_sla_p99latency:
      max_throughput = data[0].value
      max_throughput_iteration = iteration
  if max_throughput_iteration >= 0:
    sample_metadata = copy.deepcopy(metadata)
    sample_metadata['p99ReadLatency'] = iteration_data[max_throughput_iteration][1].value
    sample_metadata['iteration'] = max_throughput_iteration + 1
    if iteration_data[max_throughput_iteration][2]:
      sample_metadata['p99UpdateLatency'] = iteration_data[max_throughput_iteration][2].value
    else:
      sample_metadata['p99UpdateLatency'] = 'None'
    return sample.Sample('Maximum Throughput for Latency SLA',
                         iteration_data[max_throughput_iteration][0].value,
                         iteration_data[max_throughput_iteration][0].unit,
                         metadata=sample_metadata)
  else:
    return sample.Sample('Maximum Throughput for Latency SLA', 0, 'ops/s', metadata)


def _GetRelevantIterationData(samples):
  """ returns a tuple of three relevant samples """
  throughput_sample = None
  readp99_sample = None
  updatep99_sample = None
  for s in samples:
    if s.metric == 'overall Throughput':
      throughput_sample = s
    elif s.metric == 'read p99 latency':
      readp99_sample = s
    elif s.metric == 'update p99 latency':
      updatep99_sample = s
  return (throughput_sample, readp99_sample, updatep99_sample)


def Run(benchmark_spec):
  """Spawn YCSB and gather the results.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.

  Returns:
    A list of sample.Sample instances.
  """
  server = benchmark_spec.vm_groups['servers'][0]
  samples = []
  num_ycsb_processes = 1
  FLAGS.ycsb_record_count = _GetRecordCount(server)
  iteration_data = []  # array of tuple of three samples for each iteration (throughput, p99read, p99write)
  while True:
    logging.info("Measuring performance with {} YCSB processes.".format(num_ycsb_processes))
    instance_samples = _RunWorkload(benchmark_spec,
                                    num_ycsb_processes)
    iteration_data.append(_GetRelevantIterationData(instance_samples))
    logging.info('Throughput: {}\tp99 Read Latency: {}\tp99 Update Latency: {}'.format(iteration_data[-1][0].value,
                                                                                       iteration_data[-1][1].value,
                                                                                       iteration_data[-1][2].value if iteration_data[-1][2] else 'None'))
    samples.extend(instance_samples)
    if _MeetsExitCriteria(samples):
      logging.info("Exit criteria met.")
      break
    num_ycsb_processes += 1

  metadata = {'Memcached Version:': memcached_server.GetVersion(server)}
  samples.append(_GetMaxThroughput(iteration_data, metadata))
  samples.append(_GetMaxThroughputForLatencySLA(iteration_data, metadata))
  return samples


def Cleanup(benchmark_spec):
  """Cleanup.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  server = benchmark_spec.vm_groups['servers'][0]
  memcached_server.StopMemcached(server)
