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


"""Module containing aerospike server installation and cleanup functions."""

import logging

from perfkitbenchmarker import data
from perfkitbenchmarker import errors
from absl import flags
from perfkitbenchmarker import vm_util
from perfkitbenchmarker.linux_packages import INSTALL_DIR

FLAGS = flags.FLAGS

GIT_REPO = 'https://github.com/aerospike/aerospike-server.git'
GIT_TAG = '4.0.0.1'
AEROSPIKE_DIR = '%s/aerospike-server' % INSTALL_DIR
AEROSPIKE_CONF_PATH = '%s/as/etc/aerospike_dev.conf' % AEROSPIKE_DIR

# Port to be gradually incremented by 1000 if more than 1 aerospike instance is requested
AEROSPIKE_PORT = 3000
AEROSPIKE_HEARTBEAT_PORT = 9918
# Defining the number of instances at 1 by default, so if no flag is given, the benchmark will run as it does by default,
# with 1 aerospike instance
flags.DEFINE_integer('aerospike_total_num_processes', 1,
                     'Total number of server server processes.',
                     lower_bound=1)

AEROSPIKE_DEFAULT_TELNET_PORT = 3003

MEMORY = 'memory'
DISK = 'disk'
flags.DEFINE_enum('intel_aerospike_storage_type', MEMORY, [MEMORY, DISK],
                  'The type of storage to use for Aerospike data. The type of '
                  'disk is controlled by the "data_disk_type" flag.')
flags.DEFINE_integer('intel_aerospike_replication_factor', 1,
                     'Replication factor for aerospike server.')
flags.DEFINE_integer('intel_aerospike_transaction_threads_per_queue', 4,
                     'Number of threads per transaction queue.')


def _Install(vm):
  """Installs the Aerospike server on the VM."""
  vm.Install('build_tools')
  vm.Install('lua5_1')
  vm.Install('openssl')
  vm.RemoteCommand('git clone {0} {1}'.format(GIT_REPO, AEROSPIKE_DIR))
  vm.RemoteCommand('cd {0} && git checkout {1} && git submodule update --init '
                   '&& make'.format(AEROSPIKE_DIR, GIT_TAG))
  # Zach
  # After downloading the aerospike package, and issuing the make command to build it,
  # We  make i copies of it on disk, i = number of aerospike instances wanted.
  # The variable is specified by the user as a flag

  for i in range(FLAGS.aerospike_total_num_processes):
    vm.RemoteCommand(('cp -r {0} {0}-{1}').format(AEROSPIKE_DIR, i))

  # Set up the ports after the install
  # _ConfigurePorts()
# Creating this private function to iterate through the given number of instances and
# set the correct ports up within each aerospike folder instance

  for i in range(FLAGS.aerospike_total_num_processes):

    TEMP_PORT = AEROSPIKE_PORT + (i * 1000)
    TEMP_PORT_HEART = AEROSPIKE_PORT + 2 + (i * 1000)
    TEMP_PORT_FABRIC = AEROSPIKE_PORT + 1 + (i * 1000)
    TEMP_PORT_INFO = AEROSPIKE_PORT + 3 + (i * 1000)
    TEMP_HEARTB_PORT = AEROSPIKE_HEARTBEAT_PORT + i
    NAMESPACE_N = "test"

    sed_cmd_port = "sed -i 's/3000/%d/g' %s-%d/as/etc/aerospike_dev.conf" % (TEMP_PORT, AEROSPIKE_DIR, i)
    sed_cmd_heart = "sed -i 's/3002/%d/g' %s-%d/as/etc/aerospike_dev.conf" % (TEMP_PORT_HEART, AEROSPIKE_DIR, i)
    sed_cmd_fabric = "sed -i 's/3001/%d/g' %s-%d/as/etc/aerospike_dev.conf" % (TEMP_PORT_FABRIC, AEROSPIKE_DIR, i)
    sed_cmd_info = "sed -i 's/3003/%d/g' %s-%d/as/etc/aerospike_dev.conf" % (TEMP_PORT_INFO, AEROSPIKE_DIR, i)
    sed_cmd_hebp = "sed -i 's/9918/%d/g' %s-%d/as/etc/aerospike_dev.conf" % (TEMP_HEARTB_PORT, AEROSPIKE_DIR, i)
    sed_cmd_test = "sed -i 's/test/%s%d/g' %s-%d/as/etc/aerospike_dev.conf" % (NAMESPACE_N, i, AEROSPIKE_DIR, i)
    vm.RemoteCommand(sed_cmd_test)
    vm.RemoteCommand(sed_cmd_hebp)
    vm.RemoteCommand(sed_cmd_port)
    vm.RemoteCommand(sed_cmd_heart)
    vm.RemoteCommand(sed_cmd_fabric)
    vm.RemoteCommand(sed_cmd_info)

    sed_cmd_port = "sed -i 's/3000/%d/g' %s-%d/as/etc/aerospike.conf" % (TEMP_PORT, AEROSPIKE_DIR, i)
    sed_cmd_heart = "sed -i 's/3002/%d/g' %s-%d/as/etc/aerospike.conf" % (TEMP_PORT_HEART, AEROSPIKE_DIR, i)
    sed_cmd_fabric = "sed -i 's/3001/%d/g' %s-%d/as/etc/aerospike.conf" % (TEMP_PORT_FABRIC, AEROSPIKE_DIR, i)
    sed_cmd_info = "sed -i 's/3003/%d/g' %s-%d/as/etc/aerospike.conf" % (TEMP_PORT_INFO, AEROSPIKE_DIR, i)
    sed_cmd_hebp = "sed -i 's/9918/%d/g' %s-%d/as/etc/aerospike.conf" % (TEMP_HEARTB_PORT, AEROSPIKE_DIR, i)
    sed_cmd_test = "sed -i 's/test/%s%d/g' %s-%d/as/etc/aerospike.conf" % (NAMESPACE_N, i, AEROSPIKE_DIR, i)
    vm.RemoteCommand(sed_cmd_test)
    vm.RemoteCommand(sed_cmd_hebp)
    vm.RemoteCommand(sed_cmd_port)
    vm.RemoteCommand(sed_cmd_heart)
    vm.RemoteCommand(sed_cmd_fabric)
    vm.RemoteCommand(sed_cmd_info)

    sed_cmd_port = "sed -i 's/3000/%d/g' %s-%d/as/etc/aerospike_ssd_systemd.conf" % (TEMP_PORT, AEROSPIKE_DIR, i)
    sed_cmd_heart = "sed -i 's/3002/%d/g' %s-%d/as/etc/aerospike_ssd_systemd.conf" % (TEMP_PORT_HEART, AEROSPIKE_DIR, i)
    sed_cmd_fabric = "sed -i 's/3001/%d/g' %s-%d/as/etc/aerospike_ssd_systemd.conf" % (TEMP_PORT_FABRIC, AEROSPIKE_DIR, i)
    sed_cmd_info = "sed -i 's/3003/%d/g' %s-%d/as/etc/aerospike_ssd_systemd.conf" % (TEMP_PORT_INFO, AEROSPIKE_DIR, i)
    sed_cmd_hebp = "sed -i 's/9918/%d/g' %s-%d/as/etc/aerospike_ssd_systemd.conf" % (TEMP_HEARTB_PORT, AEROSPIKE_DIR, i)
    sed_cmd_test = "sed -i 's/test/%s%d/g' %s-%d/as/etc/aerospike_ssd_systemd.conf" % (NAMESPACE_N, i, AEROSPIKE_DIR, i)
    vm.RemoteCommand(sed_cmd_test)
    vm.RemoteCommand(sed_cmd_hebp)
    vm.RemoteCommand(sed_cmd_port)
    vm.RemoteCommand(sed_cmd_heart)
    vm.RemoteCommand(sed_cmd_fabric)
    vm.RemoteCommand(sed_cmd_info)

    sed_cmd_port = "sed -i 's/3000/%d/g' %s-%d/as/etc/aerospike_ssd.conf" % (TEMP_PORT, AEROSPIKE_DIR, i)
    sed_cmd_heart = "sed -i 's/3002/%d/g' %s-%d/as/etc/aerospike_ssd.conf" % (TEMP_PORT_HEART, AEROSPIKE_DIR, i)
    sed_cmd_fabric = "sed -i 's/3001/%d/g' %s-%d/as/etc/aerospike_ssd.conf" % (TEMP_PORT_FABRIC, AEROSPIKE_DIR, i)
    sed_cmd_info = "sed -i 's/3003/%d/g' %s-%d/as/etc/aerospike_ssd.conf" % (TEMP_PORT_INFO, AEROSPIKE_DIR, i)
    sed_cmd_hebp = "sed -i 's/9918/%d/g' %s-%d/as/etc/aerospike_ssd.conf" % (TEMP_HEARTB_PORT, AEROSPIKE_DIR, i)
    sed_cmd_test = "sed -i 's/test/%s%d/g' %s-%d/as/etc/aerospike_ssd.conf" % (NAMESPACE_N, i, AEROSPIKE_DIR, i)
    vm.RemoteCommand(sed_cmd_test)
    vm.RemoteCommand(sed_cmd_hebp)
    vm.RemoteCommand(sed_cmd_port)
    vm.RemoteCommand(sed_cmd_heart)
    vm.RemoteCommand(sed_cmd_fabric)
    vm.RemoteCommand(sed_cmd_info)

    sed_cmd_port = "sed -i 's/3000/%d/g' %s-%d/as/etc/aerospike_systemd.conf" % (TEMP_PORT, AEROSPIKE_DIR, i)
    sed_cmd_heart = "sed -i 's/3002/%d/g' %s-%d/as/etc/aerospike_systemd.conf" % (TEMP_PORT_HEART, AEROSPIKE_DIR, i)
    sed_cmd_fabric = "sed -i 's/3001/%d/g' %s-%d/as/etc/aerospike_systemd.conf" % (TEMP_PORT_FABRIC, AEROSPIKE_DIR, i)
    sed_cmd_info = "sed -i 's/3003/%d/g' %s-%d/as/etc/aerospike_systemd.conf" % (TEMP_PORT_INFO, AEROSPIKE_DIR, i)
    sed_cmd_hebp = "sed -i 's/9918/%d/g' %s-%d/as/etc/aerospike_systemd.conf" % (TEMP_HEARTB_PORT, AEROSPIKE_DIR, i)
    sed_cmd_test = "sed -i 's/test/%s%d/g' %s-%d/as/etc/aerospike_systemd.conf" % (NAMESPACE_N, i, AEROSPIKE_DIR, i)
    vm.RemoteCommand(sed_cmd_test)
    vm.RemoteCommand(sed_cmd_hebp)
    vm.RemoteCommand(sed_cmd_port)
    vm.RemoteCommand(sed_cmd_heart)
    vm.RemoteCommand(sed_cmd_fabric)
    vm.RemoteCommand(sed_cmd_info)

    sed_cmd_port = "sed -i 's/3000/%d/g' %s-%d/as/etc/aerospike_mesh.conf" % (TEMP_PORT, AEROSPIKE_DIR, i)
    sed_cmd_heart = "sed -i 's/3002/%d/g' %s-%d/as/etc/aerospike_mesh.conf" % (TEMP_PORT_HEART, AEROSPIKE_DIR, i)
    sed_cmd_fabric = "sed -i 's/3001/%d/g' %s-%d/as/etc/aerospike_mesh.conf" % (TEMP_PORT_FABRIC, AEROSPIKE_DIR, i)
    sed_cmd_info = "sed -i 's/3003/%d/g' %s-%d/as/etc/aerospike_mesh.conf" % (TEMP_PORT_INFO, AEROSPIKE_DIR, i)
    sed_cmd_test = "sed -i 's/test/%s%d/g' %s-%d/as/etc/aerospike_mesh.conf" % (NAMESPACE_N, i, AEROSPIKE_DIR, i)
    vm.RemoteCommand(sed_cmd_test)
    vm.RemoteCommand(sed_cmd_port)
    vm.RemoteCommand(sed_cmd_heart)
    vm.RemoteCommand(sed_cmd_fabric)
    vm.RemoteCommand(sed_cmd_info)

    sed_cmd_port = "sed -i 's/3000/%d/g' %s-%d/as/etc/aerospike_mesh_systemd.conf" % (TEMP_PORT, AEROSPIKE_DIR, i)
    sed_cmd_heart = "sed -i 's/3002/%d/g' %s-%d/as/etc/aerospike_mesh_systemd.conf" % (TEMP_PORT_HEART, AEROSPIKE_DIR, i)
    sed_cmd_fabric = "sed -i 's/3001/%d/g' %s-%d/as/etc/aerospike_mesh_systemd.conf" % (TEMP_PORT_FABRIC, AEROSPIKE_DIR, i)
    sed_cmd_info = "sed -i 's/3003/%d/g' %s-%d/as/etc/aerospike_mesh_systemd.conf" % (TEMP_PORT_INFO, AEROSPIKE_DIR, i)
    sed_cmd_hebp = "sed -i 's/9918/%d/g' %s-%d/as/etc/aerospike_mesh_systemd.conf" % (TEMP_HEARTB_PORT, AEROSPIKE_DIR, i)
    sed_cmd_test = "sed -i 's/test/%s%d/g' %s-%d/as/etc/aerospike_mesh_systemd.conf" % (NAMESPACE_N, i, AEROSPIKE_DIR, i)
    vm.RemoteCommand(sed_cmd_test)
    vm.RemoteCommand(sed_cmd_hebp)
    vm.RemoteCommand(sed_cmd_port)
    vm.RemoteCommand(sed_cmd_heart)
    vm.RemoteCommand(sed_cmd_fabric)
    vm.RemoteCommand(sed_cmd_info)


def YumInstall(vm):
  """Installs the memtier package on the VM."""
  _Install(vm)


def AptInstall(vm):
  """Installs the memtier package on the VM."""
  vm.InstallPackages('netcat-openbsd zlib1g-dev')
  _Install(vm)


@vm_util.Retry(poll_interval=5, timeout=300,
               retryable_exceptions=(errors.Resource.RetryableCreationError))
def _WaitForServerUp(server):
  """Block until the Aerospike server is up and responsive.

  Will timeout after 5 minutes, and raise an exception. Before the timeout
  expires any exceptions are caught and the status check is retried.

  We check the status of the server by connecting to Aerospike's out
  of band telnet management port and issue a 'status' command. This should
  return 'ok' if the server is ready. Per the aerospike docs, this always
  returns 'ok', i.e. if the server is not up the connection will fail or we
  would get no response at all.

  Args:
    server: VirtualMachine Aerospike has been installed on.

  Raises:
    errors.Resource.RetryableCreationError when response is not 'ok' or if there
      is an error connecting to the telnet port or otherwise running the remote
      check command.
  """
  address = server.internal_ip
  port = AEROSPIKE_DEFAULT_TELNET_PORT

  logging.info("Trying to connect to Aerospike at %s:%s" % (address, port))
  try:
    def _NetcatPrefix():
      _, stderr = server.RemoteCommand('nc -h', ignore_failure=True)
      if '-q' in stderr:
        return 'nc -q 1'
      else:
        return 'nc -i 1'

    out, _ = server.RemoteCommand(
        '(echo -e "status\n" ; sleep 1)| %s %s %s' % (
            _NetcatPrefix(), address, port))
    if out.startswith('ok'):
      logging.info("Aerospike server status is OK. Server up and running.")
      return
  except errors.VirtualMachine.RemoteCommandError as e:
    raise errors.Resource.RetryableCreationError(
        "Aerospike server not up yet: %s." % str(e))
  else:
    raise errors.Resource.RetryableCreationError(
        "Aerospike server not up yet. Expected 'ok' but got '%s'." % out)
# This is my wait for server. Uses the original, but passes on a port for the multi server case
# See the original for more comments


@vm_util.Retry(poll_interval=5, timeout=300,
               retryable_exceptions=(errors.Resource.RetryableCreationError))
def _MyWaitForServerUp(server, portPassed):
  address = server.internal_ip
  port = portPassed

  logging.info("Trying to connect to Aerospike at %s:%s" % (address, port))
  try:
    def _NetcatPrefix():
      _, stderr = server.RemoteCommand('nc -h', ignore_failure=True)
      if '-q' in stderr:
        return 'nc -q 1'
      else:
        return 'nc -i 1'

    out, _ = server.RemoteCommand(
        '(echo -e "status\n" ; sleep 1)| %s %s %s' % (
            _NetcatPrefix(), address, port))
    if out.startswith('ok'):
      logging.info("Aerospike server status is OK. Server up and running.")
      return
  except errors.VirtualMachine.RemoteCommandError as e:
    raise errors.Resource.RetryableCreationError(
        "Aerospike server not up yet: %s." % str(e))
  else:
    raise errors.Resource.RetryableCreationError(
        "Aerospike server not up yet. Expected 'ok' but got '%s'." % out)


def ConfigureAndStart(server, seed_node_ips=None):
  """Prepare the Aerospike server on a VM.

  Args:
    server: VirtualMachine to install and start Aerospike on.
    seed_node_ips: internal IP addresses of seed nodes in the cluster.
      Leave unspecified for a single-node deployment.
  """
  server.Install('aerospike_server')

  seed_node_ips = seed_node_ips or [server.internal_ip]

  if FLAGS.intel_aerospike_storage_type == DISK:
    devices = [scratch_disk.GetDevicePath()
               for scratch_disk in server.scratch_disks]
  else:
    devices = []

  server.RenderTemplate(
      data.ResourcePath('aerospike.conf.j2'), AEROSPIKE_CONF_PATH,
      {'devices': devices,
       'memory_size': int(server.total_memory_kb * 0.8),
       'seed_addresses': seed_node_ips,
       'transaction_threads_per_queue':
       FLAGS.intel_aerospike_transaction_threads_per_queue,
       'replication_factor': FLAGS.intel_aerospike_replication_factor})

  for scratch_disk in server.scratch_disks:
    if scratch_disk.mount_point:
      server.RemoteCommand('sudo umount %s' % scratch_disk.mount_point)

  # Set up the ports after the install
  # _ConfigurePorts('aerospike_server')

  # Looping through all instances and initializing, then starting them

  for i in range(FLAGS.aerospike_total_num_processes):
    server.RemoteCommand(('cd {0}-{1} && make init').format(AEROSPIKE_DIR, i))
    server.RemoteCommand('cd {0}-{1}; nohup sudo make start &> /dev/null &'.format(AEROSPIKE_DIR, i))
    THE_PORT = AEROSPIKE_DEFAULT_TELNET_PORT + (i * 1000)
    _MyWaitForServerUp(server, THE_PORT)

  logging.info("Aerospike server(s) configured and started.")

# Removing all Aerospike installtions, not just 1


def Uninstall(vm):
  for i in range(FLAGS.aerospike_total_num_processes):
    vm.RemoteCommand(('rm -rf {0}-{1}').format(AEROSPIKE_DIR, i))
