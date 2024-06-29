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

"""The FFMPEG Benchmark"""

import os
import yaml

from perfkitbenchmarker import data
from perfkitbenchmarker import errors
from absl import flags
from perfkitbenchmarker.benchmark_ffmpeg_util import FfmpegWorkload

BENCHMARK_NAME = 'ffmpeg'
BENCHMARK_CONFIG = """
ffmpeg:
  description: Media transcoding (ffmpeg) benchmark
  vm_groups:
    default:
      os_type: ubuntu2004
      vm_spec: *default_dual_core
  flags:
"""

# Define the ffmpeg-specific command-line options
flags.DEFINE_string('ffmpeg_config_file', 'ffmpeg_benchmark_tests.yaml',
                    'The FFMPEG benchmark tests configuration file')

flags.DEFINE_string('ffmpeg_run_tests', '',
                    'A comma-separated list of tests to run')

flags.DEFINE_string('ffmpeg_videos_dir', '',
                    'The directory on the PKB host in which to find the input videos')

flags.DEFINE_integer('ffmpeg_enable_numactl', 0,
                     'Set it to 1 to enable numactl')

FLAGS = flags.FLAGS

# The single instance of the FfmpegWorkload class
ffmpeg_workload = None


def _InstanceWorkload(benchmark_spec):
  """Create the single instance of the FfmpegWorkload class if it isn't already created"""
  global ffmpeg_workload
  if ffmpeg_workload is None:
    ffmpeg_workload = FfmpegWorkload(benchmark_spec)


def ReinitializeFlags():
   FLAGS.ffmpeg_config_file = 'ffmpeg_benchmark_tests.yaml'
   FLAGS.ffmpeg_run_tests = ''
   FLAGS.ffmpeg_videos_dir = ''
   FLAGS.ffmpeg_enable_numactl = 0


def GetUsage(_):
  """Display command-line usage information for the this workload"""
  FfmpegWorkload.GetUsage()


def CheckPrerequisites(_):
  """Perform a semantic check of the requested command-line options"""
  if (FLAGS.ffmpeg_run_tests is None or FLAGS.ffmpeg_run_tests == '') and not FLAGS.get_benchmark_usage:
    raise errors.Config.InvalidValue('You must specify at least one test to run using --ffmpeg_run_tests')

  # A user-specified videos directory must exist
  if FLAGS.ffmpeg_videos_dir != '' and not os.path.isdir(FLAGS.ffmpeg_videos_dir):
    raise errors.Config.InvalidValue('The directory \'{}\' specified with --ffmpeg_videos_dir does not exist'.format(FLAGS.ffmpeg_videos_dir))

  # The config file command line option can't be set to the empty string
  if FLAGS.ffmpeg_config_file == "":
    raise errors.Config.InvalidValue('The FFMPEG workload requires a configuration file (you cannot set --ffmpeg_config_file=\"\")')

  # Make sure the file exists
  try:
    config_file = data.ResourcePath("ffmpeg/" + FLAGS.ffmpeg_config_file)
  except Exception:
    raise errors.Config.InvalidValue('The configuration file \'{}\' specified with --ffmpeg_config_file does not exist'.format(FLAGS.ffmpeg_config_file))

  # Then make sure it is a valid YAML file. If not load() will throw an exception
  with open(config_file) as file:
    config = None
    try:
      config = yaml.load(file, Loader=yaml.SafeLoader)
    except yaml.YAMLError:
      raise errors.Config.InvalidValue('Invalid YAML syntax in configuration file: \'{}\''.format(config_file))

    # Finally, make sure that the specified tests exist in the configuration file
    for target in FLAGS.ffmpeg_run_tests.split(','):
      if target not in config:
        raise errors.Config.InvalidValue("Specified test '{}' does not exist in configuration file: {}".format(target, config_file))


def GetConfig(user_config):
  """Get the workload configuration"""
  return FfmpegWorkload.GetConfig(user_config, BENCHMARK_NAME, BENCHMARK_CONFIG)


def Prepare(benchmark_spec):
  """Carry out the necessary steps to prepare this benchmark to run"""
  _InstanceWorkload(benchmark_spec)
  ffmpeg_workload.Prepare()


def Run(benchmark_spec):
  """Run the benchmark and generate the results"""
  _InstanceWorkload(benchmark_spec)
  return ffmpeg_workload.Run()


def Cleanup(benchmark_spec):
  """Clean up after running the benchmark"""
  _InstanceWorkload(benchmark_spec)
  return ffmpeg_workload.Cleanup()
