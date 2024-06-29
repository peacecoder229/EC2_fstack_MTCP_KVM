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

"""Runs Node-DC-EIS.

A running installation consists of:
  * Node-DC-EIS server.
  * MongoDB server.
  * Node-DC-EIS client.
"""

import json
import logging
import os
import re
from six import StringIO
import yaml
import decimal

from perfkitbenchmarker import configs
from perfkitbenchmarker import data
from absl import flags
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import sample
from perfkitbenchmarker.linux_packages import INSTALL_DIR

FLAGS = flags.FLAGS

flags.DEFINE_string('intel_node_dc_eis_mode', "single_threaded",
                    'It can be single_threaded or cluster. cluster mode is not advised, '
                    'as it is not ready.')
flags.DEFINE_integer('intel_node_dc_eis_MT_interval', 300,
                     'Duration of time in seconds.')
flags.DEFINE_integer('intel_node_dc_eis_clients_number', 2,
                     'The number of actively generating workers in the client')
flags.DEFINE_integer('intel_node_dc_eis_get_ratio', 90,
                     'The ratio of read requests.')
flags.DEFINE_integer('intel_node_dc_eis_post_ratio', 5,
                     'The ratio of read requests.')
flags.DEFINE_integer('intel_node_dc_eis_delete_ratio', 5,
                     'The ratio of delete requests.')
flags.DEFINE_integer('intel_node_dc_eis_cpu_count', 0,
                     'The number of node.js processes in each cluster server.')
flags.DEFINE_integer('intel_node_dc_eis_num_instances', 2,
                     'The number of clusters.')
flags.DEFINE_string('intel_node_dc_eis_repo',
                    'https://github.com/Node-DC/Node-DC-EIS.git',
                    'The repository of Node-DC-EIS can be given as a parameter.')
flags.DEFINE_string('intel_node_dc_eis_version',
                    '9a177e69129b1538388b4f7f0544ea98a43d8f72',
                    'The version of Node-DC-EIS can be given as a parameter.')


BENCHMARK_NAME = 'node_dc_eis'
BENCHMARK_CONFIG = """
node_dc_eis:
  description: >
      Run the Node-DC-EIS benchmark.
  vm_groups:
    target:
      os_type: ubuntu1804
      vm_spec: *default_dual_core
"""

# External files required to run workload
DATA_FILES = []


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


def _PrepareKeys(vm):
  cmds = [
      'ssh-keygen -N "" -f ${HOME}/.ssh/id_rsa',
      'ssh-keyscan -H 127.0.0.1 >> ~/.ssh/known_hosts',
      'cat ${HOME}/.ssh/id_rsa.pub >> ${HOME}/.ssh/authorized_keys'
  ]
  vm.RemoteCommand(' && '.join(cmds))


def Prepare(benchmark_spec):
  """Prepare the virtual machines to run.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """

  vm = benchmark_spec.vm_groups['target'][0]

  ansible_vars = {
      'INSTALL_DIR': INSTALL_DIR
  }

  ansible_script = 'setup.redhat.ansible.yml'
  if re.match(r'Ubuntu', vm.os_info):
    vm.InstallPackages('software-properties-common')
    ansible_script = 'setup.debian.ansible.yml'

  elif re.match(r'Clear', vm.os_info):
    ansible_script = 'setup.clearlinux.ansible.yml'

  vm.Install('ansible')

  vm.RemoteCopy(
      data.ResourcePath('node_dc_eis_benchmark/' + ansible_script),
      INSTALL_DIR + '/' + ansible_script)

  context_node_dc_eis_repo_version = {
      'repo': FLAGS.intel_node_dc_eis_repo,
      'version': FLAGS.intel_node_dc_eis_version,
      'INSTALL_DIR': "{{INSTALL_DIR}}"
  }

  local_path = os.path.join(data.ResourcePath('node_dc_eis_benchmark'),
                            'node_tasks.ansible.yml.j2')
  remote_path = os.path.join(INSTALL_DIR, 'node_tasks.ansible.yml')

  vm.RenderTemplate(local_path,
                    remote_path,
                    context=context_node_dc_eis_repo_version)

  vm.RemoteHostCommand(
      'while read env; do'
      '  export $env;'
      'done < /etc/environment;'
      'ansible-playbook ' +
      ' '.join([
          '--extra-vars %s=%s' % (k, v) for (k, v) in ansible_vars.items()
      ]) +
      '  ' + INSTALL_DIR + '/' + ansible_script)

  if FLAGS.intel_node_dc_eis_mode == "cluster":

    NODE_DC_EIS_PATH = os.path.join(INSTALL_DIR, 'Node-DC-EIS')

    context_client = {
        'MT_interval': FLAGS.intel_node_dc_eis_MT_interval,
        'clients_number': FLAGS.intel_node_dc_eis_clients_number,
        'get_ratio': FLAGS.intel_node_dc_eis_get_ratio,
        'post_ratio': FLAGS.intel_node_dc_eis_post_ratio,
        'delete_ratio': FLAGS.intel_node_dc_eis_delete_ratio
    }
    local_path = os.path.join(data.ResourcePath('node_dc_eis_benchmark'),
                              'config.json.j2')
    remote_path = os.path.join(NODE_DC_EIS_PATH,
                               'Node-DC-EIS-client',
                               'config.json')
    vm.RenderTemplate(local_path, remote_path, context=context_client)
    vm.RemoteHostCommand('echo \'\' >> ' + remote_path)

    context_server = {
        'num_instances': FLAGS.intel_node_dc_eis_num_instances,
        'cpu_count': FLAGS.intel_node_dc_eis_cpu_count
    }
    local_path = os.path.join(data.ResourcePath('node_dc_eis_benchmark'),
                              'run_multiple_instance.sh.j2')
    remote_path = os.path.join(NODE_DC_EIS_PATH, 'run_multiple_instance.sh')
    vm.RenderTemplate(local_path, remote_path, context=context_server)
    vm.RemoteHostCommand('chmod 755 ' + remote_path)

    generate_file_name = 'generate_multiple_instance_config.json.sh'
    local_path = os.path.join(data.ResourcePath('node_dc_eis_benchmark'),
                              generate_file_name)
    remote_path = os.path.join(INSTALL_DIR, generate_file_name)
    vm.RemoteCopy(local_path, remote_path)
    vm.RemoteHostCommand('chmod 755 ' + remote_path)
    vm.RemoteHostCommand(remote_path +
                         ' ' + str(FLAGS.intel_node_dc_eis_num_instances) +
                         ' ' + NODE_DC_EIS_PATH)

  _, _, retcode = vm.RemoteCommandWithReturnCode('file -f  ~/.ssh/id_rsa',
                                                 ignore_failure=True,
                                                 suppress_warning=True)

  if retcode:
    _PrepareKeys(vm)

  if FLAGS.intel_node_dc_eis_mode == "single_threaded":
    mongo_dbpath = INSTALL_DIR + '/data/db'
    vm.RemoteHostCommand('mkdir -p ' + mongo_dbpath)

    optional_path_mongo_db = ""
    if re.match(r'Clear', vm.os_info):
      optional_path_mongo_db += INSTALL_DIR + "/mongodb-linux-x86_64-4.1.6/bin/"
    optional_path_mongo_db += "mongod"

    vm.RemoteHostCommand(optional_path_mongo_db +
                         ' --dbpath=' + mongo_dbpath + ' --fork --syslog')


def AddSample(line, samples, regex, name, units, keys):
  """Parse the output from the Node-DC-EIS client.

  Args:
    line: A line of text.
    samples: The list of samples to which to possibly append a sample.
    regex: The regex to retrieve the sample from the line.
    name: The name of the sample.
    units: The name of the units in which the sample value is given.
    keys: The names of samples collected so far.

  Returns:
    True, if a sample was added to the list, False otherwise.
  """
  match = re.search(regex, line)
  if match is not None and name not in keys:
    keys[name] = True
    samples.append(sample.Sample(name,
                                 float(decimal.Decimal(match.group(1))),
                                 units,
                                 None))
    return True
  return False


def ParseOutput(theOutput):
  """Parse the output from the Node-DC-EIS client.

  Args:
    theOutput: a list of strings that can be iterated over to produce single lines.

  Returns:
    A list of sample.Sample objects.
  """

  keys = {}
  samples = []
  for line in theOutput:

    if AddSample(line,
                 samples,
                 r'^Throughput = ([0-9.]+) req/sec',
                 'transaction rate',
                 'transactions per second',
                 keys):
      continue
    if AddSample(line,
                 samples,
                 r'^99 percentile = ([0-9.]+) sec',
                 '99% response time',
                 'seconds',
                 keys):
      continue
    if AddSample(line,
                 samples,
                 r'Min Response time = ([0-9.]+) sec',
                 'minimum response time',
                 'seconds',
                 keys):
      continue
    if AddSample(line,
                 samples,
                 r'Mean Response time = ([0-9.]+) sec',
                 'mean response time',
                 'seconds',
                 keys):
      continue
    if AddSample(line,
                 samples,
                 r'Max Response time = ([0-9.]+) sec',
                 'maximum response time',
                 'seconds',
                 keys):
      continue
    if AddSample(line,
                 samples,
                 r'95 percentile = ([0-9.]+) sec',
                 '95% response time',
                 'seconds',
                 keys):
      continue
  return samples


def Run(benchmark_spec):
  """Run Node-DC-EIS and gather the results.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.

  Returns:
    A list of sample.Sample objects.
  """

  vm = benchmark_spec.vm_groups['target'][0]
  logging.info("running the workload")

  if FLAGS.intel_node_dc_eis_mode == "single_threaded":
    vm.RobustRemoteCommand('cd ' + INSTALL_DIR +
                           '/Node-DC-EIS/Node-DC-EIS-cluster; bash -i -c "node server-cluster.js &"')

    stdout, _ = vm.RobustRemoteCommand(
        'cd ' + INSTALL_DIR + '/Node-DC-EIS/Node-DC-EIS-client '
        ' && /usr/bin/python2.7 runspec.py -f config.json')

    list_master_summary = StringIO(stdout)

    return ParseOutput(list_master_summary)
  else:
    _, _ = vm.RobustRemoteCommand(
        'cd ' + INSTALL_DIR + '/Node-DC-EIS/ '
        ' && FULL_NODE_PATH=$(find $HOME/.nvm/ -name node | grep bin); NODE_PATH=$(dirname $FULL_NODE_PATH); '
        ' ./run_multiple_instance.sh 0 $NODE_PATH')

    command_file_retrieval = 'find ' + INSTALL_DIR + '/Node-DC-EIS/results_multiple_instance/ -printf "%T+ %p\n" | grep master_summary | sort -r | head -1 | cut -d " " -f 2'
    string_master_summary, _ = vm.RobustRemoteCommand(command_file_retrieval + " | xargs cat")
    list_master_summary = string_master_summary.splitlines()
    return ParseOutput(list_master_summary)


def Cleanup(benchmark_spec):
  """Cleanup.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """

  vm = benchmark_spec.vm_groups['target'][0]

  if FLAGS.intel_node_dc_eis_mode == "cluster":
    vm.RemoteHostCommand(
        'ps ax'
        '| grep run_multiple_instance.sh'
        '| grep bash'
        '| grep -v grep'
        '| awk "{print \\$1;}"'
        '| xargs kill -9'
        '|| true')
    vm.RemoteHostCommand('rm -rf ${HOME}/Node-DC-EIS-multiple')

  vm.RemoteHostCommand(
      'ps ax'
      '| grep node'
      '| grep -v grep'
      '| awk "{print \\$1;}"'
      '| xargs kill -9'
      '|| true')

  vm.RemoteHostCommand(
      'ps ax'
      '| grep mongo'
      '| grep -v grep'
      '| awk "{print \\$1;}"'
      '| xargs kill -9'
      '|| true')

  vm.RemoteHostCommand('rm -rf ${HOME}/.nvm ${HOME}/.npm')

  pass
