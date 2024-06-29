# Copyright 2014 PerfKitBenchmarker Authors. All rights reserved.
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

"""Run memtier_benchmark against Redis.

memtier_benchmark is a load generator created by RedisLabs to benchmark
Redis.

Redis homepage: http://redis.io/
memtier_benchmark homepage: https://github.com/RedisLabs/memtier_benchmark
"""

import functools
import logging
import re

from perfkitbenchmarker import configs
from perfkitbenchmarker import errors
from absl import flags
from perfkitbenchmarker import sample
from perfkitbenchmarker import vm_util
from perfkitbenchmarker.linux_packages import intel_redis_server
from perfkitbenchmarker.linux_packages import INSTALL_DIR

flags.DEFINE_integer('intel_redis_numprocesses', 1, 'Number of Redis processes to '
                     'spawn per processor.')
flags.DEFINE_integer('intel_redis_clients', 5, 'Number of redis loadgen clients')
flags.DEFINE_string('intel_redis_setgetratio', '1:0', 'Ratio of writes to reads '
                    'performed by the memtier benchmark, default is '
                    '\'1:0\', ie: writes only.')
# Must be >= 256 for PMEM to be used by https://github.com/pmem/redis/tree/5.0-poc_cow/src.
# The reason is this check: https://github.com/pmem/redis/blob/5.0-poc_cow/src/sds.c#L226
flags.DEFINE_integer('intel_redis_datasize', 256, 'Object data size.')
flags.DEFINE_integer('intel_redis_client_threads_min', 1, 'Starting thread count.')
flags.DEFINE_float('intel_redis_target_latency_percentile', 50.0,
                   'The percentile used to compare against the provided limit.')
flags.DEFINE_float('intel_redis_latency_limit', 0.0,
                   'Latency threshold in milli-seconds. Stop when threshold '
                   'met. When zero, the threshold is set to 20 times the '
                   'latency measured with one thread.')
flags.DEFINE_integer('intel_redis_pipelined_requests', 1,
                     'Number of concurrent pipelined requests (default: 1).')
flags.DEFINE_boolean('intel_redis_cpu_collect', False,
                     'collect cpu utilization for each redis process (default: False).')
flags.DEFINE_string('intel_redis_version', '6.0.8',
                    'Version of redis server to use.')
flags.DEFINE_boolean('intel_redis_configure_os', True,
                     'Reconfigure the OS to achieve best performance. Might not work on all providers (for example, fails on Kubernetes). Beware, some changes are currently made permanently!')


FIRST_PORT = 6379
FLAGS = flags.FLAGS
results_dir = INSTALL_DIR + '/results'
BENCHMARK_NAME = 'intel_redis'
BENCHMARK_CONFIG = """
intel_redis:
  description: >
      Run memtier_benchmark against Redis.
      Specify the number of client VMs with --intel_redis_clients.
  vm_groups:
    workers:
      vm_spec: *default_single_core
      vm_count: 1
    clients:
      vm_spec: *default_single_core
"""
BENCHMARK_OS_CONFIG = """
flags:
  enable_transparent_hugepages: false
  set_files: '/sys/kernel/mm/transparent_hugepage/defrag=never,/proc/sys/vm/zone_reclaim_mode=0'
"""


def GetConfig(user_config):
  config = BENCHMARK_CONFIG
  if FLAGS.intel_redis_configure_os:
    config += BENCHMARK_OS_CONFIG
  config = configs.LoadConfig(config, user_config, BENCHMARK_NAME)
  config['vm_groups']['clients']['vm_count'] = FLAGS.intel_redis_clients
  return config


def _PrepareLoadgen(load_vm):
  load_vm.Install('memtier')
  load_vm.RemoteCommand('mkdir -p {}'.format(results_dir))


def _GetNumRedisServers(redis_vm):
  """Get the number of redis servers to install/use for this test."""
  if FLAGS.num_cpus_override:
    return FLAGS.num_cpus_override * FLAGS.intel_redis_numprocesses
  return redis_vm.NumCpusForBenchmark() * FLAGS.intel_redis_numprocesses


def Prepare(benchmark_spec):
  """Install Redis on one VM and memtier_benchmark on another.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  benchmark_spec.always_call_cleanup = True
  redis_vm = benchmark_spec.vm_groups['workers'][0]
  client_vms = benchmark_spec.vm_groups['clients']
  intel_redis_server.FLAGS.intel_redis_server_version = FLAGS.intel_redis_version
  intel_redis_server.FLAGS.intel_redis_server_configure_os = FLAGS.intel_redis_configure_os

  # install and configure redis on the server
  redis_vm.Install('intel_redis_server')
  redis_vm.Install('sysstat')
  redis_vm.RemoteCommand('mkdir -p {}'.format(results_dir))
  intel_redis_server.Configure(redis_vm, _GetNumRedisServers(redis_vm))
  intel_redis_server.Start(redis_vm, _GetNumRedisServers(redis_vm))

  args = [((vm,), {}) for vm in client_vms]
  vm_util.RunThreaded(_PrepareLoadgen, args)


def _RedisInit(redis_vm, load_vm, port, key_max):
  base_cmd = ('memtier_benchmark -R -n allkeys -d {} --randomize --distinct-client-seed '
              '--ratio 1:0 --key-pattern P:P --key-minimum=1 --key-maximum={} --pipeline 64 -t 1 '
              '-s {} -p {} > {}')
  final_cmd = (base_cmd.format(FLAGS.intel_redis_datasize, key_max, redis_vm.internal_ip, port, '{}/outfile-load-{}'.format(results_dir, port)))
  load_vm.RemoteCommand(final_cmd)


def _RunLoad(redis_vm, load_vm, threads, port, test_id, key_max):
  """Spawn a memteir_benchmark on the load_vm against the redis_vm:port.

  Args:
    redis_vm: The target of the memtier_benchmark
    load_vm: The vm that will run the memtier_benchmark.
    threads: The number of threads to run in this memtier_benchmark process.
    port: the port to target on the redis_vm.
  Returns:
    A throughput, latency tuple, or None if threads was 0.
  """
  if threads == 0:
    return None

  base_cmd = ('memtier_benchmark -s {}  -p {}  -d {} --randomize --distinct-client-seed '
              '--ratio {} --key-pattern R:R --key-minimum=1 --key-maximum={} -x 1 -c 1 -t {} '
              '--test-time={}  --pipeline={} > {} ;')
  final_cmd = (base_cmd.format(redis_vm.internal_ip, port, FLAGS.intel_redis_datasize,
                               FLAGS.intel_redis_setgetratio, key_max, threads, 10,
                               FLAGS.intel_redis_pipelined_requests,
                               '/dev/null') +
               base_cmd.format(redis_vm.internal_ip, port, FLAGS.intel_redis_datasize,
                               FLAGS.intel_redis_setgetratio, key_max, threads, 20,
                               FLAGS.intel_redis_pipelined_requests,
                               '{}/outfile-{}'.format(results_dir, test_id)) +
               base_cmd.format(redis_vm.internal_ip, port, FLAGS.intel_redis_datasize,
                               FLAGS.intel_redis_setgetratio, key_max, threads, 10,
                               FLAGS.intel_redis_pipelined_requests,
                               '/dev/null'))

  load_vm.RemoteCommand(final_cmd)
  output, _ = load_vm.RemoteCommand('cat {}/outfile-{}'.format(results_dir, test_id))

  def _ParseOutput(output):
    result = {}
    set_latency_percentile = []
    get_latency_percentile = []
    for line in output.splitlines():
      if line.startswith('Sets'):
        match = re.search(r'^Sets\s+([0-9]*\.?[0-9]+)[\s-]+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)', line)
        result['set_ops_throughput'] = float(match.group(1))
        result['set_avg_latency'] = float(match.group(2))
        result['set_kb_throughput'] = float(match.group(3))
      elif line.startswith('Gets'):
        match = re.search(r'^Gets\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)', line)
        result['get_ops_throughput'] = float(match.group(1))
        result['get_hit_throughput'] = float(match.group(2))
        result['get_miss_throughput'] = float(match.group(3))
        result['get_avg_latency'] = float(match.group(4))
        result['get_kb_throughput'] = float(match.group(5))
      elif line.startswith('Totals'):
        match = re.search(r'^Totals\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)', line)
        result['ops_throughput'] = float(match.group(1))
        result['hit_throughput'] = float(match.group(2))
        result['miss_throughput'] = float(match.group(3))
        result['avg_latency'] = float(match.group(4))
        result['kb_throughput'] = float(match.group(5))
      elif line.startswith('SET'):
        match = re.search(r'^SET\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)', line)
        set_latency_percentile.append((float(match.group(1)), float(match.group(2))))
      elif line.startswith('GET'):
        match = re.search(r'^GET\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)', line)
        get_latency_percentile.append((float(match.group(1)), float(match.group(2))))

    result['set_target_latency'] = 0
    for latency, percentile in set_latency_percentile:
      if percentile >= FLAGS.intel_redis_target_latency_percentile:
        result['set_target_latency'] = latency
        break

    result['get_target_latency'] = 0
    for latency, percentile in get_latency_percentile:
      if percentile >= FLAGS.intel_redis_target_latency_percentile:
        result['get_target_latency'] = latency
        break

    return result

  return _ParseOutput(output)


def Run(benchmark_spec):
  """Run memtier_benchmark against Redis.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.

  Returns:
    A list of sample.Sample objects.
  """
  redis_vm = benchmark_spec.vm_groups['workers'][0]
  load_vms = benchmark_spec.vm_groups['clients']
  latency = 0.0
  latency_threshold = 1000000.0  # a temporary high value > latency
  threads = 1  # we always get a baseline with one thread
  results = []
  num_servers = _GetNumRedisServers(redis_vm)
  shard_size = int(redis_vm.total_memory_kb / num_servers) * 800
  key_max = int(shard_size * 0.8 / FLAGS.intel_redis_datasize)
  args = [((redis_vm, load_vms[i % len(load_vms)], FIRST_PORT + i % num_servers, key_max),
           {}) for i in range(num_servers)]
  vm_util.RunThreaded(_RedisInit, args)

  cpu_cmd = '( sleep 15; pidstat -p `ps -ef|grep redis| grep -v grep|awk \'{print $2}\' |tr "\\n" "," | sed \'s/,$//\'` 5 2 > stats.txt ; \
    sed -n \'/Average/,$p\' stats.txt > average.txt;\
    awk -v c=%CPU \'NR==1 {for (i=1; i<=NF; i++) if ($i==c) break} {print $(i)}\' "average.txt"| tail -' + str(num_servers) + ') > cpu.txt &'

  max_throughput_for_completion_latency_under_1ms = 0.0

  while latency < latency_threshold:
    num_loaders = len(load_vms) * num_servers
    args = [((redis_vm, load_vms[i % len(load_vms)], int(threads / num_loaders) +
              (0 if (i + 1) > threads % num_loaders else 1),
              FIRST_PORT + i % num_servers, i, key_max),
             {}) for i in range(num_loaders)]

    if FLAGS.intel_redis_cpu_collect:
      redis_vm.RemoteCommand('cd {};{}'.format(results_dir, cpu_cmd))
    client_results = [i for i in vm_util.RunThreaded(_RunLoad, args)
                      if i is not None]
    logging.info('Redis results by client: {}'.format(client_results))

    # total throughput across clients
    total_throughput = sum(r['ops_throughput'] for r in client_results)
    if not total_throughput:
      raise errors.Benchmarks.RunError(
          'Zero throughput for {} threads: {}'.format(threads, client_results))

    # get/set latency across clients
    total_set_throughput = sum(r['set_ops_throughput'] for r in client_results)
    if total_set_throughput:
      total_set_target_latency = sum(r['set_target_latency'] * r['set_ops_throughput']
                                     for r in client_results) / total_set_throughput
    else:
      total_set_target_latency = 0
    total_get_throughput = sum(r['get_ops_throughput'] for r in client_results)
    if total_get_throughput:
      total_get_target_latency = sum(r['get_target_latency'] * r['get_ops_throughput']
                                     for r in client_results) / total_get_throughput
    else:
      total_get_target_latency = 0

    latency = (total_set_target_latency * total_set_throughput +
               total_get_target_latency * total_get_throughput) / \
        total_throughput

    if latency < 1.0:
      max_throughput_for_completion_latency_under_1ms = max(
          max_throughput_for_completion_latency_under_1ms,
          total_throughput)

    if FLAGS.intel_redis_cpu_collect:
      cpu_perc = ""
      cpu_output, _ = redis_vm.RemoteCommand('cat {}/cpu.txt'.format(results_dir))
      for line in cpu_output.splitlines():
        cpu_perc = cpu_perc + line + ','
      cpu_perc = '[' + cpu_perc[:-1] + ']'
      results.append(sample.Sample('total_throughput', total_throughput, 'ops/s',
                                   {'latency': latency,
                                    'percentile': FLAGS.intel_redis_target_latency_percentile,
                                    'threads': threads,
                                    'cpu perc': cpu_perc}))
      logging.info('Threads : {}  ({}, {}) < {} {}'.format(threads, total_throughput, latency,
                                                           latency_threshold, cpu_perc))

    else:
      results.append(sample.Sample('total_throughput', total_throughput, 'ops/s',
                                   {'latency': latency,
                                    'percentile': FLAGS.intel_redis_target_latency_percentile,
                                    'threads': threads
                                    }))
      logging.info('Threads : {}  ({}, {}) < {}'.format(threads, total_throughput, latency,
                                                        latency_threshold))


    if threads == 1:  # first time through loop
      if FLAGS.intel_redis_latency_limit == 0:
        latency_threshold = latency * 20
      else:
        latency_threshold = FLAGS.intel_redis_latency_limit
      threads = max(2, FLAGS.intel_redis_client_threads_min)
    else:
      threads += max(1, int(threads * .15))

  results.append(sample.Sample(
                 'max_throughput_for_completion_latency_under_1ms',
                 max_throughput_for_completion_latency_under_1ms,
                 'ops/s'))

  return results


def _CleanupClients(vms):
  def _CleanupClient(vm):
    vm.RemoteCommand('rm -rf {}'.format(results_dir))
  vm_util.RunThreaded(_CleanupClient, vms)


def _CleanupWorkers(vms):
  def _CleanupWorker(vm):
    intel_redis_server.Cleanup(vm)
    vm.RemoteCommand('rm -rf {}'.format(results_dir))
  vm_util.RunThreaded(_CleanupWorker, vms)


def Cleanup(benchmark_spec):
  """Remove Redis and memtier.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  workers = benchmark_spec.vm_groups['workers']
  clients = benchmark_spec.vm_groups['clients']
  client_partials = [functools.partial(_CleanupClients,
                                       clients)]
  worker_partials = [functools.partial(_CleanupWorkers,
                                       workers)]
  vm_util.RunThreaded((lambda f: f()), client_partials + worker_partials)
