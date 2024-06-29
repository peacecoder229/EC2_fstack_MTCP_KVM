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

"""Tests for hibench_benchmark."""
import os
import unittest
import mock
import posixpath
from absl import flags

from perfkitbenchmarker import benchmark_spec
from perfkitbenchmarker import test_util
from perfkitbenchmarker import os_types
from perfkitbenchmarker import linux_benchmarks
from perfkitbenchmarker.linux_benchmarks import intel_hibench_benchmark
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker.configs import benchmark_config_spec
from perfkitbenchmarker.sample import Sample
from tests import pkb_common_test_case

FLAGS = flags.FLAGS


class HibenchBenchmarkTest(unittest.TestCase):

  def setUp(self):
    super(HibenchBenchmarkTest, self).setUp()
    self.vm = mock.Mock()
    self.BENCHMARK_NAME = 'intel_hibench'

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

  def testHiBenchGitArchive(self):
    hibench_git_archive = intel_hibench_benchmark.HIBENCH_GIT_ARCHIVE
    self.assertEqual(hibench_git_archive, "https://github.com/Intel-bigdata/HiBench/archive/HiBench-7.0.tar.gz")

  def testHiBenchPath(self):
    hibench_path = intel_hibench_benchmark.HIBENCH_PATH
    self.assertEqual(hibench_path, posixpath.join(INSTALL_DIR, "HiBench"))

  def testWorkloads(self):
    hibench_workloads = intel_hibench_benchmark.WORKLOADS
    self.assertEqual(hibench_workloads, ['kmeans', 'terasort'])

  def testFrameworks(self):
    hibench_frameworks = intel_hibench_benchmark.FRAMEWORKS
    self.assertEqual(hibench_frameworks, ['spark', 'hadoop'])

  def testConfigFile(self):
    hibench_config_file = intel_hibench_benchmark.CONFIG_FILE
    self.assertEqual(hibench_config_file, os.path.join('intel_hibench_benchmark', 'config.yml'))

  def testGeneratedConfigFile(self):
    generated_config_file = intel_hibench_benchmark.GENERATED_CONFIG_FILE
    self.assertEqual(generated_config_file, "generated_config.yml")

  def testDiskConfig(self):
    disk_config = intel_hibench_benchmark.DISK_CONFIG
    self.assertEqual(disk_config, {})

  def testDefaultCommandLineOptions(self):
    FLAGS = intel_hibench_benchmark.FLAGS
    self.assertEqual(FLAGS.intel_hibench_spark_version, "2.2.2")
    self.assertEqual(FLAGS.intel_hibench_scala_version, "2.11.0")
    self.assertEqual(FLAGS.intel_hibench_hadoop_version, "2.9.2")
    self.assertEqual(FLAGS.intel_hibench_framework, "spark")
    self.assertEqual(FLAGS.intel_hibench_workloads, ['kmeans'])
    self.assertEqual(FLAGS.intel_hibench_maven_version, "3.6.1")
    self.assertEqual(FLAGS.intel_hibench_hibench_scale_profile, None)
    self.assertEqual(FLAGS.intel_hibench_hibench_default_map_parallelism, None)
    self.assertEqual(FLAGS.intel_hibench_hibench_default_shuffle_parallelism, None)
    self.assertEqual(FLAGS.intel_hibench_hibench_spark_master, None)
    self.assertEqual(FLAGS.intel_hibench_hibench_yarn_executor_num, None)
    self.assertEqual(FLAGS.intel_hibench_hibench_yarn_executor_cores, None)
    self.assertEqual(FLAGS.intel_hibench_spark_executor_memory, None)
    self.assertEqual(FLAGS.intel_hibench_spark_driver_memory, None)
    self.assertEqual(FLAGS.intel_hibench_mountpoints, None)

  def testDefaultBenchmarkName(self):
    benchmark_name = intel_hibench_benchmark.BENCHMARK_NAME
    self.assertEqual(benchmark_name, "intel_hibench")

  def testDefaultBenchmarkConfig(self):
    benchmark_config = intel_hibench_benchmark.BENCHMARK_CONFIG
    expected_benchmark_config = """
intel_hibench:
  description: Build hibench workloads
  vm_groups:
    target:
      os_type: centos7
      disk_spec: *default_disk_300gb_high_speed
      disk_count: 6
      vm_count: 5
      vm_spec: *default_high_compute
  flags:
    ssh_reuse_connections: false
"""
    self.assertEqual(benchmark_config, expected_benchmark_config)

  def testFilesToSave(self):
    files_to_save = intel_hibench_benchmark.FILES_TO_SAVE
    expected_files_to_save = {
        "system_files": [
            "/etc/hosts",
        ],
        "user_files": [
        ]
    }
    self.assertEqual(files_to_save, expected_files_to_save)

  def testBenchmarkData(self):
    benchmark_data = intel_hibench_benchmark.BENCHMARK_DATA
    hibench_git_archive = intel_hibench_benchmark.HIBENCH_GIT_ARCHIVE
    expected_benchmark_data = {hibench_git_archive.split('/')[-1]:
                               '89b01f3ad90b758f24afd5ea2bee997c3d700ce9244b8a2b544acc462ab0e847'}
    self.assertEqual(benchmark_data, expected_benchmark_data)

  def testBenchmarkDataURL(self):
    benchmark_data_url = intel_hibench_benchmark.BENCHMARK_DATA_URL
    hibench_git_archive = intel_hibench_benchmark.HIBENCH_GIT_ARCHIVE
    expected_benchmark_data_url = {hibench_git_archive.split('/')[-1]: hibench_git_archive}
    expected_benchmark_data_url = {hibench_git_archive.split('/')[-1]: hibench_git_archive}
    self.assertEqual(benchmark_data_url, expected_benchmark_data_url)

  def testKmeansConfigPath(self):
    expected_path = posixpath.join(intel_hibench_benchmark.HIBENCH_PATH, "conf", "workloads", "ml")
    kmeans_config_path = intel_hibench_benchmark.KMEANS_CONFIG_PATH
    self.assertEqual(kmeans_config_path, expected_path)


if __name__ == '__main__':
  unittest.main()
