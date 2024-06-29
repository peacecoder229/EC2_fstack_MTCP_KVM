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
from absl import flags
from perfkitbenchmarker import temp_dir  # pylint: disable=unused-import # noqa

from unittest.mock import patch
from perfkitbenchmarker import test_util
from perfkitbenchmarker.linux_packages import intel_cassandra
from perfkitbenchmarker import errors

FLAGS = flags.FLAGS
FLAGS.mark_as_parsed()


class IntelCassandraStressBenchmarkTest(unittest.TestCase):

  def testInstallDatabaseFromAwsCli(self):
    vm = mock.MagicMock()
    vm.Install = mock.MagicMock()
    vm.RemoteCommandWithReturnCode = mock.MagicMock(return_value=('200', '', 0))
    self.assertTrue(intel_cassandra.TryS3(vm, 'test_bucket', 'test_s3_path', 'test_dest'))

  def testInstallDatabaseWithCurl(self):
    vm = mock.MagicMock()
    vm.Install = mock.MagicMock(side_effect=errors.VirtualMachine.RemoteCommandError)
    vm.RemoteCommandWithReturnCode = mock.MagicMock(return_value=('200', '', 0))
    self.assertTrue(intel_cassandra.TryS3(vm, 'test_bucket', 'test_s3_path', 'test_dest'))

  @mock.patch('perfkitbenchmarker.vm_util.IssueCommand')
  def testInstallDatabaseWithCurlFromPkbHost(self, mock_issue_command):
    mock_issue_command.return_value = ('"200"', '', 0)
    FLAGS.temp_dir = '/test'
    vm = mock.MagicMock()
    vm.Install = mock.MagicMock(side_effect=errors.VirtualMachine.RemoteCommandError)
    vm.RemoteCommandWithReturnCode = mock.MagicMock(side_effect=[('', '', 1), ('', '', 1)])
    vm.PushFile = mock.MagicMock()
    self.assertTrue(intel_cassandra.TryS3(vm, 'test_bucket', 'test_s3_path', 'test_dest'))
    vm.PushFile.assert_called()
