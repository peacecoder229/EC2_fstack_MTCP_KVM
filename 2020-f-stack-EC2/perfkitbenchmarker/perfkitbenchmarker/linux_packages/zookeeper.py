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


"""Module containing Zookeeper installation and cleanup functions."""

from perfkitbenchmarker.linux_packages import INSTALL_DIR
from absl import flags

FLAGS = flags.FLAGS

ZOOKEEPER_DIR = '%s/zookeeper' % INSTALL_DIR
ZOOKEEPER_ROOT = 'zookeeper-3.4.14'
ZOOKEEPER_URL = 'https://archive.apache.org/dist/zookeeper/%s/%s.tar.gz' % (ZOOKEEPER_ROOT, ZOOKEEPER_ROOT)
ZOOKEEPER_ARCHIVE = '%s.tar.gz' % ZOOKEEPER_ROOT
ZOOKEEPER_DATA_DIR = '/tmp/zookeeper'
DEFAULT_PORT = 2181
LEADER_PORT = 2888
ELECTION_PORT = 3888


def _Install(vm):
  """Installs zookeeper on the VM."""
  vm.Install('openjdk')
  vm.Install('wget')
  vm.RemoteCommand('cd {0}; wget {1}; tar -xzvf {2}; rm {2}; mv {3} {4}'.format(INSTALL_DIR, ZOOKEEPER_URL, ZOOKEEPER_ARCHIVE, ZOOKEEPER_ROOT, ZOOKEEPER_DIR))


def YumInstall(vm):
  """Installs zookeeper on the VM."""
  _Install(vm)


def AptInstall(vm):
  """Installs zookeeper on the VM."""
  _Install(vm)


def Uninstall(vm):
  vm.RemoteCommand('sudo rm -rf {0}'.format(ZOOKEEPER_DIR))
  vm.RemoteCommand('sudo rm -rf {0}'.format(ZOOKEEPER_DATA_DIR))


def Start(vm):
  vm.RemoteCommand('{0}/bin/zkServer.sh start {1}'.format(ZOOKEEPER_DIR, _GetConfigFilePath()))


def Stop(vm):
  vm.RemoteCommand('{0}/bin/zkServer.sh stop'.format(ZOOKEEPER_DIR))
  vm.RemoteCommand('{0}/bin/zkCleanup.sh {1} -n 10'.format(ZOOKEEPER_DIR, ZOOKEEPER_DATA_DIR))


def Configure(vm, myid, config):
  # save my id
  vm.RemoteCommand('mkdir -p {0}'.format(ZOOKEEPER_DATA_DIR))
  vm.RemoteCommand('echo {0} > {1}/myid'.format(myid, ZOOKEEPER_DATA_DIR))
  # copy and then update the sample config
  vm.RemoteCommand('cp {0}/conf/zoo_sample.cfg {1}'.format(ZOOKEEPER_DIR, _GetConfigFilePath()))
  for key, value in config.items():
    vm.RemoteCommand('echo {0}={1} >> {2}'.format(key, value, _GetConfigFilePath()))


def _GetConfigFilePath():
  return '{0}/conf/zoo.cfg'.format(ZOOKEEPER_DIR)
