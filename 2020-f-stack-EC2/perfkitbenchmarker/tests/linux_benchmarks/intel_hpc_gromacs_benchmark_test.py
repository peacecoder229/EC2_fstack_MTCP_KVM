
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
from perfkitbenchmarker.linux_benchmarks import intel_hpc_gromacs_benchmark
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import sample
from absl import flags

FLAGS = flags.FLAGS


class HPCGromacsBenchmarkTest(unittest.TestCase):

  def setUp(self):
    self.gromacs_name = intel_hpc_gromacs_benchmark.__name__

  @mock.patch('time.time', mock.MagicMock(return_value=1591827991.513602))
  def testParseResultSN(self):
    benchmark_spec = mock.MagicMock()
    benchmark_spec.vms = [mock.MagicMock()]
    FLAGS.intel_hpc_gromacs_nodes = 1
    samples = []
    with mock.patch(self.gromacs_name + '.intel_hpc_utils.GetVmCpuinfo'), \
        mock.patch(self.gromacs_name + '.intel_hpc_utils.RunSysinfo'), \
        mock.patch(self.gromacs_name + '.intel_hpc_utils.GetNodeArchives'):
      benchmark_spec.vms[0].RemoteCommand.side_effect = [('', ''), ('ion_channel.pme (ion_channel.tpr) 56.414  ns/day', ''),
                                                                   ('lignocellulose_rf (lignocellulose-rf.tpr) 4.778  ns/day', ''),
                                                                   ('water_pme (topol_pme.tpr) 9.361  ns/day', ''),
                                                                   ('water_rf (topol_rf.tpr) 2.936  ns/day', '')]
      samples = intel_hpc_gromacs_benchmark.Run(benchmark_spec)
      expected = [sample.Sample(metric='ion_channel.pme (ion_channel.tpr)', value=56.414,
                                unit='ns/day', metadata={'primary_sample': True}, timestamp=1591827991.513602),
                  sample.Sample(metric='lignocellulose_rf (lignocellulose-rf.tpr)', value=4.778,
                                unit='ns/day', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='water_pme (topol_pme.tpr)', value=9.361,
                                unit='ns/day', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='water_rf (topol_rf.tpr)', value=2.936,
                                unit='ns/day', metadata={}, timestamp=1591827991.513602)]
      self.assertEqual(expected, samples)

  @mock.patch('time.time', mock.MagicMock(return_value=1591827991.513602))
  def testParseResultMN(self):
    benchmark_spec = mock.MagicMock(vm_groups={'head_node': [mock.MagicMock()], 'compute_nodes': [mock.MagicMock()]})
    FLAGS.intel_hpc_gromacs_nodes = 2
    with mock.patch(self.gromacs_name + '.intel_hpc_utils.GetVmCpuinfo'), \
        mock.patch(self.gromacs_name + '.intel_hpc_utils.RunSysinfo'), \
        mock.patch(self.gromacs_name + '.intel_hpc_utils.GetNodeArchives'):
      benchmark_spec.vm_groups['head_node'][0].RemoteCommand.side_effect = [('', ''), ('', ''), ('', ''),
                                                                            ('', '')]
      benchmark_spec.vm_groups['compute_nodes'][0].RemoteCommand.side_effect = [('ion_channel.tpr_NSTEPS_55000: 99.27 ns/day', ''),
                                                                                ('topol_pme.tpr_NSTEPS_10000: 17.73 ns/day', ''),
                                                                                ('topol_rf.tpr_NSTEPS_10000: 36.25 ns/day', ''),
                                                                                ('lignocellulose-rf.tpr_NSTEPS_8000: 11.29 ns/day', '')]
      samples = intel_hpc_gromacs_benchmark.Run(benchmark_spec)
      expected = [sample.Sample(metric='ion_channel.tpr_NSTEPS_55000', value=99.27,
                                unit='ns/day', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='topol_pme.tpr_NSTEPS_10000', value=17.73,
                                unit='ns/day', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='topol_rf.tpr_NSTEPS_10000', value=36.25,
                                unit='ns/day', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='lignocellulose-rf.tpr_NSTEPS_8000', value=11.29,
                                unit='ns/day', metadata={}, timestamp=1591827991.513602)]
      self.assertEqual(expected, samples)
