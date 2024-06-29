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

"""Run YCSB against N instances of MongoDB on a single server.
"""

import functools
import posixpath
import math
import logging
import copy
import os

from itertools import repeat

from perfkitbenchmarker import configs
from absl import flags
from perfkitbenchmarker import flag_util
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import autoscale_util
from perfkitbenchmarker import errors
from perfkitbenchmarker import sample
from perfkitbenchmarker.linux_packages import ycsb
from perfkitbenchmarker.linux_packages import mongodb
from perfkitbenchmarker.linux_packages import stress_ng_build
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker.linux_packages import maven

FLAGS = flags.FLAGS

flags.DEFINE_integer('mongodb_ycsb_target_rate', 25000,
                     'The target number of total client operations per second '
                     'across all mongodb instances. Set to zero to run as fast '
                     'possible, i.e. no limit.',
                     lower_bound=0)
flags.DEFINE_integer('mongodb_record_count', 0,
                     'The number of records inserted into each MongoDB instance.'
                     ' Set to zero to allow benchmark to choose based on memory'
                     ' available.',
                     lower_bound=0)
flags.DEFINE_integer('mongodb_ycsb_load_threads', 30,
                     'Number of threads used per YCSB instance to in load phase.',
                     lower_bound=1)
flags.DEFINE_integer('mongodb_cache_size', None,
                     'Override default cache size per database instance. Units: GB',
                     lower_bound=1)
flags.DEFINE_float('mongodb_percentage_db_cache_db', 0.25,
                   'Percentage of Database in Database Cache',
                   lower_bound=0.0, upper_bound=1.0)
flags.DEFINE_float('mongodb_sla_p99latency', 3.0,
                   'p99 latency in ms',
                   lower_bound=0.0)
flags.DEFINE_boolean('mongodb_disk_database_access', True,
                     'Mongodb has to access disk for the database'
                     'database is in memory when this flag is False.')
flags.DEFINE_integer('mongodb_instances_min', 1,
                     'The minimum number of mongodb instances to run.',
                     lower_bound=1)
flags.DEFINE_integer('mongodb_instances_max_limit', 0,
                     'The maximum number of mongodb instances to run. Set'
                     ' to zero to run as many as will fit in memory or until'
                     ' throughput decreases two times consecutively.',
                     lower_bound=0)
flags.DEFINE_boolean('mongodb_enable_encryption', False,
                     'Enable encryption and authentication with TLS/SSL.')
# Flags used for experiments
flags.DEFINE_boolean('mongodb_numa_bind_cpu', False,
                     'Experimental -- do not use for benchmarking. Bind mongodb instances to CPUs. The CPUs will '
                     'be allocated as evenly as possible across instances.')
flags.DEFINE_boolean('mongodb_numa_bind_node', False,
                     'Experimental -- do not use for benchmarking. Bind mongodb instances to alternating NUMA nodes.')
flags.DEFINE_boolean('mongodb_numa_memory_interleave', False,
                     'Experimental -- do not use for benchmarking. MongoDB memory allocations will be made from '
                     'alternating NUMA nodes. That is, memory will be '
                     'allocated evenly across NUMA nodes.')
flags.DEFINE_boolean('mongodb_numa_memory_bind', False,
                     'Experimental -- do not use for benchmarking. MongoDB instance memory allocations will only be '
                     'made from a single NUMA node.')

BENCHMARK_NAME = 'mongodb_stress'
BENCHMARK_CONFIG = """
mongodb_stress:
  description: Run YCSB against N MongoDB instances on a single node.
  vm_groups:
    workers:
      vm_spec: *default_dual_core
      os_type: ubuntu2004
      disk_spec: *default_50_gb
      vm_count: 1
    clients:
      vm_spec: *default_dual_core
      os_type: ubuntu2004
  flags:
    enable_transparent_hugepages: false
    set_files: '/sys/kernel/mm/transparent_hugepage/defrag=never,/proc/sys/vm/zone_reclaim_mode=0'
    # pkb will reboot system if this option set-- sysctl: 'vm.swappiness=1'
    publish_after_run: true

    ycsb_field_count: 10
    ycsb_field_length: 100
    ycsb_operation_count: 100000000       # very large number, iteration run time limited by ycsb_timelimit
    ycsb_timelimit: 180                   # limit iteration to this number of seconds
    ycsb_workload_files: '90Read10Update'
    ycsb_measurement_type: hdrhistogram
    ycsb_client_vms: 1                    # use this number of client vms/machines
    ycsb_threads_per_client: '10'
"""

OUTPUT_FILE = 'moncaone.crt'
PRIVATE_KEY_FILE = 'moncaone.key'
PEM_FILE = 'moncaone.pem'
KEYSTORE_FILE = '/jre/lib/security'
KEY_DIR = posixpath.join(os.getcwd(), 'perfkitbenchmarker/data/mongodb_stress/')

KEY_PATH = posixpath.join(KEY_DIR + PEM_FILE)
CRT_FILE = posixpath.join(KEY_DIR + OUTPUT_FILE)
PRIV_KEY_FILE = posixpath.join(KEY_DIR + PRIVATE_KEY_FILE)

B_PER_KB = 1024
KB_PER_MB = 1024
MB_PER_GB = 1024
KB_PER_GB = KB_PER_MB * MB_PER_GB


def GetConfig(user_config):
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
  if FLAGS['ycsb_client_vms'].present:
    config['vm_groups']['clients']['vm_count'] = FLAGS.ycsb_client_vms
  return config


def _GetDataDir(vm):
  return posixpath.join(vm.GetScratchDir(), 'mongodb-data')


def _GetThreadsPerCore(vm):
  """returns the number of threads per core, i.e. 2 if hyper-threading is enabled"""
  stdout, _ = vm.RemoteCommand("lscpu | grep 'Thread(s) per core:' | head -1 | awk '{print $4}'")
  return int(stdout.strip())


def _GetCpuIdsPerNode(vm, node):
  """return two lists, the first represents the ids of the physical cpus,
  the second represents the hyper-threads of the specified numa node"""
  threads_per_core = _GetThreadsPerCore(vm)
  num_numa_nodes_per_socket = int(vm.numa_node_count / vm.CheckLsCpu().socket_count)
  num_vcpus_per_socket = int(vm.num_cpus / vm.CheckLsCpu().socket_count)
  num_cores_per_socket = int(num_vcpus_per_socket / (num_numa_nodes_per_socket * threads_per_core))
  # if the first two 'core ids' from /proc/cpuinfo are the same then the
  # physical and hyperthread cpuids are interleaved
  stdout, _ = vm.RemoteCommand("awk '/core id/{i++}i==1{print $4; exit}' /proc/cpuinfo")
  cpu_0_core_id = int(stdout.strip())
  stdout, _ = vm.RemoteCommand("awk '/core id/{i++}i==2{print $4; exit}' /proc/cpuinfo")
  cpu_1_core_id = int(stdout.strip())

  physical_cpu_ids = []
  hyperthread_cpu_ids = []
  if cpu_0_core_id == cpu_1_core_id:
    phys_start_cpu_id = node * num_vcpus_per_socket
    physical_cpu_ids.extend([cpu for cpu in range(phys_start_cpu_id,
                                                  phys_start_cpu_id + num_vcpus_per_socket, 2)])
    hyper_start_cpu_id = node * num_vcpus_per_socket + 1
    hyperthread_cpu_ids.extend([cpu for cpu in range(hyper_start_cpu_id,
                                                     hyper_start_cpu_id + num_vcpus_per_socket, 2)])
  else:
    phys_start_cpu_id = node * num_cores_per_socket
    physical_cpu_ids.extend([cpu for cpu in range(phys_start_cpu_id,
                                                  phys_start_cpu_id + num_cores_per_socket, 1)])
    hyper_start_cpu_id = num_vcpus_per_socket + node * num_cores_per_socket
    hyperthread_cpu_ids.extend([cpu for cpu in range(hyper_start_cpu_id,
                                                     hyper_start_cpu_id + num_cores_per_socket, 1)])
  return physical_cpu_ids, hyperthread_cpu_ids


def _GetCpuIds(vm):
  """return two lists, the first represents the ids of the physical cpus,
  the second represents the hyper-threads"""
  physical_cpu_ids = []
  hyperthread_cpu_ids = []
  for node in range(vm.numa_node_count):
    node_physical, node_hyper = _GetCpuIdsPerNode(vm, node)
    physical_cpu_ids.extend(node_physical)
    hyperthread_cpu_ids.extend(node_hyper)
  return physical_cpu_ids, hyperthread_cpu_ids


def _GetCpusForInstance(vm, index, mongodb_instnc):
  """return a string containing a comma separated list of cpu numbers"""
  physical_cpu_ids, hyperthread_cpu_ids = _GetCpuIds(vm)

  num_physical_cores_per_process = int(len(physical_cpu_ids) / mongodb_instnc)
  num_physical_cores_leftover = len(physical_cpu_ids) % mongodb_instnc
  num_physical_cores_already_assigned = index * num_physical_cores_per_process

  # give any leftover physical cores to the last server/process instance
  if index == mongodb_instnc - 1:
    num_physical_cores_per_process += num_physical_cores_leftover

  instance_physical_cpu_ids = physical_cpu_ids[num_physical_cores_already_assigned:
                                               num_physical_cores_already_assigned
                                               + num_physical_cores_per_process]
  instance_hyperthread_cpu_ids = []

  # if hyper-threading is enabled
  if _GetThreadsPerCore(vm) > 1:
    def _GetSiblingHyperThreadCpuId(physical_cpu_id):
      physical_index = physical_cpu_ids.index(physical_cpu_id)
      return hyperthread_cpu_ids[physical_index]
    # assign sibling hyperthreads
    instance_hyperthread_cpu_ids.extend([_GetSiblingHyperThreadCpuId(cpu_id)
                                         for cpu_id in instance_physical_cpu_ids])

  return ','.join(str(s) for s in instance_physical_cpu_ids + instance_hyperthread_cpu_ids)


def _GetNodeForInstance(instance_index, numa_node_count):
  return instance_index % numa_node_count


def _GetAvailableScratchKb(vm):
  """ returns the amount of KB available on scratch disk """
  df_command = "df {}".format(vm.GetScratchDir())
  df_command += " | tail -1 | awk '{print $4}'"
  stdout, _ = vm.RemoteCommand(df_command)
  available = int(stdout)
  logging.info("{}KB available on {}".format(available, vm.GetScratchDir()))
  return available


def _GetUsableMemoryKb(vm):
  """ returns an estimate of the usable memory on the VM.
  """
  OS_OVERHEAD_KB = 1000000  # give the OS 1GB
  return vm.total_memory_kb - OS_OVERHEAD_KB


def _RemoteBackgroundCommand(vm, command):
  vm.RemoteCommand('nohup {0} 1> /dev/null 2> /dev/null &'.format(command))


def _GetMemoryToFillKB(vm, mongodb_instance_count):
  """ returns the total amount of memory that should be filled. """
  mongodb_reserve_kb = _GetMemoryRequiredPerInstanceKB(vm) * mongodb_instance_count
  fill_kb = _GetUsableMemoryKb(vm) - mongodb_reserve_kb
  return max(fill_kb, 0)


def _ShouldUseNumaCtl():
  """ returns true if workload is NUMA optimized """
  return FLAGS.mongodb_numa_bind_cpu or \
      FLAGS.mongodb_numa_bind_node or \
      FLAGS.mongodb_numa_memory_interleave or \
      FLAGS.mongodb_numa_memory_bind


def _FillMemory(vm, fill_kb):
  """ reduce amount of memory available to mongodb and file cache """
  assert FLAGS.mongodb_disk_database_access
  vm.Install('stress_ng_build')

  logging.info("stress-ng allocating {0}KB memory so that it will not be available for file cache.".format(fill_kb))

  num_numa_nodes = vm.numa_node_count if _ShouldUseNumaCtl() else 1
  cmd = '{0} --vm-bytes {1}k --vm-keep --vm-hang 0 --vm {2}'.format(
      stress_ng_build.STRESS_NG,
      fill_kb // num_numa_nodes,
      vm.num_cpus // num_numa_nodes)
  if num_numa_nodes > 1:
    vm.InstallPackages('numactl')
    for node in range(num_numa_nodes):
      nc_cmd = 'numactl --cpunodebind={0} --membind={0} -- {1}'.format(node, cmd)
      _RemoteBackgroundCommand(vm, nc_cmd)
  else:
    _RemoteBackgroundCommand(vm, cmd)


def _UnfillMemory(vm):
  assert FLAGS.mongodb_disk_database_access
  logging.info("stopping stress-ng to free memory")
  vm.RemoteCommand('sudo pkill stress-ng')


def _GetDatabaseInstanceSizeKB(vm):
  """ returns the size of the database for each MongoDB instance """
  return int(round((_GetRecordCountPerInstance(vm) * FLAGS.ycsb_field_count * FLAGS.ycsb_field_length) / float(B_PER_KB)))


def _GetDatabaseInstanceCacheKB(vm):
  """ returns the size of the Wired Tiger cache for each MongoDB instance """
  # WiredTiger cache size must be at least 1GB
  min_size = 1 * KB_PER_GB
  calc_size = int(round(_GetDatabaseInstanceSizeKB(vm) * FLAGS.mongodb_percentage_db_cache_db))
  return max(min_size, calc_size)


def _MaxNumMongoInstances(vm):
  """ returns maximum number of MongoDB instances based on database size,
      amount of available memory and scratch disk space """
  max_instances_mem = int(math.floor(_GetUsableMemoryKb(vm) / _GetMemoryRequiredPerInstanceKB(vm)))
  logging.info("Num mongodb instances that will fit in memory: {}".format(max_instances_mem))
  max_instances_disk = int(math.floor(_GetAvailableScratchKb(vm) / _GetDatabaseInstanceSizeKB(vm)))
  logging.info("Num mongodb instances that will fit on disk: {}".format(max_instances_disk))
  max_from_resources = min(max_instances_disk, max_instances_mem)
  if FLAGS.mongodb_instances_max_limit > 0:
    return min(max_from_resources, FLAGS.mongodb_instances_max_limit)
  else:
    return max_from_resources


def _GetMemoryRequiredPerInstanceKB(vm):
  """ returns the amount of memory that must be available for
      a single instance of MongoDB """
  cache_size_kb = _GetDatabaseInstanceCacheKB(vm)
  bookkeeping_per_record_b = 256  # very much a guess
  bookkeeping_b = _GetRecordCountPerInstance(vm) * bookkeeping_per_record_b
  bookkeeping_kb = int(round(bookkeeping_b / float(B_PER_KB)))
  process_kb = 1 * KB_PER_GB  # also a guess
  fs_cache_kb = cache_size_kb  # somewhat arbitrary
  required_kb = cache_size_kb + process_kb + bookkeeping_kb + fs_cache_kb
  logging.info("Calculated memory required per instance: {}".format(required_kb))
  return required_kb


def _GetRecordCountPerInstance(vm):
  """ returns the number of records that will be inserted into each
      instance of MongoDB, scaled to available memory and num vcpus """
  if FLAGS.mongodb_record_count:
    return FLAGS.mongodb_record_count
  RECORD_OVERHEAD_B = 256  # a very rough estimate
  RECORD_B = FLAGS.ycsb_field_count * FLAGS.ycsb_field_length + RECORD_OVERHEAD_B
  MAX_DB_INSTANCES = 16  # arbitrary upper limit
  SCALING_FACTOR = 0.032  # determined this number by playing around with below formula in Excel
  estimated_max_instances = math.ceil(MAX_DB_INSTANCES * (1 - math.exp(-SCALING_FACTOR * vm.NumCpusForBenchmark())))
  memory_per_instance_kb = _GetUsableMemoryKb(vm) / estimated_max_instances
  num_records = int(round((memory_per_instance_kb * B_PER_KB) / RECORD_B, -6))  # round to the nearest million
  logging.debug("Calculated records per instance: {}".format(num_records))
  num_records = max(num_records, 2000000)   # min records per database
  num_records = min(num_records, 20000000)  # max records per database
  logging.info("Records per instance: {}".format(num_records))
  return num_records


def _PrepareServer(vm):
  """Installs MongoDB on the server."""
  vm.Install('mongodb')
  if _ShouldUseNumaCtl():
    vm.InstallPackages('numactl')


def _PrepareClient(vm):
  """Install YCSB on the client VM."""
  vm.Install('ycsb')
  # Disable logging for MongoDB driver, which is otherwise quite verbose.
  log_config = """<configuration><root level="WARN"/></configuration>"""
  vm.RemoteCommand("echo '{0}' > {1}/logback.xml".format(
      log_config, ycsb.YCSB_DIR))
  if FLAGS.mongodb_enable_encryption:
    vm.PushDataFile(KEY_PATH, ycsb.YCSB_DIR)
    java_home = maven._GetJavaHome(vm)
    keystore_path = posixpath.join(java_home + KEYSTORE_FILE)
    stdout, _ = vm.RemoteCommand('cd {0} && sudo keytool -import -noprompt -trustcacerts -alias cacert -storepass changeit -keystore {1}/cacerts -file {2}'.format(ycsb.YCSB_DIR, keystore_path, ycsb.YCSB_DIR + '/' + PEM_FILE))


def Prepare(benchmark_spec):
  """Install MongoDB on one VM and YCSB on others.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  benchmark_spec.always_call_cleanup = True
  mongodb_vm = benchmark_spec.vm_groups['workers'][0]

  if FLAGS.mongodb_enable_encryption:
    cn_name = ('/CN=' + mongodb_vm.hostname)
    openssl_cmd = ['openssl', 'req', '-newkey', 'rsa:2048', '-new', '-x509', '-days', '3650', '-nodes', '-out', CRT_FILE, '-keyout', PRIV_KEY_FILE, '-subj', cn_name]
    logging.info("Create public and private key pair with openssl ({})".format(openssl_cmd))
    vm_util.IssueCommand(openssl_cmd)

    logging.info("Concatenate public and private key")
    vm_util.IssueCommand("sed w{2} {0} {1}".format(CRT_FILE, PRIV_KEY_FILE, KEY_PATH).split())

    mongodb_vm.PushDataFile(KEY_PATH, mongodb.INSTALL_DIR)

  if _MaxNumMongoInstances(mongodb_vm) == 0:
    raise Exception("Insufficient memory or disk space to execute workload "
                    "as currently configured. "
                    "Consider reducing the number of records.")

  server_partials = [functools.partial(_PrepareServer, mongodb_vm)]
  client_partials = [functools.partial(_PrepareClient, client)
                     for client in benchmark_spec.vm_groups['clients']]
  vm_util.RunThreaded((lambda f: f()), server_partials + client_partials)


def _GetClientVms(benchmark_spec, mongodb_instnc, num_client_vms):
  ycsb_vms = benchmark_spec.vm_groups['clients']
  num_ycsb = mongodb_instnc
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


def _ConfigureServer(vm, mongodb_cache_size, mongodb_instnc):
  """ configure and start mongodb """
  mongodb.Configure(vm,
                    FLAGS.mongodb_enable_encryption,
                    mongodb_cache_size,
                    mongodb_instnc,
                    autoscale_util.GetInternalIpAddresses(vm)
                    )
  if not _ShouldUseNumaCtl():
     mongodb.Start(vm, FLAGS.mongodb_enable_encryption, mongodb_instnc)
  else:
    vm.RemoteCommand('sudo sync')
    vm.DropCaches()
    for i in range(mongodb_instnc):
      cmd = 'sudo numactl'
      if FLAGS.mongodb_numa_bind_cpu:
        cmd += ' --physcpubind={0}'.format(_GetCpusForInstance(vm, i, mongodb_instnc))
      elif FLAGS.mongodb_numa_bind_node:
        cmd += ' --cpunodebind={0}'.format(_GetNodeForInstance(i, vm.numa_node_count))
      if FLAGS.mongodb_numa_memory_interleave:
        cmd += ' --interleave=all'
      elif FLAGS.mongodb_numa_memory_bind:
        cmd += ' --membind={0}'.format(_GetNodeForInstance(i, vm.numa_node_count))
      cmd += ' -- {0}'.format(mongodb.GetStartCommand(vm, i, FLAGS.mongodb_enable_encryption))
      logging.info('Starting MongoDB: {0}'.format(cmd))
      vm.RemoteCommand(cmd)


def _LoadWorkload(benchmark_spec, mongodb_vm, mongodb_instance_count, num_client_vms):

  server_ips = autoscale_util.GetInternalIpAddresses(mongodb_vm)

  if FLAGS.mongodb_enable_encryption:
    # With the mongodb_enable_encryption enabled, workload will use server hostname in
    # mongodb.url instead of the IP address. As of now, mongodb.url with ssl=true donot
    # accept the ip address. Thus, workload will not accept multiple ip addresses with
    # the encrytion enabled
    server_metadata = [
        {'mongodb.url': '"mongodb://{0}:{1}/ycsbdb?ssl=true&maxPoolSize=256"'.format(mongodb_vm.hostname,
                                                                                     mongodb.MONGODB_FIRST_PORT
                                                                                     + i % mongodb_instance_count)}
        for i in range(mongodb_instance_count)]
  else:
    server_metadata = [
        {'mongodb.url': 'mongodb://{0}:{1}/?maxPoolSize=256'.format(server_ips[i % len(server_ips)],
                                                                    mongodb.MONGODB_FIRST_PORT
                                                                    + i % mongodb_instance_count)}
        for i in range(mongodb_instance_count)]

  benchmark_spec.executor = ycsb.YCSBExecutor('mongodb', cp=ycsb.YCSB_DIR, **{
                                              'shardkeyspace': True,
                                              'perclientparam': server_metadata})
  # load records into database(s)
  benchmark_spec.executor.Load(_GetClientVms(benchmark_spec, mongodb_instance_count, num_client_vms),
                               load_kwargs={'threads': FLAGS.mongodb_ycsb_load_threads})


def _ShouldFillMemory(fill_kb):
  return FLAGS.mongodb_disk_database_access and fill_kb > 0


def _RunWorkload(benchmark_spec, vm, mongodb_instance_count, records_per_instance, num_client_vms):

  # fill a block of memory...maybe
  fill_kb = _GetMemoryToFillKB(vm, mongodb_instance_count)
  fill = _ShouldFillMemory(fill_kb)
  if fill:
    _FillMemory(vm, fill_kb)

  # each database in each iteration should have the same number of records
  FLAGS.ycsb_record_count = records_per_instance * mongodb_instance_count
  mongodb_instance_cache_gb = FLAGS.mongodb_cache_size or\
      int(round(_GetDatabaseInstanceCacheKB(vm) / float(KB_PER_GB)))
  _ConfigureServer(vm, mongodb_instance_cache_gb, mongodb_instance_count)
  _LoadWorkload(benchmark_spec, vm, mongodb_instance_count, num_client_vms)

  if FLAGS.mongodb_ycsb_target_rate > 0:
    ycsb_target_rate_value = mongodb_instance_count * FLAGS.mongodb_ycsb_target_rate
  else:
    ycsb_target_rate_value = None
  samples = list(benchmark_spec.executor.Run(_GetClientVms(benchmark_spec,
                                                           mongodb_instance_count, num_client_vms),
                                             run_kwargs={'target': ycsb_target_rate_value}))
  if fill:
    _UnfillMemory(vm)

  mongodb.Stop(vm, mongodb_instance_count)

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
    # p99read is the 2nd item, p99update is 3rd
    if data[0].value > max_throughput:
      max_throughput = data[0].value
      max_throughput_iteration = iteration
  assert max_throughput_iteration >= 0
  sample_metadata = copy.deepcopy(metadata)
  read_lat = iteration_data[max_throughput_iteration][1].value \
      if iteration_data[max_throughput_iteration][1] else 'None'
  update_lat = iteration_data[max_throughput_iteration][2].value \
      if iteration_data[max_throughput_iteration][2] else 'None'
  sample_metadata['p99ReadLatency'] = read_lat
  sample_metadata['p99UpdateLatency'] = update_lat
  sample_metadata['iteration'] = max_throughput_iteration + 1
  if max_throughput_iteration == len(iteration_data) - 1:
    msg = "Maximum throughput was found on the last iteration. "\
          "System may have more capacity."
    logging.warn(msg)
    sample_metadata['warning'] = msg
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
    if data[0].value > max_throughput and data[1].value <= FLAGS.mongodb_sla_p99latency:
      max_throughput = data[0].value
      max_throughput_iteration = iteration
  if max_throughput_iteration >= 0:
    sample_metadata = copy.deepcopy(metadata)
    read_lat = iteration_data[max_throughput_iteration][1].value \
        if iteration_data[max_throughput_iteration][1] else 'None'
    update_lat = iteration_data[max_throughput_iteration][2].value \
        if iteration_data[max_throughput_iteration][2] else 'None'
    sample_metadata['p99ReadLatency'] = read_lat
    sample_metadata['p99UpdateLatency'] = update_lat
    sample_metadata['iteration'] = max_throughput_iteration + 1
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
  """Run YCSB against MongoDB.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.

  Returns:
    A list of sample.Sample objects.
  """
  samples = []
  mongodb_vm = benchmark_spec.vm_groups['workers'][0]
  max_mongodb_instnc = _MaxNumMongoInstances(mongodb_vm)
  logging.info("The maximum number of MongoDB instances limited to {0}".format(max_mongodb_instnc))
  assert(max_mongodb_instnc > 0)
  records_per_instance = _GetRecordCountPerInstance(mongodb_vm)
  iteration_data = []  # array of tuple of three samples for each iteration (throughput, p99read, p99write)
  for mongodb_instnc in range(FLAGS.mongodb_instances_min, max_mongodb_instnc + 1):
    logging.info("Measuring performance with {0} MongoDB instance(s).".format(mongodb_instnc))
    mongodb_vm.DropCaches()
    instance_samples = _RunWorkload(benchmark_spec, mongodb_vm,
                                    mongodb_instnc, records_per_instance,
                                    FLAGS.ycsb_client_vms)
    iteration_data.append(_GetRelevantIterationData(instance_samples))
    throughput = iteration_data[-1][0].value if iteration_data[-1][0] else 'None'
    read_lat = iteration_data[-1][1].value if iteration_data[-1][1] else 'None'
    update_lat = iteration_data[-1][2].value if iteration_data[-1][2] else 'None'
    logging.info('Throughput: {}\tp99 Read Latency: {}\tp99 Update Latency: {}'.format(throughput,
                                                                                       read_lat,
                                                                                       update_lat))
    samples.extend(instance_samples)
    if _MeetsExitCriteria(samples):
      logging.info("Exit criteria met.")
      break

  metadata = {'MongoDB Version': mongodb.MONGODB_VERSION}
  samples.append(_GetMaxThroughput(iteration_data, metadata))
  samples.append(_GetMaxThroughputForLatencySLA(iteration_data, metadata))
  return samples


def Cleanup(benchmark_spec):
  """Remove MongoDB and YCSB.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  pass
