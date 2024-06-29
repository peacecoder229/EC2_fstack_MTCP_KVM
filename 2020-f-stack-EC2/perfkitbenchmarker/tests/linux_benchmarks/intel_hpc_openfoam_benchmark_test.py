
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
from perfkitbenchmarker.linux_benchmarks import intel_hpc_openfoam_benchmark
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import sample
from absl import flags

FLAGS = flags.FLAGS


class HPCOpenfoamBenchmarkTest(unittest.TestCase):

  def setUp(self):
    self.openfoam_name = intel_hpc_openfoam_benchmark.__name__

  @mock.patch('time.time', mock.MagicMock(return_value=1591827991.513602))
  def testParseResultSN(self):
    benchmark_spec = mock.MagicMock()
    benchmark_spec.vms = [mock.MagicMock()]
    FLAGS.intel_hpc_openfoam_nodes = 1
    samples = []
    with mock.patch(self.openfoam_name + '.intel_hpc_utils.GetVmCpuinfo'), \
        mock.patch(self.openfoam_name + '.intel_hpc_utils.RunSysinfo'), \
        mock.patch(self.openfoam_name + '.intel_hpc_utils.GetNodeArchives'):
       benchmark_spec.vms[0].RemoteCommand.side_effect = [('', ''),
                                                          (' SimpleFoam: ClockTime    = 2446    s', '')]
       samples = intel_hpc_openfoam_benchmark.Run(benchmark_spec)
       expected = [sample.Sample(metric='SimpleFoam', value=2446,
                                 unit='ClockTime(s)', metadata={'primary_sample': True}, timestamp=1591827991.513602)]
       self.assertEqual(expected, samples)

  @mock.patch('time.time', mock.MagicMock(return_value=1591827991.513602))
  def testParseResultSNAMD(self):
    benchmark_spec = mock.MagicMock()
    benchmark_spec.vms = [mock.MagicMock()]
    FLAGS.intel_hpc_openfoam_nodes = 1
    FLAGS.intel_hpc_openfoam_image_type = 'amd'
    samples = []
    with mock.patch(self.openfoam_name + '.intel_hpc_utils.GetVmCpuinfo'), \
        mock.patch(self.openfoam_name + '.intel_hpc_utils.RunSysinfo'), \
        mock.patch(self.openfoam_name + '.intel_hpc_utils.GetNodeArchives'):
       benchmark_spec.vms[0].RemoteCommand.side_effect = [('', ''),
                                                          (' SimpleFoam: ClockTime    = 2446    s', '')]
       samples = intel_hpc_openfoam_benchmark.Run(benchmark_spec)
       expected = [sample.Sample(metric='SimpleFoam', value=2446,
                                 unit='ClockTime(s)', metadata={'primary_sample': True}, timestamp=1591827991.513602)]
       self.assertEqual(expected, samples)

  @mock.patch('time.time', mock.MagicMock(return_value=1591827991.513602))
  def testParseResultMN(self):
    benchmark_spec = mock.MagicMock(vm_groups={'head_node': [mock.MagicMock()], 'compute_nodes': [mock.MagicMock()]})
    FLAGS.intel_hpc_openfoam_nodes = 2
    samples = []
    with mock.patch(self.openfoam_name + '.intel_hpc_utils.GetVmCpuinfo'), \
        mock.patch(self.openfoam_name + '.intel_hpc_utils.RunSysinfo'), \
        mock.patch(self.openfoam_name + '.intel_hpc_utils.GetNodeArchives'):
      benchmark_spec.vm_groups['head_node'][0].RemoteCommand.side_effect = [('', ''), ('', ''), ('', ''),
                                                                            ('', '')]
      benchmark_spec.vm_groups['compute_nodes'][0].RemoteCommand.side_effect = [('', ''),
                                                                                ('ClockTime    =   11    s', ''),
                                                                                ('ClockTime    =  603    s', '')]
      samples = intel_hpc_openfoam_benchmark.Run(benchmark_spec)
      expected = [sample.Sample(metric='potentialFoam', value=11,
                                unit='ClockTime(s)', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='SimpleFoam', value=603,
                                unit='ClockTime(s)', metadata={'primary_sample': True}, timestamp=1591827991.513602)]
      self.assertEqual(expected, samples)
