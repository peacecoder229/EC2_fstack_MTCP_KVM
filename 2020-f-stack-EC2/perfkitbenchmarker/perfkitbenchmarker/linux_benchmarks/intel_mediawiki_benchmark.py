# Copyright 2015 PerfKitBenchmarker Authors. All rights reserved.
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

"""Runs Siege against PHP/MediaWiki.

A running installation consists of:
  * HHVM oss-performance harness.
  * Siege client.
  * Nginx/PHP/MediaWiki.
  * MariaDB server.
"""

from perfkitbenchmarker import configs
from perfkitbenchmarker import data
from absl import flags
from perfkitbenchmarker import intel_php_utils
from perfkitbenchmarker.linux_packages import INSTALL_DIR

FLAGS = flags.FLAGS

flags.DEFINE_integer('intel_mediawiki_execution_count', 1,
                     'The number of times to run against chosen target.')
flags.DEFINE_integer('intel_mediawiki_server_threads', None,
                     'The number of threads to execute.')
flags.DEFINE_integer('intel_mediawiki_client_threads', None,
                     'The number of client threads to use to drive load.')

BENCHMARK_NAME = 'intel_mediawiki'
BENCHMARK_CONFIG = """
intel_mediawiki:
  description: >
      Run the oss-performance harness to drive Siege against
      Nginx, PHP or HHVM, MediaWiki using MariaDB on the back end.
  vm_groups:
    target:
      os_type: ubuntu1604
      vm_spec: *default_dual_core
"""

# External files required to run workload
DATA_FILES = ['intel_mediawiki_benchmark/config.yml']


def GetConfig(user_config):
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
  return config


def CheckPrerequisites(config):
  """Verifies that the required resources are present.

  Raises:
    perfkitbenchmarker.data.ResourceNotFound: On missing resource.
  """
  for resource in DATA_FILES:
    data.ResourcePath(resource)


def Prepare(benchmark_spec):
  """Prepare the virtual machines to run.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  intel_php_utils.Prepare(benchmark_spec, 'php', mt=False)


def Run(benchmark_spec):
  """Run Siege and gather the results.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.

  Returns:
    A list of sample.Sample objects.
  """
  return intel_php_utils.Run(benchmark_spec,
                             'mediawiki',
                             'php',
                             FLAGS.intel_mediawiki_execution_count,
                             FLAGS.intel_mediawiki_server_threads,
                             FLAGS.intel_mediawiki_client_threads,
                             mt=False)


def Cleanup(benchmark_spec):
  """Cleanup.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  pass