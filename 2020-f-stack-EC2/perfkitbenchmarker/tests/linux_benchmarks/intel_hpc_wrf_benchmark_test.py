
# Copyright 2020 PerfKitBenchmarker Authors. All rights reserved.
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
import os
import unittest
import mock
import posixpath

from unittest.mock import patch
from perfkitbenchmarker import test_util
from perfkitbenchmarker.linux_benchmarks import intel_hpc_wrf_benchmark
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import sample
from absl import flags

FLAGS = flags.FLAGS


class HPCWRFBenchmarkTest(unittest.TestCase):

  def setUp(self):
    self.wrf_name = intel_hpc_wrf_benchmark.__name__

  @mock.patch('time.time', mock.MagicMock(return_value=1591827991.513602))
  def testParseResultSN(self):
    benchmark_spec = mock.MagicMock()
    benchmark_spec.vms = [mock.MagicMock()]
    FLAGS.intel_hpc_wrf_nodes = 1
    samples = []
    with mock.patch(self.wrf_name + '.intel_hpc_utils.RunSysinfo'), \
        mock.patch(self.wrf_name + '.intel_hpc_utils.GetNodeArchives'):
       benchmark_spec.vms[0].RemoteCommand.side_effect = [('', ''),
                                                          ('Figure of merit :      mean:         3.274770 s/timestep', '')]
       samples = intel_hpc_wrf_benchmark.Run(benchmark_spec)
       expected = [sample.Sample(metric='Figure of merit :      mean:', value=3.274770,
                                 unit='s/timestep', metadata={'primary_sample': True}, timestamp=1591827991.513602)]
       self.assertEqual(expected, samples)

  @mock.patch('time.time', mock.MagicMock(return_value=1591827991.513602))
  def testParseResultMN(self):
    benchmark_spec = mock.MagicMock(vm_groups={'head_node': [mock.MagicMock()], 'compute_nodes': [mock.MagicMock()]})
    FLAGS.intel_hpc_wrf_nodes = 2
    samples = []
    with mock.patch(self.wrf_name + '.intel_hpc_utils.GetVmCpuinfo'), \
        mock.patch(self.wrf_name + '.intel_hpc_utils.RunSysinfo'), \
        mock.patch(self.wrf_name + '.intel_hpc_utils.GetNodeArchives'):
      benchmark_spec.vm_groups['head_node'][0].RemoteCommand.side_effect = [('', '')]
      benchmark_spec.vm_groups['compute_nodes'][0].RemoteCommand.side_effect = [('', ''),
                                                                                ('Figure of merit :      mean:         3.274770 s/timestep', '')]
      samples = intel_hpc_wrf_benchmark.Run(benchmark_spec)
      expected = [sample.Sample(metric='Figure of merit :      mean:', value=3.274770,
                                unit='s/timestep', metadata={'primary_sample': True}, timestamp=1591827991.513602)]
      self.assertEqual(expected, samples)
