# Copyright 2018 PerfKitBenchmarker Authors. All rights reserved.
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


"""Module containing Kafka installation and cleanup functions."""


from perfkitbenchmarker.linux_packages import INSTALL_DIR
from absl import flags


FLAGS = flags.FLAGS


KAFKA_DIR = '{0}/kafka'.format(INSTALL_DIR)
KAFKA_ROOT = 'kafka_2.12-2.5.1'
KAFKA_URL = 'https://archive.apache.org/dist/kafka/2.5.1/{0}.tgz'.format(KAFKA_ROOT)
KAFKA_ARCHIVE = '{0}.tgz'.format(KAFKA_ROOT)
DEFAULT_PORT = 9092
CONF_DIR = '{0}/config'.format(KAFKA_DIR)


def _Install(vm):
  """Installs kafka on the VM."""
  vm.Install('openjdk')
  vm.Install('wget')
  vm.RemoteCommand('cd {0}; wget {1}; tar -xzvf {2}; rm {2}; mv {3} {4}'.format(INSTALL_DIR, KAFKA_URL, KAFKA_ARCHIVE, KAFKA_ROOT, KAFKA_DIR))


def YumInstall(vm):
  """Installs kafka on the VM."""
  _Install(vm)


def AptInstall(vm):
  """Installs kafka on the VM."""
  _Install(vm)


def Uninstall(vm):
  vm.RemoteCommand('sudo rm -rf {0}'.format(KAFKA_DIR))


def Start(vm, server_number):
  vm.RemoteCommand('{0}/bin/kafka-server-start.sh -daemon {1}'.format(KAFKA_DIR, _GetConfigFilePath(server_number)))


def Stop(vm):
  vm.RemoteCommand('{0}/bin/kafka-server-stop.sh'.format(KAFKA_DIR))


def Configure(vm, server_number, config, base_port, ip_addrs, extra_config, encrypt=False):
  # make a copy of the default config file to be used for this server
  vm.RemoteCommand('cp {0} {1}'.format(_GetDefaultConfigFilePath(), _GetConfigFilePath(server_number)))

  # edit that server-specific config file
  for key, value in config.items():
    vm.RemoteCommand(r"sed -i -e 's/^{0}=.*/{0}={1}/' {2}".format(key, value, _GetConfigFilePath(server_number)))

  # set the ip/port(s) in the config file
  # listeners=PLAINTEXT://10.0.0.90:9092,PLAINTEXT1://10.0.0.21:9093
  # listener.security.protocol.map=PLAINTEXT:PLAINTEXT,PLAINTEXT1:PLAINTEXT
  listeners = []
  maps = []
  for idx, ip in enumerate(ip_addrs):
    listeners.append(r"{0}{1}:\/\/{2}:{3}".format('SSL' if encrypt else 'PLAINTEXT', idx if idx > 0 else '', ip, base_port + idx))
    maps.append("{0}{1}:{0}".format('SSL' if encrypt else 'PLAINTEXT', idx if idx > 0 else ''))

  vm.RemoteCommand(r"sed -i -e 's/^#listeners=.*/listeners={0}/' {1}".format(','.join(listeners), _GetConfigFilePath(server_number)))
  vm.RemoteCommand(r"sed -i -e 's/^#listener.security.protocol.map=.*/listener.security.protocol.map={0}/' {1}".format(','.join(maps), _GetConfigFilePath(server_number)))

  if encrypt:
    for key, value in extra_config.items():
      vm.RemoteCommand(r"sed -i -e '$a{0}={1}' {2}".format(key, value, _GetConfigFilePath(server_number)))


def _GetDefaultConfigFilePath():
  return '{0}/config/server.properties'.format(KAFKA_DIR)


def _GetConfigFilePath(server_number):
  return '{0}/config/server.properties.{1}'.format(KAFKA_DIR, server_number)


def DeleteLogFile(vm, benchmark_spec, vm_index):
  # deletes the mount directory which is used to store log files
  mount_dir = benchmark_spec.vm_groups['brokers'][vm_index].disk_specs[0].mount_point
  vm.RemoteCommand('sudo rm -rf {0}/kafka'.format(mount_dir))
