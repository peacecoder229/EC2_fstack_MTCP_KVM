
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
from perfkitbenchmarker.linux_benchmarks import intel_hpc_namd_benchmark
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import sample
from absl import flags

FLAGS = flags.FLAGS


class HPCNAMDBenchmarkTest(unittest.TestCase):

  def setUp(self):
    self.namd_name = intel_hpc_namd_benchmark.__name__
    self.cpuinfo = mock.MagicMock()
    self.cpuinfo.num_cores = 36
    self.cpuinfo.threads_per_core = 2
    self.apoaList = (('apoa1-36cores-2ppn-4nodes-:  32.9863\n' +
                      'apoa1-36cores-2ppn-4nodes-ht:  23.7565\n' +
                      'apoa1-36cores-4ppn-4nodes-:  39.4566\n ' +
                      'apoa1-36cores-4ppn-4nodes-ht:  24.5734\n' +
                      'apoa1-36cores-8ppn-4nodes-:  32.7714\n' +
                      'apoa1-36cores-8ppn-4nodes-ht:  19.962\n' +
                      'apoa1-72cores-2ppn-4nodes-:  10.8054\n' +
                      'apoa1-72cores-4ppn-4nodes-:  6.9941\n' +
                      'apoa1-72cores-8ppn-4nodes-:  35.47\n', ''))
    self.stmvList = (('stmv-36cores-2ppn-4nodes-:  3.5269\n' +
                      'stmv-36cores-2ppn-4nodes-ht:  2.44142\n' +
                      'stmv-36cores-4ppn-4nodes-:  3.78615\n' +
                      'stmv-36cores-4ppn-4nodes-ht:  2.34242\n' +
                      'stmv-36cores-8ppn-4nodes-:  2.89792\n' +
                      'stmv-36cores-8ppn-4nodes-ht:  1.83439\n' +
                      'stmv-72cores-2ppn-4nodes-:  2.90132\n' +
                      'stmv-72cores-4ppn-4nodes-:  2.32375\n' +
                      'stmv-72cores-8ppn-4nodes-:  4.51115\n', ''))
    self.apoa1_npstr_cudaList = (('apoa1_nptsr_cuda-24cores-1ppn-1nodes-:  7.3556\n' +
                                  'apoa1_nptsr_cuda-24cores-1ppn-1nodes-ht:        4.83238\n' +
                                  'apoa1_nptsr_cuda-24cores-2ppn-1nodes-:  7.07849\n' +
                                  'apoa1_nptsr_cuda-24cores-2ppn-1nodes-ht:        4.55638\n' +
                                  'apoa1_nptsr_cuda-24cores-4ppn-1nodes-:  6.46345\n' +
                                  'apoa1_nptsr_cuda-24cores-4ppn-1nodes-ht:        4.16887\n' +
                                  'apoa1_nptsr_cuda-24cores-8ppn-1nodes-:  5.30142\n' +
                                  'apoa1_nptsr_cuda-24cores-8ppn-1nodes-ht:        3.39498\n' +
                                  'apoa1_nptsr_cuda-48cores-1ppn-1nodes-:  9.20985\n' +
                                  'apoa1_nptsr_cuda-48cores-2ppn-1nodes-:  8.92074\n' +
                                  'apoa1_nptsr_cuda-48cores-4ppn-1nodes-:  8.60003\n' +
                                  'apoa1_nptsr_cuda-48cores-8ppn-1nodes-:  7.82648\n', ''))
    self.stmv_npstr_cudaList = (('stmv_nptsr_cuda-24cores-1ppn-1nodes-:   0.647632\n' +
                                 'stmv_nptsr_cuda-24cores-1ppn-1nodes-ht:         0.424532\n' +
                                 'stmv_nptsr_cuda-24cores-2ppn-1nodes-:   0.619305\n' +
                                 'stmv_nptsr_cuda-24cores-2ppn-1nodes-ht:         0.397301\n' +
                                 'stmv_nptsr_cuda-24cores-4ppn-1nodes-:   0.566009\n' +
                                 'stmv_nptsr_cuda-24cores-4ppn-1nodes-ht:         0.365521\n' +
                                 'stmv_nptsr_cuda-24cores-8ppn-1nodes-:   0.46039\n' +
                                 'stmv_nptsr_cuda-24cores-8ppn-1nodes-ht:         0.295485\n' +
                                 'stmv_nptsr_cuda-48cores-1ppn-1nodes-:   0.83068\n' +
                                 'stmv_nptsr_cuda-48cores-2ppn-1nodes-:   0.804389\n' +
                                 'stmv_nptsr_cuda-48cores-4ppn-1nodes-:   0.772629\n' +
                                 'stmv_nptsr_cuda-48cores-8ppn-1nodes-:   0.705902\n', ''))

  @mock.patch('time.time', mock.MagicMock(return_value=1591827991.513602))
  def testParseResultIASN(self):
    benchmark_spec = mock.MagicMock()
    benchmark_spec.vms = [mock.MagicMock()]
    FLAGS.intel_hpc_namd_nodes = 1
    FLAGS.intel_hpc_namd_image_type = 'avx512'
    samples = []
    with mock.patch(self.namd_name + '.intel_hpc_utils.GetVmCpuinfo', return_value=self.cpuinfo), \
        mock.patch(self.namd_name + '.intel_hpc_utils.RunSysinfo'), \
        mock.patch(self.namd_name + '.intel_hpc_utils.GetNodeArchives'):
      benchmark_spec.vms[0].RemoteCommand.side_effect = [('', ''), ('FOM for APOA1 in ns/days:\n' + '15.0391\n', ''),
                                                         ('FOM for STMV in ns/days:\n' + '1.32213\n', ''),
                                                         ('FOM for APOA1_2fs in ns/days:\n' + '9.209850\n', ''),
                                                         ('FOM for STMV_2fs in ns/days:\n' + '0.830680\n', '')]
      samples = intel_hpc_namd_benchmark.Run(benchmark_spec)
      expected = [sample.Sample(metric='FOM for APOA1', value=15.0391,
                                unit='ns/days', metadata={'primary_sample': True}, timestamp=1591827991.513602),
                  sample.Sample(metric='FOM for STMV', value=1.32213,
                                unit='ns/days', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='FOM for APOA1_2fs', value=9.209850,
                                unit='ns/days', metadata={}, timestamp=1591827991.513602),
                  sample.Sample(metric='FOM for STMV_2fs', value=0.830680,
                                unit='ns/days', metadata={}, timestamp=1591827991.513602)]
      self.assertEqual(expected, samples)

  @mock.patch('time.time', mock.MagicMock(return_value=1591827991.513602))
  def testParseResultAMDSN(self):
    benchmark_spec = mock.MagicMock()
    benchmark_spec.vms = [mock.MagicMock()]
    FLAGS.intel_hpc_namd_nodes = 1
    FLAGS.intel_hpc_namd_image_type = 'amd'
    samples = []
    with mock.patch(self.namd_name + '.intel_hpc_utils.GetVmCpuinfo', return_value=self.cpuinfo), \
        mock.patch(self.namd_name + '.intel_hpc_utils.RunSysinfo'), \
        mock.patch(self.namd_name + '.intel_hpc_utils.GetNodeArchives'):
       commandList = []
       for i in range(49):
         commandList.append(('', ''))
       commandList.append(self.apoaList)
       commandList.append(self.apoa1_npstr_cudaList)
       commandList.append(self.stmvList)
       commandList.append(self.stmv_npstr_cudaList)
       benchmark_spec.vms[0].RemoteCommand.side_effect = commandList
       samples = intel_hpc_namd_benchmark.Run(benchmark_spec)
       expected = [sample.Sample(metric='FOM for APOA1', value=39.4566,
                                 unit='ns/days', metadata={'primary_sample': True}, timestamp=1591827991.513602),
                   sample.Sample(metric='FOM for APOA1_NPTSR_CUDA', value=9.20985,
                                 unit='ns/days', metadata={}, timestamp=1591827991.513602),
                   sample.Sample(metric='FOM for STMV', value=4.51115,
                                 unit='ns/days', metadata={}, timestamp=1591827991.513602),
                   sample.Sample(metric='FOM for STMV_NPTSR_CUDA', value=0.830680,
                                 unit='ns/days', metadata={}, timestamp=1591827991.513602)]
       self.assertEqual(expected, samples)

  @mock.patch('time.time', mock.MagicMock(return_value=1591827991.513602))
  def testParseResultMN(self):
    benchmark_spec = mock.MagicMock(vm_groups={'head_node': [mock.MagicMock()], 'compute_nodes': [mock.MagicMock()]})
    FLAGS.intel_hpc_namd_nodes = 2
    samples = []
    with mock.patch(self.namd_name + '.intel_hpc_utils.GetVmCpuinfo', return_value=self.cpuinfo), \
        mock.patch(self.namd_name + '.intel_hpc_utils.RunSysinfo'), \
        mock.patch(self.namd_name + '.intel_hpc_utils.GetNodeArchives'):
       commandList = []
       for i in range(36):
         commandList.append(('', ''))
       benchmark_spec.vm_groups['head_node'][0].RemoteCommand.side_effect = commandList
       benchmark_spec.vm_groups['compute_nodes'][0].RemoteCommand.side_effect = [('', ''), self.apoaList, self.apoa1_npstr_cudaList, self.stmvList, self.stmv_npstr_cudaList]
       samples = intel_hpc_namd_benchmark.Run(benchmark_spec)
       expected = [sample.Sample(metric='FOM for APOA1', value=39.4566,
                                 unit='ns/days', metadata={'primary_sample': True}, timestamp=1591827991.513602),
                   sample.Sample(metric='FOM for APOA1_NPTSR_CUDA', value=9.20985,
                                 unit='ns/days', metadata={}, timestamp=1591827991.513602),
                   sample.Sample(metric='FOM for STMV', value=4.51115,
                                 unit='ns/days', metadata={}, timestamp=1591827991.513602),
                   sample.Sample(metric='FOM for STMV_NPTSR_CUDA', value=0.830680,
                                 unit='ns/days', metadata={}, timestamp=1591827991.513602)]
       self.assertEqual(expected, samples)
