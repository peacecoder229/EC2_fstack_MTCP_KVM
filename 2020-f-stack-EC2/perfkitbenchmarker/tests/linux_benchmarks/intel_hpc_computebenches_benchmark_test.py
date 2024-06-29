
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
from perfkitbenchmarker.linux_benchmarks import intel_hpc_computebenches_benchmark
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import sample
from absl import flags

FLAGS = flags.FLAGS


class HPCComputeBenchesBenchmarkTest(unittest.TestCase):

  def setUp(self):
    self.computebenches_name = intel_hpc_computebenches_benchmark.__name__

  @mock.patch('time.time', mock.MagicMock(return_value=1591827991.513602))
  def testRunHPL(self):
    vm = mock.MagicMock()
    samples = []
    vm.RemoteCommand.side_effect = [('', ''), ('HPL: 2.69003e+03 GF/s', '')]
    intel_hpc_computebenches_benchmark._RunHPL(vm, 'computeBenches', 'hpl', samples)
    expected = [sample.Sample(metric='HPL', value=2.69003e+03,
                              unit='GF/s', metadata={'primary_sample': True}, timestamp=1591827991.513602)]
    self.assertEqual(expected, samples)

  @mock.patch('time.time', mock.MagicMock(return_value=1591827991.513602))
  def testRunHPCG(self):
    vm = mock.MagicMock()
    samples = []
    vm.RemoteCommand.side_effect = [('', ''), ('HPCG: 9.719784 GFLOP/s', '')]
    intel_hpc_computebenches_benchmark._RunHPCG(vm, 'computeBenches', 'hpcg', samples)
    expected = [sample.Sample(metric='HPCG', value=9.719784,
                              unit='GFLOP/s', metadata={}, timestamp=1591827991.513602)]
    self.assertEqual(expected, samples)

  @mock.patch('time.time', mock.MagicMock(return_value=1591827991.513602))
  def testRunGemms(self):
    vm = mock.MagicMock()
    samples = []
    vm.RemoteCommand.side_effect = [('', ''), (('SGEMM Performance N =  40000 :  5761.8654 GF\n' +
                                    'DGEMM Performance N =  40000 :  2951.8521 GF'), '')]
    intel_hpc_computebenches_benchmark._RunGemms(vm, 'computeBenches', 'gemms', samples)
    expected = [sample.Sample(metric='SGEMM', value=5761.8654,
                              unit='GF', metadata={}, timestamp=1591827991.513602),
                sample.Sample(metric='DGEMM', value=2951.8521,
                              unit='GF', metadata={}, timestamp=1591827991.513602)]
    self.assertEqual(expected, samples)
