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

"""Module containing mongodb installation and cleanup functions."""
import time
import logging
import os
import posixpath


from perfkitbenchmarker import errors
from perfkitbenchmarker import data
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from absl import flags
FLAGS = flags.FLAGS

flags.DEFINE_string('mongodb_pre_generated', None,
                    'Path to root of pre-generated database directories. '
                    'Directory names within must match this format: '
                    'mongod-<port>-data.')
flags.DEFINE_string('mongodb_tar', None,
                    'Path to pre-downloaded MongoDB package in tar.gz format. '
                    'If provided, MongoDB will not be downloaded from mongodb.org. '
                    'May be used with --data_search_paths.')

MONGODB_DIR = os.path.join(INSTALL_DIR, 'mongodb-folder')
MONGODB_FIRST_PORT = 27017
MONGODB_VERSION = '4.4.1'
MONGODB_URL_UBUNTU = 'https://downloads.mongodb.com/linux/mongodb-linux-x86_64-enterprise-ubuntu2004-{}.tgz'.format(MONGODB_VERSION)
MONGODB_URL_RHEL = 'https://downloads.mongodb.com/linux/mongodb-linux-x86_64-enterprise-rhel80-{}.tgz'.format(MONGODB_VERSION)
MONGODB_TAR_FILENAME = 'mongodb.tgz'
MONCAONE_PEM = 'moncaone.pem'


def AptInstall(vm):
  vm.InstallPackages('libcurl4')   # mongod needs this
  _Install(vm, MONGODB_URL_UBUNTU)
  vm.InstallPackages('snmp')


def YumInstall(vm):
  _Install(vm, MONGODB_URL_RHEL)
  vm.InstallPackages('net-snmp')


def _Install(vm, mongodb_dl_url):
  """Installs mongodb on the VM."""
  if FLAGS.mongodb_tar:
    vm.RemoteCopy(data.ResourcePath(FLAGS.mongodb_tar), os.path.join(INSTALL_DIR, MONGODB_TAR_FILENAME))
  else:
    vm.Install('wget')
    vm.RemoteCommand('wget {} -O {}'.format(mongodb_dl_url, os.path.join(INSTALL_DIR, MONGODB_TAR_FILENAME)))

  vm.RemoteCommand('mkdir -p {}'.format(MONGODB_DIR))
  vm.RemoteCommand('tar xvfz {} -C {} --strip-components 1'.format(os.path.join(INSTALL_DIR, MONGODB_TAR_FILENAME), MONGODB_DIR))

  vm.RemoteCommand('cd {0}/bin/ && chmod 744 *'.format(MONGODB_DIR))


def Configure(vm, mongodb_enable_encryption, cache_size=None, num_mongodb_instances=1, ip_addresses=[]):
  """Configure mongodb server."""
  logging.info("mongodb: Configure(cache_size=" +
               str(cache_size) + ", num_mongodb_instances=" +
               str(num_mongodb_instances) + ")")
  if not cache_size:
    # MongoDB recommends cache size of 50% of (RAM - 1GB)
    total_ram_gb = (vm.total_memory_kb / 1000 / 1000)
    useable_ram_gb = (total_ram_gb - num_mongodb_instances) / 2
    cache_size = useable_ram_gb / num_mongodb_instances
  assert cache_size > 0
  if not ip_addresses:
    ip_addresses = [vm.internal_ip]
  for i in range(num_mongodb_instances):
    bindip = ip_addresses[i % len(ip_addresses)]
    port = MONGODB_FIRST_PORT + i
    dbpath = '{0}/mongod-{1}-data'.format(vm.GetScratchDir(), port)
    logpath = '{0}/mongod-{1}.log'.format(vm.GetScratchDir(), port)
    pidpath = '{0}/mongod-{1}.pid'.format(vm.GetScratchDir(), port)
    # mongodb.conf from: https://github.com/mongodb/mongo/blob/v4.0/debian/mongod.conf
    config_str = """\
# mongod.conf
# for documentation of all options, see:
#   http://docs.mongodb.org/manual/reference/configuration-options/
# Where and how to store data.
storage:
  dbPath: {dbpath}
  journal:
    enabled: false
  syncPeriodSecs: 0
  engine: wiredTiger
  wiredTiger:
    engineConfig:
      cacheSizeGB: {cache_size}
# where to write logging data.
systemLog:
  destination: file
  logAppend: true
  path: {logpath}
# network interfaces
net:
  port: {port}
  bindIp: {bindip}
# how the process runs
processManagement:
  fork: true
  pidFilePath: {pidpath}
#security:
#operationProfiling:
#replication:
#sharding:
## Enterprise-Only Options:
#auditLog:
#snmp:
""".format(port=port, bindip=bindip,
           cache_size=cache_size, dbpath=dbpath,
           logpath=logpath, pidpath=pidpath)
    vm.RemoteCommand('echo "{0}" > {1}/mongod-{2}.conf'.format(config_str, MONGODB_DIR, port))
    if mongodb_enable_encryption:
      vm.RemoteCommand('sed -i "/bindIp:/anet.tls.certificateKeyFile: {0}/{1}" {2}/mongod-{3}.conf'.format(INSTALL_DIR, MONCAONE_PEM, MONGODB_DIR, port))
      vm.RemoteCommand('sed -i "/bindIp:/anet.tls.mode: requireTLS" {0}/mongod-{1}.conf'.format(MONGODB_DIR, port))
    vm.RemoteCommand('mkdir -p {0}'.format(dbpath))
    if FLAGS.mongodb_pre_generated:
      cmd = 'sudo cp -r {0}/mongod-{1}-data/* {2}/mongod-{1}-data/'.format(FLAGS.mongodb_pre_generated,
                                                                           port, vm.GetScratchDir())
      vm.RemoteCommand(cmd)


def GetStartCommand(vm, instance_index, mongodb_enable_encryption):
  port = MONGODB_FIRST_PORT + instance_index
  if mongodb_enable_encryption:
    mongodb_start = '{0}/bin/mongod -f {0}/mongod-{1}.conf --tlsDisabledProtocols none'.format(MONGODB_DIR, port)
  else:
    mongodb_start = '{0}/bin/mongod -f {0}/mongod-{1}.conf '.format(MONGODB_DIR, port)
  return mongodb_start


def Start(vm, mongodb_enable_encryption, num_mongodb_instances):
  """Start mongodb server process."""
  vm.RemoteCommand('sudo sync')
  vm.DropCaches()
  for i in range(num_mongodb_instances):
    vm.RemoteCommand(GetStartCommand(vm, i, mongodb_enable_encryption))


def Stop(vm, num_mongodb_instances):
  """Stop all instances of mongod."""
  logging.info("Wait until MongoDB instances have stopped before deleting data files.")
  max_wait = 300
  wait_interval = 5
  total_wait = 0
  while True:
    try:
      vm.RemoteCommand('sudo pkill mongod')
    except errors.VirtualMachine.RemoteCommandError:
      # no mongodb processes left
      break
    time.sleep(wait_interval)
    total_wait += wait_interval
    if total_wait >= max_wait:
      raise Exception("Failed to stop MongoDB instances within {} seconds.".format(max_wait))
  # remove data files
  for i in range(num_mongodb_instances):
    port = MONGODB_FIRST_PORT + i
    dbpath = '{0}/mongod-{1}-data'.format(vm.GetScratchDir(), port)
    logpath = '{0}/mongod-{1}.log'.format(vm.GetScratchDir(), port)
    pidpath = '{0}/mongod-{1}.pid'.format(vm.GetScratchDir(), port)
    vm.RemoteCommand('sudo rm -rf {}'.format(dbpath))
    vm.RemoteCommand('sudo rm -f {}'.format(logpath))
    vm.RemoteCommand('sudo rm -f {}'.format(pidpath))


def Uninstall(vm):
  """Remove mongodb."""
  vm.RemoteCommand('sudo rm -rf {0}'.format(MONGODB_DIR))
