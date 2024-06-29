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

"""Sysbench CPU Benchmarks.

This is a set of benchmarks that measures CPU performance.
"""

import logging
import re
from six import StringIO
import copy

from perfkitbenchmarker import configs
from perfkitbenchmarker import flag_util
from absl import flags
from perfkitbenchmarker import sample


FLAGS = flags.FLAGS

flags.DEFINE_integer('sysbench_cpu_time', 120,
                     'Limit for total execution time in seconds. 0 is unlimited.')
flags.DEFINE_integer('sysbench_cpu_events', 0,
                     'Limit for total number of events. 0 is unlimited.')
flags.DEFINE_integer('sysbench_cpu_cpu_max_prime', 10000,
                     'Upper limit for primes generator')
flag_util.DEFINE_integerlist(
    'sysbench_cpu_thread_counts',
    flag_util.IntegerList([0]),
    'An array of thread counts passed to sysbench, one at a time. A zero (0) '
    'thread count in the list will run sysbench with number of threads set '
    'equal to the number of VCPUs', module_name=__name__)

BENCHMARK_NAME = 'sysbench_cpu'
BENCHMARK_CONFIG = """
sysbench_cpu:
  description: Sysbench CPU benchmarks.
  vm_groups:
    vm_1:
      vm_spec: *default_single_core
"""


def GetConfig(user_config):
  return configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)


def _GetFloatFromLine(line):
  val = 0.0
  match = re.search(r'([0-9]*\.?[0-9]+)', line)
  if match is None:
    logging.error("Parsing error -- regex doesn't match for string: %s", line)
  else:
    try:
      val = float(match.group(1))
    except ValueError:
      logging.error("Parsing error -- type conversion failed for: %s", match.group(1))
  return val


def _ParseSysbenchOutput(sysbench_output, metadata):
  """Parses sysbench output.

  Args:
    sysbench_output: The output from sysbench.

  Returns:
    results: array of samples
  """

  """ Sample Sysbench --test=cpu Output:
  sysbench 1.0.11 (using system LuaJIT 2.1.0-beta3)

  Running the test with following options:
  Number of threads: 1
  Initializing random number generator from current time


  Prime numbers limit: 10000

  Initializing worker threads...

  Threads started!

  CPU speed:
      events per second:  1087.23

  General statistics:
      total time:                          9.1960s
      total number of events:              10000

  Latency (ms):
          min:                                  0.86
          avg:                                  0.92
          max:                                 19.89
          95th percentile:                      0.89
          sum:                               9191.34

  Threads fairness:
      events (avg/stddev):           10000.0000/0.00
      execution time (avg/stddev):   9.1913/0.00
  """
  results = []
  cpu_speed = None
  sysbench_output_io = StringIO(sysbench_output)
  for line in sysbench_output_io:
    sline = line.strip()
    metadata = copy.deepcopy(metadata)
    if sline.startswith("events per second:"):
      cpu_speed = _GetFloatFromLine(line)
      results.append(sample.Sample('cpu speed',
                                   cpu_speed, "events/s", metadata))
    if sline.startswith("total time:"):
      results.append(sample.Sample('total time',
                                   _GetFloatFromLine(line), "seconds", metadata))
    elif sline.startswith("total number of events:"):
      results.append(sample.Sample('total number of events',
                                   _GetFloatFromLine(line), "count", metadata))
    elif sline.startswith("min:"):
      results.append(sample.Sample('latency min',
                                   _GetFloatFromLine(line), "ms", metadata))
    elif sline.startswith("avg:"):
      results.append(sample.Sample('latency avg',
                                   _GetFloatFromLine(line), "ms", metadata))
    elif sline.startswith("max:"):
      results.append(sample.Sample('latency max',
                                   _GetFloatFromLine(line), "ms", metadata))
    elif sline.startswith("95th"):
      results.append(sample.Sample('latency 95th percentile',
                                   _GetFloatFromLine(line), "ms", metadata))
    elif sline.startswith("sum:"):
      results.append(sample.Sample('latency sum',
                                   _GetFloatFromLine(line), "ms", metadata))
  return results, cpu_speed


def _IssueSysbenchCommand(vm, thread_count):
  """Issues a sysbench run command.

  Args:
    vm: The test VM to issue command to.

  Returns:
    stdout, stderr: the result of the command.
  """
  stdout = ''
  stderr = ''
  run_cmd_tokens = ['sysbench',
                    '--cpu-max-prime=%d' % FLAGS.sysbench_cpu_cpu_max_prime,
                    '--events=%d' % FLAGS.sysbench_cpu_events,
                    '--time=%d' % FLAGS.sysbench_cpu_time,
                    '--threads=%d' % thread_count,
                    'cpu',
                    'run']
  run_cmd = ' '.join(run_cmd_tokens)
  stdout, stderr = vm.RobustRemoteCommand(run_cmd)
  logging.info('Sysbench results: \n stdout is:\n%s\nstderr is\n%s',
               stdout, stderr)
  return stdout, stderr


def Prepare(benchmark_spec):
  """Prepare the client test VM, installs SysBench, configures it.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  benchmark_spec.always_call_cleanup = True
  benchmark_spec.workload_name = "Sysbench CPU"
  _SetMetadataFromFlags(benchmark_spec)
  benchmark_spec.sut_vm_group = 'vm_1'

  vm = benchmark_spec.vms[0]
  vm.Install('sysbench1')


def _SetMetadataFromFlags(benchmark_spec):
  """Create meta data with all flags for sysbench."""
  benchmark_spec.tunable_parameters_metadata.update({
      'sysbench_cpu_time': FLAGS.sysbench_cpu_time,
      'sysbench_cpu_events': FLAGS.sysbench_cpu_events,
      'sysbench_cpu_cpu_max_prime': FLAGS.sysbench_cpu_cpu_max_prime,
  })


def _GetNumVcpus(vm):
  return vm.num_cpus


def Run(benchmark_spec):
  """Run the Sysbench CPU benchmark and publish results.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.

  Returns:
    Results.
  """
  results = []
  logging.info('Start benchmarking CPU with Sysbench')
  vm = benchmark_spec.vms[0]
  for thread_count in FLAGS.sysbench_cpu_thread_counts:
    if thread_count == 0:
      thread_count = _GetNumVcpus(vm)
    sample_metadata = {'sysbench_cpu_threads': thread_count}
    stdout, _ = _IssueSysbenchCommand(vm, thread_count)
    logging.info('\n Parsing Sysbench Results...\n')
    partial_results, _ = _ParseSysbenchOutput(stdout, sample_metadata)
    results.extend(partial_results)
  best_sample = None
  for result in results:
    if result.metric == 'cpu speed':
      if not best_sample or result.value > best_sample.value:
        best_sample = result
  if best_sample:
    best_sample.metadata['primary_sample'] = True
  return results


def Cleanup(benchmark_spec):
  """Clean up Sysbench CPU benchmark related states.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  del benchmark_spec
