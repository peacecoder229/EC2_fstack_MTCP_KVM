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

"""Runs stress-ng benchmarks.

stress-ng will stress test a computer system in various selectable ways.
"""

import logging
import re
from six import StringIO
import numpy
import os

from perfkitbenchmarker import configs
from perfkitbenchmarker import flag_util
from absl import flags
from perfkitbenchmarker import sample
from perfkitbenchmarker import vm_util
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker.linux_packages import stress_ng_build
from perfkitbenchmarker import errors

FLAGS = flags.FLAGS

flags.DEFINE_integer('intel_stress_ng_t', 5,
                     'Execution time per method in seconds.',
                     lower_bound=1)

BENCHMARK_CPU_METHODS = [
    'ackermann',
    'bitops',
    'callfunc',
    'cdouble',
    'cfloat',
    'clongdouble',
    'correlate',
    'crc16',
    'decimal32',
    'decimal64',
    'decimal128',
    'dither',
    'djb2a',
    'double',
    'euler',
    'explog',
    'fft',
    'factorial',
    'fibonacci',
    'float',
    'float32',
    'float80',
    'float128',
    'fnv1a',
    'gamma',
    'gcd',
    'gray',
    'hamming',
    'hanoi',
    'hyperbolic',
    'idct',
    'int128',
    'int64',
    'int32',
    'int16',
    'int8',
    'int128float',
    'int128double',
    'int128longdouble',
    'int128decimal32',
    'int128decimal64',
    'int128decimal128',
    'int64float',
    'int64double',
    'int64longdouble',
    'int32float',
    'int32double',
    'int32longdouble',
    'jenkin',
    'jmp',
    'ln2',
    'longdouble',
    'loop',
    'matrixprod',
    'nsqrt',
    'omega',
    'parity',
    'phi',
    'pi',
    'pjw',
    'prime',
    'psi',
    'queens',
    'rand',
    'rand48',
    'rgb',
    'sdbm',
    'sieve',
    'stats',
    'sqrt',
    'trig',
    'union',
    'zeta'
]

flags.DEFINE_list('intel_stress_ng_cpu_method', BENCHMARK_CPU_METHODS,
                  'A list of cpu-methods to run.')
flags.register_validator('intel_stress_ng_cpu_method',
                         lambda methods: methods and set(methods).issubset(BENCHMARK_CPU_METHODS))

flag_util.DEFINE_integerlist(
    'intel_stress_ng_cpu',
    flag_util.IntegerList([1, 0]),
    'An array of thread counts passed to stress-ng, one at a time. A zero (0) '
    'thread count in the list will run stress-ng with number of threads set '
    'equal to the number of VCPUs', module_name=__name__)

BENCHMARK_NAME = 'intel_stress_ng'
BENCHMARK_CONFIG = """
intel_stress_ng:
  description: STRESS-NG benchmark.
  vm_groups:
    default:
      vm_spec: *default_single_core
      os_type: ubuntu1804
"""


def GetConfig(user_config):
  return configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)


def _GetCpuMethods(vm):
  """Returns list of CPU Methods
  """
  stdout, _ = vm.RemoteCommand('{} --cpu 0 --cpu-method x 2>&1'.format(stress_ng_build.STRESS_NG), ignore_failure=True)
  methods = stdout.split(':')[1].split()[1:]
  logging.info("Stress-ng supported CPU methods: {}".format(str(methods)))
  return methods


def Prepare(benchmark_spec):
  """Prepare the client test VM, installs stress-ng.
  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  benchmark_spec.always_call_cleanup = True
  vm = benchmark_spec.vms[0]
  vm.Install('stress_ng_build')
  # make sure stress-ng supports the expected CPU methods
  supported_methods = set(_GetCpuMethods(vm))
  expected_methods = set(BENCHMARK_CPU_METHODS)
  if expected_methods != supported_methods:
    if expected_methods - supported_methods:
      logging.error("Stress-ng does not support these expected CPU methods: {}".format(str(expected_methods - supported_methods)))
      raise errors.Benchmarks.PrepareException("Stress-ng does not support expected CPU methods.")
    else:
      logging.warning("Stress-ng supports more than expected CPU methods: {}".format(str(supported_methods - expected_methods)))


def _IssueStressngCommand(vm, cpu_count, cpu_method):
  """Issues a stress-ng run command.
  Args:
    vm: The test VM to issue command to.
  Returns:
    stdout, stderr: the result of the command.
  """
  stdout = ''
  stderr = ''
  run_cmd_tokens = [stress_ng_build.STRESS_NG,
                    '--cpu %d' % cpu_count,
                    '-t %d' % FLAGS.intel_stress_ng_t,
                    '--metrics-brief',
                    '--cpu-method %s' % cpu_method]
  run_cmd = ' '.join(run_cmd_tokens)
  stdout, stderr = vm.RobustRemoteCommand(run_cmd)
  logging.info('Stress-ng output for %s:\nstdout is:\n%s\nstderr is\n%s',
               cpu_method, stdout, stderr)
  return stdout, stderr


def _GetMetricsFromLine(line):
  match = re.search(r'cpu\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)\s+([0-9]*\.?[0-9]+)', line)
  if match is None:
    logging.error("Parsing error -- regex doesn't match for string: %s", line)
  else:
    try:
      ops = int(match.group(1))
      real_time = float(match.group(2))
      usr_time = float(match.group(3))
      sys_time = float(match.group(4))
      cpu_speed = float(match.group(5))
    except ValueError:
      logging.error("Parsing error -- type conversion failed")
      raise
  return ops, real_time, usr_time, sys_time, cpu_speed


def _ParseStressngOutput(stress_ng_output, method, metadata, values_to_geomean_list):
  """Parses stress-ng output.
  Args:
    stress_ng_output: The output from stress-ng.

  Returns:
    results: array of samples
  """
  """ Sample Sysbench --cpu-method prime Output:
  stress-ng --cpu 0 --cpu-method prime -t 60 --metrics-brief
  stress-ng: info:  [15220] dispatching hogs: 72 cpu
  stress-ng: info:  [15220] cache allocate: default cache size: 46080K
  stress-ng: info:  [15220] successful run completed in 60.16s (1 min, 0.16 secs)
  stress-ng: info:  [15220] stressor      bogo ops real time  usr time  sys time   bogo ops/s   bogo ops/s
  stress-ng: info:  [15220]                          (secs)    (secs)    (secs)   (real time) (usr+sys time)
  stress-ng: info:  [15220] cpu              33868     60.06   4292.12      0.01       563.90         7.89
  """
  results = []
  stress_ng_output_io = StringIO(stress_ng_output)
  for line in stress_ng_output_io:
    sline = line.strip()
    if "] cpu" in sline:
      _, _, _, _, bogo_ops_s = _GetMetricsFromLine(sline)
      results.append(sample.Sample(method, bogo_ops_s, "bogo ops/s", metadata))
      values_to_geomean_list.append(bogo_ops_s)
  return results


def _GeoMeanOverflow(iterable):
  """Returns the geometric mean.

  See https://en.wikipedia.org/wiki/Geometric_mean#Relationship_with_logarithms

  Args:
    iterable: a list of positive floats to take the geometric mean of.

  Returns: The geometric mean of the list.
  """
  a = numpy.log(iterable)
  return numpy.exp(a.sum() / len(a))


def Run(benchmark_spec):
  """Run the stress-ng CPU benchmark and publish results.
  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  Returns:
    Results.
  """
  results = []
  vm = benchmark_spec.vms[0]
  for cpu_count in FLAGS.intel_stress_ng_cpu:
    values_to_geomean_list = []
    for method in FLAGS.intel_stress_ng_cpu_method:
      metadata = {}
      metadata['run_time'] = FLAGS.intel_stress_ng_t
      metadata['cpu_count'] = cpu_count
      stdout, stderr = _IssueStressngCommand(vm, cpu_count, method)
      partial_results = _ParseStressngOutput(stdout + stderr, method, metadata, values_to_geomean_list)
      results.extend(partial_results)
    if len(values_to_geomean_list) != len(FLAGS.intel_stress_ng_cpu_method):
      logging.warning("We don't have the expected number of results: {} != {}".format(len(values_to_geomean_list), len(FLAGS.intel_stress_ng_cpu_method)))
    geomean_metadata = {}
    geomean_metadata['run_time'] = FLAGS.intel_stress_ng_t
    geomean_metadata['cpu_count'] = cpu_count
    geomean_metadata['cpu_methods'] = str(FLAGS.intel_stress_ng_cpu_method)
    geomean_val = _GeoMeanOverflow(values_to_geomean_list)
    logging.info('geomean: %f', geomean_val)
    geomean_sample = sample.Sample(
        metric='STRESS_NG_CPU_GEOMEAN',
        value=geomean_val,
        unit='ops/sec',
        metadata=geomean_metadata)
    results.append(geomean_sample)
  return results


def Cleanup(benchmark_spec):
  """Clean up stress-ng benchmark related states.
  """
  pass
