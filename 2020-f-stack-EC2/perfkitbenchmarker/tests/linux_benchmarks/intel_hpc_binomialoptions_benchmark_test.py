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
from perfkitbenchmarker.linux_benchmarks import intel_hpc_binomialoptions_benchmark
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import sample
from absl import flags

FLAGS = flags.FLAGS


class HPCBinomialOptionsBenchmarkTest(unittest.TestCase):

  def setUp(self):
    pass

  @mock.patch('time.time', mock.MagicMock(return_value=1591827991.513602))
  def testParseResult(self):
    benchmark_spec = mock.MagicMock()
    benchmark_spec.vms = [mock.MagicMock()]
    binomialoptions_name = intel_hpc_binomialoptions_benchmark.__name__
    samples = []
    with mock.patch(binomialoptions_name + '.intel_hpc_utils.RunSysinfo'), \
        mock.patch(binomialoptions_name + '.intel_hpc_utils.GetNodeArchives'):
      benchmark_spec.vms[0].RemoteCommand.side_effect = [('', ''), ('FOM in seconds : 124.80131873952067746004', '')]
      samples = intel_hpc_binomialoptions_benchmark.Run(benchmark_spec)
      expected = [sample.Sample(metric='FOM', value=124.80131873952067746004,
                                unit='seconds', metadata={'primary_sample': True}, timestamp=1591827991.513602)]
      self.assertEqual(expected, samples)
