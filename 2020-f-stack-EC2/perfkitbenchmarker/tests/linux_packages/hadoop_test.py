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

"""Tests for hadoop_package."""
import os
import unittest
import mock
import posixpath

from absl import flags
from perfkitbenchmarker import virtual_machine
from perfkitbenchmarker.linux_packages import hadoop
from perfkitbenchmarker.linux_packages import INSTALL_DIR

FLAGS = flags.FLAGS


class HadoopPackageTest(unittest.TestCase):

  def setUp(self):
    super(HadoopPackageTest, self).setUp()
    self.vm = mock.Mock()

  def assertCallArgsEqual(self, call_args_singles, mock_method):
    """Compare the list of single arguments to all mocked calls in mock_method.

    Mock calls can be tested like this:
      (('x',),) == call('x')
    As all the mocked method calls have one single argument (ie 'x') they need
    to be converted into the tuple of positional arguments tuple that mock
    expects.
    Args:
      call_args_singles: List of single arguments sent to the mock_method,
        ie ['x', 'y'] is for when mock_method was called twice: once with
        x and then with y.
      mock_method: Method that was mocked and called with call_args_singles.
    """
    # convert from ['a', 'b'] into [(('a',),), (('b',),)]
    expected = [((arg,),) for arg in call_args_singles]
    self.assertEqual(expected, mock_method.call_args_list)

  def assertRemoteCommandsEqual(self, expected_cmds):
    # tests the calls to vm.RemoteCommand(str)
    self.assertCallArgsEqual(expected_cmds, self.vm.RemoteCommand)

  def assertVmInstallCommandsEqual(self, expected_cmds):
    # tests the calls to vm.Install(str)
    self.assertCallArgsEqual(expected_cmds, self.vm.Install)

  def assertOnlyKnownMethodsCalled(self, *known_methods):
    # this test will fail if vm.foo() was called and "foo" was not in the
    # known methods
    found_methods = set()
    for mock_call in self.vm.mock_calls:
      found_methods.add(mock_call[0])
    self.assertEqual(set(known_methods), found_methods)

  def test_Install(self):
    hadoop._Install(self.vm)
    expected = "test -d {0} && rm -rf {0}; mkdir {0} && tar -C {0} --strip-component=1 -xzf {1}"
    HADOOP_DIR = hadoop.HADOOP_DIR
    FLAGS.hadoop_version = hadoop.FLAGS.hadoop_version
    hadoop_url = hadoop.HADOOP_URL.format(FLAGS.hadoop_version)
    hadoop_tar = hadoop_url.split('/')[-1]
    hadoop_remote_path = posixpath.join(INSTALL_DIR, hadoop_tar)
    self.assertRemoteCommandsEqual([expected.format(HADOOP_DIR, hadoop_remote_path)])
    self.assertVmInstallCommandsEqual(['openjdk', 'curl'])
    self.assertOnlyKnownMethodsCalled('RemoteCommand',
                                      'InstallPreprovisionedPackageData',
                                      'Install')

  def testConfigureAndStart(self):
    benchmark_spec = mock.MagicMock()
    benchmark_spec.vms = [mock.MagicMock(), mock.MagicMock()]
    with self.assertRaises(Exception) as context:
      hadoop.ConfigureAndStart(benchmark_spec.vms[0], benchmark_spec.vms[1], start_yarn=True)
      self.assertTrue('ConfigureAndAssert() Raises Exception' in context.exception)


if __name__ == '__main__':
  unittest.main()
