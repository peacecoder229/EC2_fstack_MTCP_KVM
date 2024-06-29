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


"""Module containing redis installation and cleanup functions."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from absl import flags
from perfkitbenchmarker import linux_packages
from six.moves import range


flags.DEFINE_integer('redis_total_num_processes', 1,
                     'Total number of redis server processes.',
                     lower_bound=1)
flags.DEFINE_boolean('redis_enable_aof', False,
                     'Enable append-only file (AOF) with appendfsync always.')
flags.DEFINE_string('redis_server_version', '4.0.11',
                    'Version of redis server to use.')


REDIS_FIRST_PORT = 6379
REDIS_PID_FILE = 'redis.pid'
FLAGS = flags.FLAGS
REDIS_GIT = 'https://github.com/antirez/redis.git'


def _GetRedisTarName():
  return 'redis-%s.tar.gz' % FLAGS.redis_server_version


def GetRedisDir():
  return '%s/redis' % linux_packages.INSTALL_DIR


def _Install(vm):
  """Installs the redis package on the VM."""
  vm.InstallPackages('numactl')
  vm.Install('build_tools')
  vm.Install('wget')
  vm.RemoteCommand('cd %s; git clone %s' %
                   (linux_packages.INSTALL_DIR, REDIS_GIT))
  vm.RemoteCommand('cd %s && git checkout %s && make' % (
      GetRedisDir(), FLAGS.redis_server_version))


def YumInstall(vm):
  """Installs the redis package on the VM."""
  vm.InstallPackages('tcl-devel')
  _Install(vm)


def AptInstall(vm):
  """Installs the redis package on the VM."""
  vm.InstallPackages('tcl-dev')
  _Install(vm)


def Uninstall(vm):
  vm.RemoteCommand('rm -rf {0}'.format(GetRedisDir()))
  vm.RemoteCommand('cd %s && rm %s' % (linux_packages.INSTALL_DIR, _GetRedisTarName()))


def Configure(vm, num_processes=None):
  """Configure redis server."""
  if not num_processes:
    num_processes = FLAGS.redis_total_num_processes
  vm.RemoteCommand('cp {0}/redis.conf {0}/redis.conf.orig'.format(GetRedisDir()))
  sed_cmd = (
      r"sed -i -e '/^save /d' -e 's/# *save \"\"/save \"\"/' "
      "{0}/redis.conf").format(GetRedisDir())
  vm.RemoteCommand(
      'sudo sed -i "s/bind/#bind/g" {0}/redis.conf'.format(GetRedisDir()))
  vm.RemoteCommand(
      'sudo sed -i "s/protected-mode yes/protected-mode no/g" {0}/redis.conf'.
      format(GetRedisDir()))
  vm.RemoteCommand(sed_cmd)
  vm.RemoteCommand(r'sed -i -e "s/^bind 127.0.0.1/# bind 127.0.0.1/g" '
                   r'{0}/redis.conf'.format(GetRedisDir()))
  vm.RemoteCommand(r'sed -i -e "s/^protected-mode yes/protected-mode no/g" '
                   r'{0}/redis.conf'.format(GetRedisDir()))
  if FLAGS.redis_enable_aof:
    vm.RemoteCommand(
        r'sed -i -e "s/appendonly no/appendonly yes/g" {0}/redis.conf'.format(
            GetRedisDir()))
    vm.RemoteCommand((
        r'sed -i -e "s/appendfsync everysec/# appendfsync everysec/g" '
        r'{0}/redis.conf'
    ).format(GetRedisDir()))
    vm.RemoteCommand((
        r'sed -i -e "s/# appendfsync always/appendfsync always/g" '
        r'{0}/redis.conf'
    ).format(GetRedisDir()))
  command = ''
  for i in range(num_processes):
    port = REDIS_FIRST_PORT + i
    command += 'cp %s/redis.conf %s/redis-%d.conf ;' % (GetRedisDir(), GetRedisDir(), port)
    command += r'sed -i -e "s/port %d/port %d/g" %s/redis-%d.conf ;' % (REDIS_FIRST_PORT, port, GetRedisDir(), port)
  vm.RemoteCommand(command)


def Unconfigure(vm):
  """Undo configuration steps."""
  vm.RemoteCommand('rm {0}/redis-*.conf'.format(GetRedisDir()))
  vm.RemoteCommand('mv {0}/redis.conf.orig {0}/redis.conf'.format(GetRedisDir()))


def Start(vm, num_processes=None, numa_node_count=0):
  """Start redis server process."""
  if not num_processes:
    num_processes = FLAGS.redis_total_num_processes
  command = ''
  for i in range(num_processes):
    port = REDIS_FIRST_PORT + i
    if numa_node_count > 0:
      # distribute redis instances across numa nodes
      numa_cmd = 'numactl --membind={0} --cpunodebind={0} -- '.format(i % numa_node_count)
    else:
      numa_cmd = ''
    command += 'nohup sudo {0}{1}/src/redis-server {1}/redis-{2}.conf ' \
               '&> /dev/null & echo $! > {1}/{3}-{2}'.format(numa_cmd, GetRedisDir(), port, REDIS_PID_FILE)
  vm.RemoteCommand(command)


def Stop(vm):
  """Stop all running redis processes."""
  vm.RemoteCommand('sudo pkill redis-server')


def Cleanup(vm):
  """Cleanup redis."""
  Stop(vm)
  Unconfigure(vm)
