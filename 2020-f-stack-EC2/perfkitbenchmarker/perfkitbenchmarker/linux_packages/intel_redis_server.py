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

import os
from urllib.parse import urlparse
from absl import flags

from perfkitbenchmarker import errors
from perfkitbenchmarker.linux_packages import INSTALL_DIR


flags.DEFINE_integer('intel_redis_total_num_processes', 1,
                     'Total number of redis server processes.',
                     lower_bound=1)
flags.DEFINE_boolean('intel_redis_enable_aof', False,
                     'Enable append-only file (AOF) with appendfsync always.')
flags.DEFINE_string('intel_redis_server_version', '6.0.8',
                    'Version of redis server to use.')
flags.DEFINE_boolean('intel_redis_server_configure_os', True,
                     'Reconfigure the OS to achieve best performance. Might not work on all providers '
                     '(for example, fails on Kubernetes). Beware, some changes are currently made permanently!')
flags.DEFINE_string('intel_redis_url', '',
                    'download Redis tar archive from this URL instead of http://download.redis.io/releases/')
flags.DEFINE_string('intel_redis_pmem_size', '',
                    'size of PMEM region per server as expected by the pmdir parameter (1g, 10m, ...); '
                    'empty string disables PMEM support at compile time')


REDIS_FIRST_PORT = 6379
REDIS_PID_FILE = 'redis.pid'
FLAGS = flags.FLAGS


def _GetRedisTarName():
  if FLAGS.intel_redis_url:
    return os.path.basename(urlparse(FLAGS.intel_redis_url).path)
  else:
    return 'redis-{}.tar.gz'.format(FLAGS.intel_redis_server_version)


def _GetRedisDir():
  return '{}/redis-{}'.format(INSTALL_DIR, FLAGS.intel_redis_server_version)


def _Install(vm, packages):
  """Installs the redis package on the VM."""
  packages.append('numactl')  # same for yum and apt
  vm.InstallPackages(' '.join(packages))
  # Install from source.
  vm.Install('wget')
  vm.Install('build_tools')
  redis_url = FLAGS.intel_redis_url or 'http://download.redis.io/releases/' + _GetRedisTarName()
  vm.RemoteCommand('cd {} && wget {}'.format(INSTALL_DIR, redis_url))
  vm.RemoteCommand('mkdir -p {0} && cd {0} && '
                   'tar --auto-compress -x --strip-components=1 -f {1}'.
                   format(_GetRedisDir(), os.path.join(INSTALL_DIR, _GetRedisTarName())))
  make_flags = ''
  if FLAGS.intel_redis_pmem_size:
    # We need local scratch space for this. Check this now instead of failing much later in Configure.
    if len(vm.scratch_disks) < 1:
      raise errors.Config.InvalidValue('The VM config for {} contains no scratch disk, '
                                       'which is needed for running with PMEM.'.format(vm))
    # This only works when the source code supports PMEM.
    result, err = vm.RemoteCommand('grep ^pmdir "{0}/redis.conf"'.format(_GetRedisDir()), ignore_failure=True)
    if not result:
      raise errors.Config.InvalidValue('The redis.conf in {} does not contain the pmdir option. '
                                       'You have to download source which supports PMEM, for example with '
                                       '--intel_redis_url=https://github.com/pmem/redis/archive/5.0-poc_cow.tar.gz'.
                                       format(redis_url))
    vm.RemoteCommand(' && '.join((
        'cd {0}',
        'wget https://github.com/memkind/memkind/archive/v1.9.0.tar.gz',
        'tar xvfz v1.9.0.tar.gz',
        'cd memkind-1.9.0',
        './build_jemalloc.sh',
        './autogen.sh',
        './configure --prefix={0}/local',
        'make install',
    )).format(INSTALL_DIR))
    # We have to compile the source differently depending on how we
    # want to use it, because when compiled with MALLOC=memkind,
    # running without PMEM is not supported and segfaults because
    # server.pm_dir_path is nul:
    # https://github.com/pmem/redis/blob/3f3e96ca8bf1780257f5f99fcd50f5af41b7e2e2/src/server.c#L4178
    make_flags += " MALLOC=memkind CFLAGS='-I{0}/local/include' " \
                  "LDFLAGS='-L{0}/local/lib -Wl,-rpath,{0}/local/lib'".format(INSTALL_DIR)
  vm.RemoteCommand('cd {} && make {}'.format(_GetRedisDir(), make_flags))


def YumInstall(vm):
  """Installs the redis package on the VM."""
  packages = ['tcl-devel']
  if FLAGS.intel_redis_pmem_size:
    packages.append('numactl-devel')
  _Install(vm, packages)


def AptInstall(vm):
  """Installs the redis package on the VM."""
  packages = ['tcl-dev']
  if FLAGS.intel_redis_pmem_size:
    packages.append('libnuma-dev')
  _Install(vm, packages)


def Uninstall(vm):
  vm.RemoteCommand('rm -rf {}'.format(_GetRedisDir()))
  vm.RemoteCommand('rm -rf {}'.format(os.path.join(INSTALL_DIR, _GetRedisTarName())))


def Configure(vm, num_processes=None):
  """Configure redis server."""
  if not num_processes:
    num_processes = FLAGS.intel_redis_total_num_processes

  # 90% of RAM will be scheduled to all redis processes
  portion = 900  # 90% * 1000
  shard_size = int(vm.total_memory_kb / num_processes) * portion
  cmds = [
      'cp {0}/redis.conf {0}/redis.conf.orig'.format(_GetRedisDir()),
      r"sed -i -e '/^save /d' -e 's/# *save \"\"/save \"\"/' " "{0}/redis.conf".format(_GetRedisDir()),
      'sudo sed -i "s/bind/#bind/g" {0}/redis.conf'.format(_GetRedisDir()),
      'sudo sed -i "s/protected-mode yes/protected-mode no/g" {0}/redis.conf'.format(_GetRedisDir()),
      'sudo sed -i "s/daemonize no/daemonize yes/g" {0}/redis.conf'.format(_GetRedisDir()),
      'sudo sed -i "s/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/g" {0}/redis.conf'.format(_GetRedisDir()),
      'sudo sed -i "s/# maxmemory <bytes>/maxmemory ' + str(shard_size) + '/g" {0}/redis.conf'.format(_GetRedisDir()),
  ]
  if FLAGS.intel_redis_server_configure_os:
    cmds.extend([
        'echo never | sudo tee /sys/kernel/mm/transparent_hugepage/enabled',
        'echo 1 | sudo tee /proc/sys/vm/overcommit_memory',
        'sudo sysctl -w net.core.somaxconn=65535',
        "echo -e '* soft nofile 1000000\n* hard nofile 1000000\n"
        "root soft nofile 1000000\nroot hard nofile 1000000' | "
        "sudo tee -a  /etc/security/limits.conf",
        'sudo swapoff -a',
    ])

  cmd = ' && '.join(cmds)
  vm.RemoteCommand(cmd)

  if FLAGS.intel_redis_enable_aof:
    cmds = [
        r'sed -i -e "s/appendonly no/appendonly yes/g" {0}/redis.conf'.format(_GetRedisDir()),
        r'sed -i -e "s/appendfsync everysec/# appendfsync everysec/g" ' r'{0}/redis.conf'.format(_GetRedisDir()),
        r'sed -i -e "s/# appendfsync always/appendfsync always/g" ' r'{0}/redis.conf'.format(_GetRedisDir())
    ]
    cmd = ' && '.join(cmds)
    vm.RemoteCommand(cmd)

  commands = []
  for i in range(num_processes):
    port = REDIS_FIRST_PORT + i
    commands.append('cp {0}/redis.conf {1}/redis-{2}.conf'.format(_GetRedisDir(), _GetRedisDir(), port))
    commands.append(r'sed -i -e "s/port {0}/port {1}/g" {2}/redis-{1}.conf'.
                    format(REDIS_FIRST_PORT, port, _GetRedisDir()))
    if FLAGS.intel_redis_pmem_size:
      commands.append((r'mkdir -p {2}/redis-pmem-{0};'
                       r'sed -i -e "s;^pmdir .*;pmdir {2}/redis-pmem-{0} {3};g" {1}/redis-{0}.conf').
                      format(port, _GetRedisDir(), vm.scratch_disks[0].mount_point, FLAGS.intel_redis_pmem_size))
    else:
      # When using github.com/pmem/redis there's a "pmem" entry in the config that we need to remove
      # when not actually using PMEM, otherwise it complains about not being able to write to the
      # directory that is specified there as default when parsing that config line.
      commands.append(r'sed -i -e "s;^pmdir;#pmdir;g" {1}/redis-{0}.conf'.format(port, _GetRedisDir()))
  vm.RemoteCommand(' && '.join(commands))


def _Unconfigure(vm):
  """Undo configuration steps."""
  vm.RemoteCommand('rm {0}/redis-*.conf'.format(_GetRedisDir()))
  vm.RemoteCommand('mv {0}/redis.conf.orig {0}/redis.conf'.format(_GetRedisDir()))


def Start(vm, num_processes=None, numa_node_count=0):
  """Start redis server process."""
  if not num_processes:
    num_processes = FLAGS.intel_redis_total_num_processes
  commands = []
  for i in range(num_processes):
    port = REDIS_FIRST_PORT + i
    if numa_node_count > 0:
      # distribute redis instances across numa nodes
      numa_cmd = 'numactl --membind={0} --cpunodebind={0} -- '.format(i % numa_node_count)
    else:
      numa_cmd = ''
    commands.append('sudo {0}{1}/src/redis-server {1}/redis-{2}.conf'.format(
        numa_cmd, _GetRedisDir(), port))
  # Redis will daemonize itself. If there's any error before that, it gets printed to stderr
  # and starting the daemons is aborted.
  vm.RemoteCommand(' && '.join(commands))


def _Stop(vm):
  """Stop all running redis processes."""
  vm.RemoteCommand('sudo pkill redis-server')


def Cleanup(vm):
  """Cleanup redis."""
  _Stop(vm)
  _Unconfigure(vm)
