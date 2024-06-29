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

"""Runs Siege against PHP/WordPress by default on separate instances.

A running installation consists of:
  * php oss-performance harness.
  * Siege client.
  * Nginx/PHP/WordPress server.
  * MariaDB server.
"""

from perfkitbenchmarker import configs
from perfkitbenchmarker import data
from absl import flags
from perfkitbenchmarker import intel_php_utils
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker.linux_packages import intel_webtier_provisioning

FLAGS = flags.FLAGS

flags.DEFINE_integer('intel_wordpress5_mt_execution_count', 1,
                     'The number of times to run against chosen target.')
flags.DEFINE_integer('intel_wordpress5_mt_server_threads', None,
                     'The number of threads to execute.')
flags.DEFINE_integer('intel_wordpress5_mt_client_threads', None,
                     'The number of client threads to use to drive load.')

BENCHMARK_NAME = 'intel_wordpress5_mt'
BENCHMARK_CONFIG = """
intel_wordpress5_mt:
  description: >
      Run the oss-performance harness to drive Siege against
      Nginx, PHP or HHVM, WordPress using MariaDB on the back end.
      Will run PHP or HHVM on the server, MariaDB on the database
      and Siege on the client instance.
  vm_groups:
    server:
      os_type: ubuntu1604
      vm_spec: *default_dual_core
      vm_count: 1
    client:
      os_type: ubuntu1604
      vm_spec: *default_dual_core
      vm_count: 1
    database:
      os_type: ubuntu1604
      vm_spec: *default_dual_core
      vm_count: 1
"""

SERVER_GROUP = 'server'
CLIENT_GROUP = 'client'
DATABASE_GROUP = 'database'

# External files required to run workload
DATA_FILES = ['intel_wordpress5_mt_benchmark/config.yml']


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
  FLAGS.intel_wordpress_version = 'v5.2'
  intel_php_utils.Prepare(benchmark_spec, 'php', mt=True)


def Run(benchmark_spec):
  """Run Siege and gather the results.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.

  Returns:
    A list of sample.Sample objects.
  """
  FLAGS.intel_wordpress_version = 'v5.2'
  return intel_php_utils.Run(benchmark_spec,
                             'wordpress',
                             'php',
                             FLAGS.intel_wordpress5_mt_execution_count,
                             FLAGS.intel_wordpress5_mt_server_threads,
                             FLAGS.intel_wordpress5_mt_client_threads,
                             mt=True)


def Cleanup(benchmark_spec):
  """Cleanup.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  FLAGS.intel_wordpress_version = 'v5.2'
  intel_php_utils.Cleanup(benchmark_spec)
