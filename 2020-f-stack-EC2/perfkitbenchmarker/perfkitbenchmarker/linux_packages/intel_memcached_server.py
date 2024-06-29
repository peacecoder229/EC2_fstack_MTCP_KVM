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


"""Module containing memcached server installation and cleanup functions."""

import logging
import os

from perfkitbenchmarker import errors
from absl import flags
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import data
from perfkitbenchmarker.linux_packages import INSTALL_DIR

FLAGS = flags.FLAGS

MEMCACHED_PORT = 11211
MEMCACHED_TAR_FILENAME = "memcached.tar.gz"
MEMCACHED_DIR = os.path.join(INSTALL_DIR, "memcached_src")
MEMCACHED_BIN = os.path.join(INSTALL_DIR, "memcached_src", "memcached")
MEMCACHED_PID_FILE = os.path.join(INSTALL_DIR, "memcached.pid")
MEMCACHED_SIZE_FILE = os.path.join(INSTALL_DIR, "memcached.cachesize")

flags.DEFINE_string('intel_memcached_version', None,
                    'Memcached version to download. Uses latest stable '
                    'release if version not specified.')

flags.DEFINE_string('intel_memcached_tar', None,
                    'Path to pre-downloaded memcached source package in tgz '
                    'format. If provided, Memcached will not be downloaded.')

flags.DEFINE_integer('intel_memcached_size_mb', 64,
                     'Size of memcached cache in megabytes. '
                     'Zero to fit in available memory.')

flags.DEFINE_integer('intel_memcached_size_mb_max', 25000,
                     'Sets upper limit when intel_memcached_size_mb is set to '
                     'zero.')

flags.DEFINE_integer('intel_memcached_num_threads', 4,
                     'Number of worker threads. '
                     'Zero to use all threads available on VM.')

flags.DEFINE_integer('intel_memcached_max_client_connections', 1024,
                     'Number of client connections.')


def _Install(vm):
  """Installs the memcached server on the VM."""
  vm.Install('build_tools')
  vm.Install('event')
  if FLAGS.intel_memcached_tar:
    vm.RemoteCopy(data.ResourcePath(FLAGS.intel_memcached_tar), os.path.join(INSTALL_DIR, MEMCACHED_TAR_FILENAME))
  else:
    vm.Install('wget')
    if FLAGS.intel_memcached_version:
      memcached_dl_url = "http://www.memcached.org/files/memcached-{}.tar.gz".format(FLAGS.intel_memcached_version)
    else:
      memcached_dl_url = "http://memcached.org/latest"
    vm.RemoteCommand('wget {} -O {}'.format(memcached_dl_url, os.path.join(INSTALL_DIR, MEMCACHED_TAR_FILENAME)))

  vm.RemoteCommand('mkdir -p {}'.format(MEMCACHED_DIR))
  vm.RemoteCommand('tar xvfz {} -C {} --strip-components 1'.format(os.path.join(INSTALL_DIR, MEMCACHED_TAR_FILENAME), MEMCACHED_DIR))
  vm.RemoteCommand('cd {} && ./configure && make'.format(MEMCACHED_DIR))


def YumInstall(vm):
  """Installs the memcache server on the VM."""
  _Install(vm)


def AptInstall(vm):
  """Installs the memcache server on the VM."""
  _Install(vm)


@vm_util.Retry(poll_interval=5, timeout=300,
               retryable_exceptions=(errors.Resource.RetryableCreationError))
def _WaitForServerUp(vm):
  """Block until the memcached server is up and responsive.

  Will timeout after 5 minutes, and raise an exception. Before the timeout
  expires any exceptions are caught and the status check is retried.

  We check the status of the server by issuing a 'stats' command. This should
  return many lines of form 'STAT <name> <value>' if the server is up and
  running.

  Args:
    vm: VirtualMachine memcached has been installed on.

  Raises:
    errors.Resource.RetryableCreationError when response is not as expected or
      if there is an error connecting to the port or otherwise running the
      remote check command.
  """
  address = vm.internal_ip
  port = MEMCACHED_PORT

  logging.info('Trying to connect to memcached at %s:%s', address, port)
  try:
    out, _ = vm.RemoteCommand(
        '(echo -e "stats\n")| netcat -q 1 %s %s' % (address, port))
    if out.startswith('STAT '):
      logging.info('memcached server stats received. Server up and running.')
      return
  except errors.VirtualMachine.RemoteCommandError as e:
    raise errors.Resource.RetryableCreationError(
        'memcached server not up yet: %s.' % str(e))
  else:
    raise errors.Resource.RetryableCreationError(
        'memcached server not up yet. Expected "STAT" but got "%s".' % out)


def _GetCacheSizeMb(vm):
  if FLAGS.intel_memcached_size_mb:
    return FLAGS.intel_memcached_size_mb
  # set to 80% of free memory, maximum of intel_memcached_size_mb_max
  size = int(round((vm.total_free_memory_kb / 1024) * 0.8))
  size = min(size, FLAGS.intel_memcached_size_mb_max)
  return size


def GetConfiguredCacheSizeMb(vm):
  if FLAGS.intel_memcached_size_mb:
    return FLAGS.intel_memcached_size_mb
  # free memory has likely changed so can't recalculate, must retrieve
  # from config file
  stdout, _ = vm.RemoteCommand("cat {}".format(MEMCACHED_SIZE_FILE))
  size = int(stdout)
  return size


def Configure(vm):
  """Prepare the memcached server on a VM.

  Args:
    vm: VirtualMachine to install and start memcached on.
  """
  for scratch_disk in vm.scratch_disks:
    vm.RemoteCommand('sudo umount %s' % scratch_disk.mount_point)


def StartMemcached(vm):
  mb = _GetCacheSizeMb(vm)
  vm.RemoteCommand('{binary} -d -l {network} -m {size} '
                   '-p {port} -t {threads} -c {connections} '
                   '-P {pidfile}'.format(binary=MEMCACHED_BIN,
                                         network="0.0.0.0",
                                         size=mb,
                                         port=MEMCACHED_PORT,
                                         threads=FLAGS.intel_memcached_num_threads or vm.NumCpusForBenchmark(),
                                         connections=FLAGS.intel_memcached_max_client_connections,
                                         pidfile=MEMCACHED_PID_FILE))
  vm.RemoteCommand("echo '{}' > {}".format(mb, MEMCACHED_SIZE_FILE))
  _WaitForServerUp(vm)
  logging.info('memcached server started.')


def GetVersion(vm):
  """Returns the version of the memcached server installed."""
  results, _ = vm.RemoteCommand('{binary} -help |grep -m 1 "memcached"'
                                '| tr -d "\n"'.format(binary=MEMCACHED_BIN))
  return results


def StopMemcached(vm):
  vm.RemoteCommand('pkill -F {}'.format(MEMCACHED_PID_FILE), ignore_failure=True)


def FlushMemcachedServer(vm):
  vm.RemoteCommand('echo "flush_all" | nc -q 1 {ip} {port}'.format(ip=vm.internal_ip,
                                                                   port=MEMCACHED_PORT))
