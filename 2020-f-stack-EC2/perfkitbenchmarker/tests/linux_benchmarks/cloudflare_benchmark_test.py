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

import tempfile
import unittest
import uuid

from absl.flags import _exceptions
from absl import flags

from perfkitbenchmarker import errors
from perfkitbenchmarker.linux_benchmarks import cloudflare_benchmark
from tests.ignite_virtual_machine import Ubuntu2004BasedIgniteVirtualMachine

FLAGS = flags.FLAGS


class CloudflareBenchmarkTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        FLAGS.temp_dir = cls.temp_dir.name
        FLAGS.run_uri = str(uuid.uuid4())[-8:]

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def setUp(self):
        cloudflare_benchmark.ReinitializeFlags()

    def tearDown(self):
        pass

    def testCommandLineOptionDefaults(self):
        self.assertEqual(FLAGS.cloudflare_config_file, "cloudflare_benchmark_test.yaml")
        self.assertEqual(FLAGS.cloudflare_run_tests, "go")
        self.assertEqual(FLAGS.cloudflare_run_on_threads, [1])

    def testInvalidCommandLineOption(self):
        with self.assertRaises(_exceptions.UnrecognizedFlagError):
            FLAGS(["program_name", "--some_invalid_command_line_option"])

    def testNonExistentConfigurationFile(self):
        FLAGS.cloudflare_run_tests = "go"
        FLAGS.cloudflare_config_file = "this_file_does_not_exist"

        with self.assertRaises(errors.Config.InvalidValue):
            cloudflare_benchmark.CheckPrerequisites(None)

    def testConfigurationFileExists(self):
        FLAGS.cloudflare_run_tests = "whatever"
        FLAGS.cloudflare_config_file = "cloudflare_benchmark_tests.yaml"

        self.assertIsNone(cloudflare_benchmark.CheckPrerequisites(None))

    def testAtLeastOneTargetSpecified(self):
        with self.assertRaises(flags._exceptions.IllegalFlagValueError):
            FLAGS.cloudflare_run_tests = ""


if __name__ == '__main__':
    unittest.main()
