# Copyright 2014 PerfKitBenchmarker Authors. All rights reserved.
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

"""Runs cassandra.
"""

import functools
import locale
import logging
import posixpath
import threading
import os

from perfkitbenchmarker import configs
from perfkitbenchmarker import data
from absl import flags
from perfkitbenchmarker import regex_util
from perfkitbenchmarker import sample
from perfkitbenchmarker import vm_util
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker.linux_packages import intel_cassandra

PREPROVISIONED_DATA_FILENAMES = ['cassandra-1.0.0.tgz', 'cassandra_100g_i1-1.0.0.tgz']

FLAGS = flags.FLAGS

flags.DEFINE_integer('intel_cassandra_xms', None, 'Min heap size in gigabytes. '
                                                  'No flag: auto adjust for system size')
flags.DEFINE_integer('intel_cassandra_xmx', None, 'Max heap size in gigabytes. '
                                                  'No flag: auto adjust for system size')
flags.DEFINE_string('intel_cassandra_gctype', '+UseG1GC', 'type of GC algorithm')
flags.DEFINE_enum('intel_cassandra_db', 'cassandra-1.0.0.tgz', PREPROVISIONED_DATA_FILENAMES,
                  'Preprovisioned database that will be pulled from S3')
flags.DEFINE_integer('intel_cassandra_write_percent', 30, 'percentage of writes during cassandra run')
flags.DEFINE_integer('intel_cassandra_read_percent', 70, 'percentage of reads during cassandra run')
flags.DEFINE_integer('intel_cassandra_num_db_entries', 100, 'number of entries into the database')
flags.DEFINE_integer('intel_cassandra_rate_threads', 0, 'number of client threads, 0: adjust to vCPUs')
flags.DEFINE_integer('intel_cassandra_chunk_length_in_kb', 64, 'chunk length to use in cql file')
flags.DEFINE_string('intel_cassandra_run_duration', '20m', 'duration for which cassandra worklaod should be run')
flags.DEFINE_string('intel_cassandra_xss', '256k', 'Per thread stack size')
flags.DEFINE_string('intel_cassandra_static_db', None, 'path to a database that already exists on the '
                                                       'database SUT and is untarred')

CASSANDRA_VER = "1.0.1"
CASSANDRA_DIR = posixpath.join(INSTALL_DIR, 'apache-cassandra')
CASSANDRA_CQL = "cqlstress-insanity-example.yaml"
CASSANDRA_JVM_FILE = "jvm.options"
CASSANDRA_YAML = "cassandra.yaml"
CASSANDRA_RUN_TEMPLATE = 'intel_cassandra/run.sh.j2'

BENCHMARK_NAME = 'intel_cassandra_stress'
BENCHMARK_CONFIG = """
intel_cassandra_stress:
  description: Benchmark Cassandra using cassandra-stress-Intel version
  vm_groups:
    workers:
      os_type: rhel7
      vm_spec: *default_dual_core
      disk_spec: *default_500_gb
      vm_count: 1
    client:
      os_type: rhel7
      vm_spec: *default_dual_core
"""


SERVER_GROUP = 'workers'
CLIENT_GROUP = 'client'

RESULTS_METRICS = {
    'Op rate': {
        "aggregation": "sum",
        "meaning": "Number of operations per second performed during the run."
    },
    'Latency mean': {
        "aggregation": "avg",
        "meaning": "Average latency in milliseconds for each operation during that run."
    },
    'Latency 99th percentile': {
        "aggregation": "avg",
        "meaning": "99% of the time the latency was less than the number displayed in the column."
    }
}


def GetConfig(user_config):
  return configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)


def Prepare(benchmark_spec):
  """Install Cassandra and Java on target vms.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  benchmark_spec.workload_name = "Intel Cassandra Stress"
  benchmark_spec.software_config_metadata = {
      "cassandra_version": "3.11",
      "openjdk_version": FLAGS.openjdk_version}
  benchmark_spec.tunable_parameters_metadata = {
      "rate_threads": FLAGS.intel_cassandra_rate_threads,
      'xmx': FLAGS.intel_cassandra_xmx}
  benchmark_spec.sut_vm_group = SERVER_GROUP
  benchmark_spec.always_call_cleanup = True
  benchmark_spec.db_checksum = None
  vm_dict = benchmark_spec.vm_groups
  server_vms = vm_dict[SERVER_GROUP]
  client_vms = vm_dict[CLIENT_GROUP]

  if FLAGS.intel_cassandra_instances > len(server_vms[0].additional_private_ip_addresses) + 1:
    raise Exception("At least one Cassandra instance do not have an IP to be assigned. Stopping Everything!")

  logging.info('Authorizing loader[0] permission to access all other vms.')
  client_vms[0].AuthenticateVm()

  logging.info('Installing data files and Java on all vms.')

  # installing on server and clients
  vm_util.RunThreaded(lambda vm: vm.Install('intel_cassandra'), server_vms)
  vm_util.RunThreaded(lambda vm: vm.Install('intel_cassandra'), client_vms)

  logging.info('Configuring data files and Java on all vms.')

  # configuring server
  configure = functools.partial(intel_cassandra.ConfigureServer, server_vms=server_vms)
  vm_util.RunThreaded(configure, server_vms)

  # configuring client
  configure = functools.partial(intel_cassandra.ConfigureClient, client_vms=client_vms)
  vm_util.RunThreaded(configure, client_vms)

  # pulling data from S3
  if not intel_cassandra.StaticDatabase(server_vms):
    logging.info('Pulling database from AWS S3')
    cassandra_S3_tar = FLAGS.intel_cassandra_db
    benchmark_spec.db_checksum = intel_cassandra.InstallDatabase(cassandra_S3_tar, server_vms)
  else:
    logging.info('Using static database')
    intel_cassandra.CreateStaticDatabases(server_vms)

  # starting cassandra server
  logging.info('Starting cassandra server')
  intel_cassandra.StartCluster(server_vms)


def CollectResults(benchmark_spec):
  """Collect and parse test results.

  Args:
    benchmark_spec: The benchmark specification. Contains all data
        that is required to run the benchmark.
  """
  logging.info('Gathering results.')
  locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
  vm_dict = benchmark_spec.vm_groups
  server_vms = vm_dict[SERVER_GROUP]
  client_vms = vm_dict[CLIENT_GROUP]

  metric_dict = {}
  for metric in RESULTS_METRICS.keys():
    metric_dict[metric] = {
        "values": [],
        "unit": ""
    }

  results = []

  for instance in range(int(FLAGS.intel_cassandra_instances)):
    cassandra_path = CASSANDRA_DIR + str(instance)
    local_dir = posixpath.join(vm_util.GetTempDir(), 'run_data', str(instance))
    cmd = ['mkdir', '-p', local_dir]
    vm_util.IssueCommand(cmd)
    server_files = ['{0}/logs'.format(cassandra_path),
                    '{0}/conf/{1}'.format(cassandra_path, CASSANDRA_YAML),
                    '{0}/conf/{1}'.format(cassandra_path, CASSANDRA_JVM_FILE)]

    client_files = ['{0}/tools/{1}'.format(cassandra_path, CASSANDRA_CQL),
                    '{0}/run.sh'.format(cassandra_path),
                    '{0}/run.out'.format(cassandra_path),
                    '{0}/cass.html'.format(cassandra_path)]
    for server_file in server_files:
      vm_util.RunThreaded(lambda vm: vm.PullFile(local_dir, server_file), server_vms)
    for client_file in client_files:
      vm_util.RunThreaded(lambda vm: vm.PullFile(local_dir, client_file), client_vms)

    result_file = posixpath.join(cassandra_path, 'run.out')
    resp, _ = client_vms[0].RemoteCommand('tail -n 20 ' + result_file)
    logging.info(resp)
    for metric in RESULTS_METRICS.keys():
      value = regex_util.ExtractGroup(r'%s\s+\:\s+(.*?)\s.*' % metric, resp).replace(',', '')
      unit = regex_util.ExtractGroup(r'%s\s+\:\s+.*?\s+(.*?)\s.*' % metric, resp)
      results.append(sample.Sample(metric + " Cassandra {0}".format(instance), value, unit, {}))

      metric_dict[metric]["values"].append(locale.atof(value))
      metric_dict[metric]["unit"] = unit
  for metric in RESULTS_METRICS.keys():
    if RESULTS_METRICS[metric]["aggregation"] == "sum":
      metadata = {}
      if metric == 'Op rate':
        metadata = {'primary_sample': True}
      s = sample.Sample("Total " + metric, sum(metric_dict[metric]["values"]), metric_dict[metric]["unit"], metadata)
      results.append(s)
    if RESULTS_METRICS[metric]["aggregation"] == "avg":
      results.append(sample.Sample("Average " + metric, sum(metric_dict[metric]["values"]) / float(len(metric_dict[metric]["values"])), metric_dict[metric]["unit"], {}))

  return results


def _GenerateMetadataFromFlags(benchmark_spec):
  vm_dict = benchmark_spec.vm_groups
  server_vms = vm_dict[SERVER_GROUP]
  metadata = {}
  if intel_cassandra.StaticDatabase(server_vms):
    db = FLAGS.intel_cassandra_static_db
  else:
    db = FLAGS.intel_cassandra_db
  xms, xmx = intel_cassandra.GetHeapConfiguration(server_vms[0])
  benchmark_spec.tunable_parameters_metadata = {
      'xms': xms,
      'xmx': xmx,
      'write_percent': FLAGS.intel_cassandra_write_percent,
      'read_percent': FLAGS.intel_cassandra_read_percent,
      'rate_threads': intel_cassandra.GetRateThreads(server_vms[0]),
      'run_duration': FLAGS.intel_cassandra_run_duration,
  }
  benchmark_spec.software_config_metadata = {
      'num_server_nodes': len(vm_dict[SERVER_GROUP]),
      'num_client_nodes': len(vm_dict[CLIENT_GROUP]),
      'compaction_strategy': FLAGS.intel_cassandra_compaction_strategy,
      'compressor_class': FLAGS.intel_cassandra_compressor_class,
      'chunk_length_in_kb': FLAGS.intel_cassandra_chunk_length_in_kb,
      'concurrent_reads': intel_cassandra.GetConcurrentReads(server_vms[0]),
      'concurrent_writes': FLAGS.intel_cassandra_concurrent_writes,
      'num_instances': FLAGS.intel_cassandra_instances,
      'db_checksum': benchmark_spec.db_checksum,
      'num_db_entries': FLAGS.intel_cassandra_num_db_entries,
      'gctype': FLAGS.intel_cassandra_gctype,
      'db': db,
      'openjdk_version': FLAGS.intel_cassandra_openjdk_url or FLAGS.intel_cassandra_openjdk_version,
      'version': FLAGS.intel_cassandra_bin_url,
      'benchmark_version': CASSANDRA_VER,
  }
  return metadata


def Run(benchmark_spec):
  """Run Cassandra on server vms.

  Args:
    benchmark_spec: The benchmark specification. Contains all data
        that is required to run the benchmark.
  """
  vm_dict = benchmark_spec.vm_groups
  server_vms = vm_dict[SERVER_GROUP]
  client_vms = vm_dict[CLIENT_GROUP]

  _GenerateMetadataFromFlags(benchmark_spec)
  cassandra_thread_list = []
  if len(server_vms[0].additional_private_ip_addresses) > 0:
    cassandra_ips = [str(server_vms[0].internal_ip)] + server_vms[0].additional_private_ip_addresses
  else:
    cassandra_ips = [str(server_vms[0].internal_ip)]
  for instance in range(int(FLAGS.intel_cassandra_instances)):
    cassandra_path = CASSANDRA_DIR + str(instance)
    context = {'cassandra_dir': cassandra_path,
               'cassandra_cql': CASSANDRA_CQL,
               'write_percent': benchmark_spec.tunable_parameters_metadata['write_percent'],
               'read_percent': benchmark_spec.tunable_parameters_metadata['read_percent'],
               'duration': benchmark_spec.tunable_parameters_metadata['run_duration'],
               'num_rows': benchmark_spec.software_config_metadata['num_db_entries'],
               'server_internal_ip': cassandra_ips[instance],
               'rate_threads': benchmark_spec.tunable_parameters_metadata['rate_threads'],
               'graph_out': "{0}/cass.html".format(cassandra_path)}
    # replace run.sh template file with user inputs
    for config_file in [CASSANDRA_RUN_TEMPLATE]:
      local_path = data.ResourcePath(config_file)
      remote_path = posixpath.join(
          cassandra_path, os.path.splitext(os.path.basename(config_file))[0])
      client_vms[0].RenderTemplate(local_path, remote_path, context=context)
    if FLAGS.intel_cassandra_parallel is True:
      cassandra_thread = threading.Thread(target=lambda vm, path: vm.RemoteCommand('chmod +x {0}/run.sh && {0}/run.sh > {0}/run.out &'.format(path)), args=(client_vms[0], cassandra_path))
      cassandra_thread.start()
      cassandra_thread_list.append(cassandra_thread)
    else:
      client_vms[0].RemoteCommand('chmod +x {0}/run.sh && '
                                  '{0}/run.sh > {0}/run.out'.format(cassandra_path))
  if FLAGS.intel_cassandra_parallel is True:
    for thread in cassandra_thread_list:
      thread.join()
  return CollectResults(benchmark_spec)


def Cleanup(benchmark_spec):
  """Cleanup function.

  Args:
    benchmark_spec: The benchmark specification. Contains all data
        that is required to run the benchmark.
  """
  vm_dict = benchmark_spec.vm_groups
  server_vms = vm_dict[SERVER_GROUP]
  client_vms = vm_dict[CLIENT_GROUP]

  vm_util.RunThreaded(intel_cassandra.Stop, server_vms)
  vm_util.RunThreaded(intel_cassandra.CleanServer, server_vms)
  vm_util.RunThreaded(intel_cassandra.CleanNode, client_vms)
