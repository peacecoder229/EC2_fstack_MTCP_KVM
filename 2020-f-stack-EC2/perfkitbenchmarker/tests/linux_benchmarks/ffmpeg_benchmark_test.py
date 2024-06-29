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

import logging
import os
import sys
import tempfile
import tests.test_utils
import unittest
import uuid

from absl.flags import _exceptions
from absl import flags
from perfkitbenchmarker import errors
from perfkitbenchmarker import static_virtual_machine
from perfkitbenchmarker.linux_benchmarks import ffmpeg_benchmark
from perfkitbenchmarker.benchmark_ffmpeg_util import FfmpegWorkload
from tests.ignite_virtual_machine import Ubuntu2004BasedIgniteVirtualMachine

FLAGS = flags.FLAGS


class FfmpegBenchmarkTest(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    """Per-class initialization"""
    # Enable logging
    # Remove comments to view logging from commands.
    # cls.logger = logging.getLogger()
    # cls.logger.level = logging.DEBUG
    # cls.logger.addHandler(logging.StreamHandler(sys.stdout))

    # Set up the temporary directory for the results
    cls.temp_dir = tempfile.TemporaryDirectory()
    FLAGS.temp_dir = cls.temp_dir.name
    FLAGS.run_uri = str(uuid.uuid4())[-8:]

  @classmethod
  def tearDownClass(cls):
    """Per-class teardown"""
    cls.temp_dir.cleanup()

  def setUp(self):
    """
    Per-test initialization. Since FLAGS are global, reset the FFMPEG flags
    to their default values after every test. Otherwise, the changes will
    affect subsequent tests
    """
    ffmpeg_benchmark.ReinitializeFlags()

  def tearDown(self):
    """Per-test teardown"""
    pass

  def testCommandLineOptionDefaults(self):
    """Verify the default settings of all FFMPEG-specific command-line options"""
    self.assertEqual(FLAGS.ffmpeg_config_file, "ffmpeg_benchmark_tests.yaml")
    self.assertEqual(FLAGS.ffmpeg_run_tests, "")
    self.assertEqual(FLAGS.ffmpeg_videos_dir, "")
    self.assertEqual(FLAGS.ffmpeg_enable_numactl, 0)


  def testDisplayBenchmarkUsage(self):
    """
    Verify that the FFMPEG workload correctly displays usage information
    to the user, including command-line options and available tests
    """
    ffmpeg_benchmark.GetUsage(None)
    # TODO: verify that the output contains the right thing
    self.assertEqual(0, 0)

  def testInvalidCommandLineOption(self):
    """
    Verify that the FFMPEG workload detects invalid command line
    options and reports the errors to the user
    """
    with self.assertRaises(_exceptions.UnrecognizedFlagError):
      FLAGS(["program_name", "--some_invalid_command_line_option"])

  def testNonExistentConfigurationFile(self):
    """
    Verify that the FFMPEG workload correctly detects when the
    specified configuration file does not exist and provides an
    appropriate error message to the user
    """
    FLAGS.ffmpeg_run_tests = "x264-medium-1to1Live-1080p"
    FLAGS.ffmpeg_config_file = "this_file_does_not_exist"

    with self.assertRaises(errors.Config.InvalidValue):
      ffmpeg_benchmark.CheckPrerequisites(None)

  def testAtLeastOneTargetSpecified(self):
    """
    Verify that the FFMPEG workload detects that the user has
    provided at least one target test to run
    """
    FLAGS.ffmpeg_run_tests = ""

    with self.assertRaises(errors.Config.InvalidValue):
      ffmpeg_benchmark.CheckPrerequisites(None)

  def testNonExistentVideosDir(self):
    """
    Verify that the FFMPEG workload correctly detects if the specified
    videos directory does not exist and provides an appropriate error
    message to the user
    """
    FLAGS.ffmpeg_run_tests = "x264-medium-1to1Live-1080p"
    FLAGS.ffmpeg_videos_dir = "this_directory_does_not_exist"

    with self.assertRaises(errors.Config.InvalidValue):
      ffmpeg_benchmark.CheckPrerequisites(None)

  def testInvalidConfigurationFileSyntax(self):
    """
    Verify that the FFMPEG workload detects a syntactically invalid
    configuration file and reports the issue to the user
    """
    FLAGS.ffmpeg_run_tests = "x264-medium-1to1Live-1080p"
    FLAGS.ffmpeg_config_file = "invalid_config_file"

    with self.assertRaises(errors.Config.InvalidValue):
      ffmpeg_benchmark.CheckPrerequisites(None)

  def testInvalidTestTarget(self):
    """
    Verify that the FFMPEG workload detects that the user provided an
    invalid test target (one that doesn't exist in the configuration file)
    and reports the issue to the user
    """
    FLAGS.ffmpeg_run_tests = "this_test_not_in_config_file"

    with self.assertRaises(errors.Config.InvalidValue):
      ffmpeg_benchmark.CheckPrerequisites(None)

  def testPrepareAndCleanupUsingCachedVideos(self):
    """
    Test the Prepare and Cleanup phases of the FFMPEG workload. Because this
    requires a VM, we implement multiple tests from the test plan in this method.
    Each test from the test plan is called out in a comment
    """
    # Create a VM and benchmark spec to use for this test. Skip the test if there's a problem
    # with Ignite, such as it not being installed on the host
    try:
      benchmark_uid = ffmpeg_benchmark.BENCHMARK_NAME + '0'
      vm_name = benchmark_uid + '_vm'
      self.vm = Ubuntu2004BasedIgniteVirtualMachine(name=vm_name, cores=4, memory=16)
      self.spec = tests.test_utils.CreateBenchmarkSpec(ffmpeg_benchmark, self.vm, benchmark_uid)
    except Exception:
      self.skipTest("Ignite VM not created, skipping testPrepareAndCleanup (is Ignite installed?)")

    # Set user flags
    FLAGS.ffmpeg_run_tests = "x264-medium-1to1Live-1080p"
    # TODO: Need a legit network home for the cached video files
    FLAGS.ffmpeg_videos_dir = "/home/mjeronimo/videos"

    # Initialize an instance of the FFMPEG workload
    self.ffmpeg = FfmpegWorkload(self.spec)

    # Run its Prepare phase
    self.ffmpeg.Prepare()

    # RamDiskAvailable - Verify that the RAM disk has been set up properly and is of sufficient
    # size to hold the available videos
    ramdisk_path = self.ffmpeg.sut.GetRamDiskPath()
    with tempfile.NamedTemporaryFile(mode='w+t') as temp:
      str_to_write = "Hello, world!"
      temp.writelines(str_to_write)
      temp.flush()
      self.vm.PushFile(temp.name, ramdisk_path)
      stdout, stderr = self.vm.RemoteCommand("cat {}/{}".format(ramdisk_path, os.path.basename(temp.name)))
      self.assertEqual(stdout, str_to_write)

    # TODO:  AllCodecsBuiltAndAvailable - Verify that the Prepare phase builds all codecs correctly
    # and that they are ready for use (for example, no missing shared object dependencies)

    # TODO: VideoFilesNotCopiedDuringPrepare - When using the --ffmpeg_videos_dir command-line option,
    # (cached videos) the video files are not copied during Prepare

    # Run the Cleanup phase
    self.ffmpeg.Cleanup()

    # RamDiskRemoved - The RAM disk has been removed
    stdout, stderr = self.vm.RemoteCommand('test -f {} && echo "True" || echo "False"'.format(ramdisk_path))
    ramdisk_exists = stdout.rstrip()
    self.assertEqual(ramdisk_exists, "False")

    # TODO: CodecsRemoved - The FFMPEG binaries and intermediate directories have been removed

    # TODO: VideoFilesRemoved - Any downloaded (or copied) video files have been removed

    # Clean up the benchmark spec (and the VM)
    tests.test_utils.destroyBenchmarkSpec(self.spec)


if __name__ == '__main__':
  unittest.main()
