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
from perfkitbenchmarker.linux_benchmarks import intel_hammerdb_benchmark
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import sample


class HammerDBBenchmarkTest(unittest.TestCase):

  def setUp(self):
    pass

  @mock.patch('perfkitbenchmarker.linux_benchmarks.intel_hammerdb_benchmark._GetMySQLResults')
  @mock.patch('time.time', mock.MagicMock(return_value=1591827991.513602))
  def testParseMySQLResult(self, getdbvm_mock):
    samples = []
    vm0 = mock.MagicMock()
    vm1 = mock.MagicMock()
    allResults = ('No of Virtual Users: 4, MySQL TPM: 210629, NOPM: 69616 <br>' +
                  'No of Virtual Users: 10, MySQL TPM: 436494, NOPM: 143491 <br>' +
                  'No of Virtual Users: 16, MySQL TPM: 581807, NOPM: 191563 <br>' +
                  'No of Virtual Users: 22, MySQL TPM: 603776, NOPM: 199285 <br>' +
                  'No of Virtual Users: 24, MySQL TPM: 608754, NOPM: 200732 <br>')
    vm1.RemoteCommand.side_effect = [(('Vuser 1:TEST RESULT : System achieved 69616 NOPM from 210629 MySQL TPM\n' +
                                       'Vuser 1:TEST RESULT : System achieved 143491 NOPM from 436494 MySQL TPM\n' +
                                       'Vuser 1:TEST RESULT : System achieved 191563 NOPM from 581807 MySQL TPM\n' +
                                       'Vuser 1:TEST RESULT : System achieved 199285 NOPM from 603776 MySQL TPM\n' +
                                       'Vuser 1:TEST RESULT : System achieved 200732 NOPM from 608754 MySQL TPM'), ''),
                                     (('Vuser 1:4 Active Virtual Users configured\n' +
                                       'Vuser 1:10 Active Virtual Users configured\n' +
                                       'Vuser 1:16 Active Virtual Users configured\n' +
                                       'Vuser 1:22 Active Virtual Users configured\n' +
                                       'Vuser 1:24 Active Virtual Users configured'), '')]

    samples = intel_hammerdb_benchmark._CollectMYSQLResults(vm0, vm1)
    expected = [sample.Sample(metric='Num of Virtual Users with Peak Value', value=24, unit='',
                              metadata={'List of all results': allResults}, timestamp=1591827991.513602),
                sample.Sample(metric='MySQL TPM', value=608754, unit='Transactions/Minute',
                              metadata={}, timestamp=1591827991.513602),
                sample.Sample(metric='NOPM', value=200732, unit='New Orders Per Minute',
                              metadata={'primary_sample': True}, timestamp=1591827991.513602)]
    self.assertEqual(expected, samples)

  @mock.patch('perfkitbenchmarker.linux_benchmarks.intel_hammerdb_benchmark._GetPGResults')
  @mock.patch('time.time', mock.MagicMock(return_value=1591827991.513602))
  def testParsePGResult(self, getdbvm_mock):
    samples = []
    vm0 = mock.MagicMock()
    vm1 = mock.MagicMock()
    allResults = ('No of Virtual Users: 4, PostgreSQL TPM: 210629, NOPM: 69616 <br>' +
                  'No of Virtual Users: 10, PostgreSQL TPM: 436494, NOPM: 143491 <br>' +
                  'No of Virtual Users: 16, PostgreSQL TPM: 581807, NOPM: 191563 <br>' +
                  'No of Virtual Users: 22, PostgreSQL TPM: 603776, NOPM: 199285 <br>' +
                  'No of Virtual Users: 24, PostgreSQL TPM: 608754, NOPM: 200732 <br>')
    vm1.RemoteCommand.side_effect = [(('Vuser 1:TEST RESULT : System achieved 69616 NOPM from 210629 PostgreSQL TPM\n' +
                                       'Vuser 1:TEST RESULT : System achieved 143491 NOPM from 436494 PostgreSQL TPM\n' +
                                       'Vuser 1:TEST RESULT : System achieved 191563 NOPM from 581807 PostgreSQL TPM\n' +
                                       'Vuser 1:TEST RESULT : System achieved 199285 NOPM from 603776 PostgreSQL TPM\n' +
                                       'Vuser 1:TEST RESULT : System achieved 200732 NOPM from 608754 PostgreSQL TPM'), ''),
                                     (('Vuser 1:4 Active Virtual Users configured\n' +
                                       'Vuser 1:10 Active Virtual Users configured\n' +
                                       'Vuser 1:16 Active Virtual Users configured\n' +
                                       'Vuser 1:22 Active Virtual Users configured\n' +
                                       'Vuser 1:24 Active Virtual Users configured'), '')]

    samples = intel_hammerdb_benchmark._CollectPGResults(vm0, vm1)
    expected = [sample.Sample(metric='Num of Virtual Users with Peak Value', value=24, unit='',
                              metadata={'List of all results': allResults}, timestamp=1591827991.513602),
                sample.Sample(metric='PostgreSQL TPM', value=608754, unit='Transactions/Minute',
                              metadata={}, timestamp=1591827991.513602),
                sample.Sample(metric='NOPM', value=200732, unit='New Orders Per Minute',
                              metadata={'primary_sample': True}, timestamp=1591827991.513602)]
    self.assertEqual(expected, samples)

  def testGetDefaultRangeForHammerUsers(self):
    vm = mock.Mock()
    vm.num_cpus = 96
    expected_hammer_users = "64 74 84 90 96 102 108 118 128 144 "
    actual_hammer_users = intel_hammerdb_benchmark._GetDefaultRangeForHammerUsers(vm)
    self.assertEqual(expected_hammer_users, actual_hammer_users)

  def testGetNumWarehouses(self):
    vm = mock.Mock()
    vm.num_cpus = 96
    expected_num_warehouses = 800
    actual_num_warehouses = intel_hammerdb_benchmark._GetNumWarehouses(vm)
    self.assertEqual(expected_num_warehouses, actual_num_warehouses)
    vm.num_cpus = 32
    expected_num_warehouses = 400
    actual_num_warehouses = intel_hammerdb_benchmark._GetNumWarehouses(vm)
    self.assertEqual(expected_num_warehouses, actual_num_warehouses)

  def testGetDBThreadsForBuildSchema(self):
    vm = mock.Mock()
    vm.num_cpus = 96
    expected_threads = 96
    actual_threads = intel_hammerdb_benchmark._GetDBThreadsForBuildSchema(vm)
    self.assertEqual(expected_threads, actual_threads)

  def tearDown(self):
    pass

if __name__ == '__main__':
  unittest.main()
