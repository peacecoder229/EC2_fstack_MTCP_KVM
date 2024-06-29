
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
from perfkitbenchmarker.linux_benchmarks import intel_hpc_lammps_benchmark
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import sample
from absl import flags

FLAGS = flags.FLAGS


class HPCLammpsBenchmarkTest(unittest.TestCase):

  def setUp(self):
    pass

  @mock.patch('time.time', mock.MagicMock(return_value=1591827991.513602))
  def testParseResultSN(self):
    benchmark_spec = mock.MagicMock()
    benchmark_spec.vms = [mock.MagicMock()]
    lammps_name = intel_hpc_lammps_benchmark.__name__
    FLAGS.intel_hpc_lammps_nodes = 1
    samples = []
    with mock.patch(lammps_name + '.intel_hpc_utils.GetVmCpuinfo'), \
        mock.patch(lammps_name + '.intel_hpc_utils.RunSysinfo'), \
        mock.patch(lammps_name + '.intel_hpc_utils.GetNodeArchives'):
      benchmark_spec.vms[0].RemoteCommand.side_effect = [('', ''), ('', ''), ('', ''),
                                                         ('Polyethelene (airebo) Performance: 5.033 timesteps/sec\n', ''),
                                                         ('Dissipative Particle Dynamics (dpd) '
                                                          'Performance: 38.514 timesteps/sec\n', ''),
                                                         ('Copper with Embedded Atom Method (eam) '
                                                          'Performance: 34.075 timesteps/sec\n', ''),
                                                         ('Liquid Crystal (lc) Performance: 7.378 timesteps/sec\n', ''),
                                                         ('Atomic fluid (lj) Performance: 76.983 timesteps/sec\n', ''),
                                                         ('Protein (rhodo) Performance: 6.418 timesteps/sec', ''),
                                                         ('Silicon with Stillinger-Weber (sw) '
                                                          'Performance: 55.715 timesteps/sec', ''),
                                                         ('Silicon with Tersoff (tersoff) '
                                                          'Performance: 29.555 timesteps/sec\n', ''),
                                                         ('Coarse-grain water (water) '
                                                          'Performance: 28.454 timesteps/sec', '')]
      samples = intel_hpc_lammps_benchmark.Run(benchmark_spec)
      expected = [sample.Sample(metric='Polyethelene (airebo)', value=5.033,
                                unit='timesteps/sec', metadata={'primary_sample': True}, timestamp=1591827991.513602),
                  sample.Sample(metric='Dissipative Particle Dynamics (dpd)', value=38.514,
                                unit='timesteps/sec', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='Copper with Embedded Atom Method (eam)', value=34.075,
                                unit='timesteps/sec', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='Liquid Crystal (lc)', value=7.378,
                                unit='timesteps/sec', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='Atomic fluid (lj)', value=76.983,
                                unit='timesteps/sec', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='Protein (rhodo)', value=6.418,
                                unit='timesteps/sec', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='Silicon with Stillinger-Weber (sw)', value=55.715,
                                unit='timesteps/sec', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='Silicon with Tersoff (tersoff)', value=29.555,
                                unit='timesteps/sec', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='Coarse-grain water (water)', value=28.454,
                                unit='timesteps/sec', metadata={}, timestamp=1591827991.513602)]
      self.assertEqual(expected, samples)

  @mock.patch('time.time', mock.MagicMock(return_value=1591827991.513602))
  def testParseResultMN(self):
    benchmark_spec = mock.MagicMock(vm_groups={'head_node': [mock.MagicMock()], 'compute_nodes': [mock.MagicMock()]})
    lammps_name = intel_hpc_lammps_benchmark.__name__
    FLAGS.intel_hpc_lammps_nodes = 2
    samples = []
    with mock.patch(lammps_name + '.intel_hpc_utils.GetVmCpuinfo'), \
        mock.patch(lammps_name + '.intel_hpc_utils.RunSysinfo'), \
        mock.patch(lammps_name + '.intel_hpc_utils.GetNodeArchives'):
      commandList = []
      for i in range(9):
        commandList.append(('', ''))
      benchmark_spec.vm_groups['head_node'][0].RemoteCommand.side_effect = commandList
      benchmark_spec.vm_groups['compute_nodes'][0].RemoteCommand.side_effect = [('', ''),
                                                                                ('Polyethelene (airebo) '
                                                                                 'Performance: 5.033 timesteps/sec\n', ''),
                                                                                ('Dissipative Particle Dynamics (dpd) '
                                                                                 'Performance: 38.514 timesteps/sec\n', ''),
                                                                                ('Copper with Embedded Atom Method (eam) '
                                                                                 'Performance: 34.075 timesteps/sec\n', ''),
                                                                                ('Liquid Crystal (lc) Performance: '
                                                                                 '7.378 timesteps/sec\n', ''),
                                                                                ('Atomic fluid (lj) Performance:'
                                                                                 ' 76.983 timesteps/sec\n', ''),
                                                                                ('Protein (rhodo) Performance: '
                                                                                 '6.418 timesteps/sec', ''),
                                                                                ('Silicon with Stillinger-Weber (sw) '
                                                                                 'Performance: 55.715 timesteps/sec', ''),
                                                                                ('Silicon with Tersoff (tersoff) '
                                                                                 'Performance: 29.555 timesteps/sec\n', ''),
                                                                                ('Coarse-grain water (water) '
                                                                                 'Performance: 28.454 timesteps/sec', '')]
      samples = intel_hpc_lammps_benchmark.Run(benchmark_spec)
      expected = [sample.Sample(metric='Polyethelene (airebo)', value=5.033,
                                unit='timesteps/sec', metadata={'primary_sample': True}, timestamp=1591827991.513602),
                  sample.Sample(metric='Dissipative Particle Dynamics (dpd)', value=38.514,
                                unit='timesteps/sec', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='Copper with Embedded Atom Method (eam)', value=34.075,
                                unit='timesteps/sec', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='Liquid Crystal (lc)', value=7.378,
                                unit='timesteps/sec', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='Atomic fluid (lj)', value=76.983,
                                unit='timesteps/sec', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='Protein (rhodo)', value=6.418,
                                unit='timesteps/sec', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='Silicon with Stillinger-Weber (sw)', value=55.715,
                                unit='timesteps/sec', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='Silicon with Tersoff (tersoff)', value=29.555,
                                unit='timesteps/sec', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='Coarse-grain water (water)', value=28.454,
                                unit='timesteps/sec', metadata={}, timestamp=1591827991.513602)]
      self.assertEqual(expected, samples)
