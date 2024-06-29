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

"""Installs/Configures Cassandra.

See 'perfkitbenchmarker/data/cassandra/' for configuration files used.

Cassandra homepage: http://cassandra.apache.org
"""

import functools
import logging
import itertools
import os
import posixpath
import time
import datetime

from perfkitbenchmarker import data
from perfkitbenchmarker import errors
from absl import flags
from perfkitbenchmarker import vm_util
from perfkitbenchmarker.linux_packages import INSTALL_DIR


FLAGS = flags.FLAGS
flags.DEFINE_string('intel_cassandra_openjdk_url', None,
                    'Link to custom openjdk version with .tar.gz extension. '
                    'Replaces value in --openjdk_url. See --helpmatch=openjdk for more options.')
flags.DEFINE_integer('intel_cassandra_openjdk_version', 8,
                     'OpenJDK major version which will be installed by system packages. '
                     'Replaces value in --openjdk_version. See --helpmatch=openjdk for more options.')
flags.DEFINE_string('intel_cassandra_bin_url',
                    'https://archive.apache.org/dist/cassandra/3.11.3/apache-cassandra-3.11.3-bin.tar.gz',
                    'link to cassandra binary')
flags.DEFINE_integer('intel_cassandra_concurrent_reads', 0,
                     'Concurrent read requests each server accepts. 0: adjust to number of CPUs')
flags.DEFINE_integer('intel_cassandra_concurrent_writes', 32,
                     'Concurrent write requests each server accepts.')
flags.DEFINE_string('intel_cassandra_compaction_strategy',
                    'SizeTieredCompactionStrategy', 'Compaction strategy to use in cql file')
flags.DEFINE_string('intel_cassandra_compressor_class',
                    'LZ4Compressor', 'Compressor class to use in cql file')
flags.DEFINE_string('intel_cassandra_cluster_name',
                    'Test cluster', 'can be used to provide a custom name for the cassandra cluster')
flags.DEFINE_integer('intel_cassandra_instances', 1, 'Number of Cassandra instances; default 1')
flags.DEFINE_boolean('intel_cassandra_parallel', True, 'set this True if you want to run Cassandra instances in parallel')

CASSANDRA_YAML_TEMPLATE = 'intel_cassandra/cassandra.yaml.j2'
CASSANDRA_JVM_FILE = 'jvm.options.j2'
CASSANDRA_JVM_FILE_TEMPLATE = posixpath.join('intel_cassandra', CASSANDRA_JVM_FILE)
CASSANDRA_JVM_FILE_LOCAL = posixpath.join('/tmp', CASSANDRA_JVM_FILE)
CASSANDRA_CQL = "cqlstress-insanity-example.yaml"
cassandra_jinja_template = CASSANDRA_CQL + ".j2"
CASSANDRA_CQL_TEMPLATE = posixpath.join('intel_cassandra', cassandra_jinja_template)
DEFAULT_CASSANDRA_AWS_BUCKET = 'cumulus'

CASSANDRA_DIR = posixpath.join(INSTALL_DIR, 'apache-cassandra')
CONFIG_PARAMS = {}

# Time, in seconds, to sleep between node starts.
NODE_START_SLEEP = 5


def _CheckNumaNode(vm):
    if vm.CheckLsCpu().numa_node_count is None:
        raise errors.Setup.InvalidConfigurationError("intel_cassandra package requires at least one NUMA node to be "
                                                     "present on the system.")


def _Install(vm):
  _CheckNumaNode(vm)
  """Installs Cassandra from a url. Sets up environment variables."""
  PREREQ_PKGS = ["numactl", "bc", "psmisc", "wget", "net-tools"]
  vm.InstallPackages(' '.join(PREREQ_PKGS))

  vm.RemoteCommand('if -d {0}; then cd {1} && mv apache-cassandra {2}-apache-cassandra; fi'.format(
      CASSANDRA_DIR,
      INSTALL_DIR,
      datetime.datetime.today().strftime("%Y%m%d%H%M%S%f")))
  cmds = ['cd {0}'.format(INSTALL_DIR),
          'wget {0}'.format(FLAGS.intel_cassandra_bin_url),
          'tar -xvzf apache-cassandra-*',
          'mv apache-cassandra-*[0-9] apache-cassandra',
          'rm -f apache-cassandra-*']
  vm.RemoteCommand(' && '.join(cmds))

  for instance in range(FLAGS.intel_cassandra_instances):
    vm.RemoteCommand('cp -r {0}/apache-cassandra {0}/apache-cassandra{1}'.format(INSTALL_DIR, instance))
  vm.RemoteCommand('rm -rf {0}/apache-cassandra'.format(INSTALL_DIR))

  if FLAGS.intel_cassandra_openjdk_url:
    FLAGS.openjdk_url = FLAGS.intel_cassandra_openjdk_url
  elif FLAGS.intel_cassandra_openjdk_version:
    FLAGS.openjdk_version = FLAGS.intel_cassandra_openjdk_version
  try:
    vm.Install('openjdk')
  except errors.VirtualMachine.RemoteCommandError:
    logging.error('Error installing OpenJDK package. See --helpmatch=openjdk for more otions.')
    return False


def YumInstall(vm):
  """Installs Cassandra on the VM."""
  _Install(vm)


def AptInstall(vm):
  """Installs Cassandra on the VM."""
  _Install(vm)


def ConfigureNetwork(vm):
  logging.info("Applying Cassandra network tunings")
  cmds = ["sudo sysctl -w net.ipv4.tcp_keepalive_time=60",
          "sudo sysctl -w net.ipv4.tcp_keepalive_probes=3",
          "sudo sysctl -w net.ipv4.tcp_keepalive_intvl=10",
          "sudo sysctl -w net.core.rmem_max=16777216",
          "sudo sysctl -w net.core.wmem_max=16777216",
          "sudo sysctl -w net.core.rmem_default=16777216",
          "sudo sysctl -w net.core.wmem_default=16777216",
          "sudo sysctl -w net.core.optmem_max=40960",
          "sudo sysctl -w net.ipv4.tcp_rmem='4096 87380 16777216'",
          "sudo sysctl -w net.ipv4.tcp_wmem='4096 65536 16777216'"]
  vm.RemoteCommand(" && ".join(cmds))


def ConfigureSystemSettings(vm):
  logging.info("Applying Cassandra system tunings")
  cmds = ['echo 0 | sudo tee /proc/sys/vm/zone_reclaim_mode',
          'echo never | sudo tee /sys/kernel/mm/transparent_hugepage/defrag',
          'sudo swapoff --all',
          'sudo sysctl -w vm.max_map_count=1048576',
          'sudo sysctl -p',
          'sudo prlimit --pid=$PPID --memlock=unlimited',
          'sudo prlimit --pid=$PPID --nofile=1048576',
          'sudo prlimit --pid=$PPID --as=unlimited',
          'sudo prlimit --pid=$PPID --nproc=32768',
          'sudo prlimit --pid=$PPID']
  vm.RemoteCommand(' && '.join(cmds))
  try:
    stdout, _ = vm.RemoteCommand('sudo sysctl -w vm.watermark_scale_factor=1000')
    logging.info(stdout)
  except errors.VirtualMachine.RemoteCommandError:
    logging.warn('/proc/sys/vm/watermark_scale_factor is absent')


def ConfigureDisks(vm):
  for disk in vm.scratch_disks:
    device_path = disk.GetDevicePath()
    disk_name = os.path.basename(device_path)
    read_ahead_kb = 0
    if disk.disk_type != 'local':
      read_ahead_kb = 32
    cmds = ['echo none | sudo tee /sys/block/{}/queue/scheduler'.format(disk_name),
            'echo 0 | sudo tee /sys/class/block/{}/queue/rotational'.format(disk_name),
            'echo {0} | sudo tee /sys/class/block/{1}/queue/read_ahead_kb'.format(read_ahead_kb, disk_name),
            'echo 2000000 | sudo tee /proc/sys/dev/raid/speed_limit_min',
            'echo 10000000 | sudo tee /proc/sys/dev/raid/speed_limit_max']
    vm.RemoteCommand(' && '.join(cmds), ignore_failure=True)


def ConfigureServer(vm, server_vms):
  """Configure Cassandra on 'vm'.

  Args:
    vm: The VM to configure.
    server_vms: List of cassandra vms.
  """
  if len(vm.scratch_disks) < FLAGS.intel_cassandra_instances:
    raise Exception('VM disks {0} are lesser than Cassandra instances{1}! '
                    'Stopping Everything!'.format(len(vm.scratch_disks), FLAGS.intel_cassandra_instances))

  numa_node_count = vm.CheckLsCpu().numa_node_count
  if numa_node_count > FLAGS.intel_cassandra_instances:
    logging.info("The number of NUMA nodes {0} is greater than the number of Cassandra instances {1}. "
                 "This may result in degraded performance".format(numa_node_count, FLAGS.intel_cassandra_instances))
    if numa_node_count % FLAGS.intel_cassandra_instances > 0:
      raise Exception("Cannot evenly distribute {0} Cassandra instances "
                      "over {1} NUMA nodes.".format(FLAGS.intel_cassandra_instances, numa_node_count))
  cassandra_ips = [str(vm.internal_ip)] + vm.additional_private_ip_addresses
  for instance in range(FLAGS.intel_cassandra_instances):
    cassandra_path = CASSANDRA_DIR + str(instance)
    context = {'ip_address': cassandra_ips[instance],
               'data_path': posixpath.join(vm.GetScratchDir(disk_num=instance), 'cassandra'),
               'seeds': ','.join(cassandra_ips[instance] for vm in server_vms),
               'cluster_name': FLAGS.intel_cassandra_cluster_name,
               'concurrent_reads': GetConcurrentReads(vm),
               'concurrent_writes': FLAGS.intel_cassandra_concurrent_writes}

    local_path = data.ResourcePath(CASSANDRA_YAML_TEMPLATE)
    remote_path = posixpath.join(
        cassandra_path, 'conf',
        os.path.splitext(os.path.basename(CASSANDRA_YAML_TEMPLATE))[0])
    vm.RenderTemplate(local_path, remote_path, context=context)
  # updating conf2
  port = 7099
  xms, xmx = GetHeapConfiguration(vm)
  for instance in range(FLAGS.intel_cassandra_instances):
    cassandra_path = CASSANDRA_DIR + str(instance)
    port += 100
    context = {
        'jmxport': str(port),
        'xms': xms,
        'xmx': xmx,
        'xss': FLAGS.intel_cassandra_xss,
        'xgcx': FLAGS.intel_cassandra_gctype
    }
    local_path = data.ResourcePath(CASSANDRA_JVM_FILE_TEMPLATE)
    remote_path = posixpath.join(
        cassandra_path, 'conf',
        os.path.splitext(os.path.basename(CASSANDRA_JVM_FILE_TEMPLATE))[0])
    vm.RenderTemplate(local_path, remote_path, context=context)
  # Cassandra Network settings from DataStax
  ConfigureNetwork(vm)
  # Cassandra System settings from DataStax
  ConfigureSystemSettings(vm)
  # Cassandra Disk settings from DataStax
  vm.Install('storage_tools')
  vm.RemoteCommand("sudo touch /var/lock/subsys/local")

  if not vm.is_static:
    ConfigureDisks(vm)


def ConfigureClient(vm, client_vms):
  # updating confs in client
  logging.info(" cassandra template %s" % CASSANDRA_CQL_TEMPLATE)
  context = {'compaction_strategy': FLAGS.intel_cassandra_compaction_strategy,
             'chunk_length': FLAGS.intel_cassandra_chunk_length_in_kb}
  local_path = data.ResourcePath(CASSANDRA_CQL_TEMPLATE)
  for instance in range(FLAGS.intel_cassandra_instances):
    cassandra_path = CASSANDRA_DIR + str(instance)
    remote_path = posixpath.join(
        cassandra_path, 'tools',
        os.path.splitext(os.path.basename(CASSANDRA_CQL_TEMPLATE))[0])
    vm.RenderTemplate(local_path, remote_path, context=context)


def StaticDatabase(server_vms):
  cmd = 'if [ -d {0} ]; then echo True; else echo False; fi'.format(FLAGS.intel_cassandra_static_db)
  if FLAGS['intel_cassandra_static_db'].present:
    for vm in server_vms:
      stdout, _ = vm.RemoteCommand(cmd)
      if stdout.strip() == "False":
        return False
    return True
  else:
    return False


def _CreateStaticDatabase(vm, instance):
  if vm.GetScratchDir(disk_num=instance) not in FLAGS.intel_cassandra_static_db:
    vm.RemoteCommand('cp -r {0} {1}'.format(FLAGS.intel_cassandra_static_db, vm.GetScratchDir(disk_num=instance)))


def CreateStaticDatabases(server_vms):
  db_fns = [functools.partial(_CreateStaticDatabase, vm, instance) for vm, instance in
            itertools.product(server_vms, range(FLAGS.intel_cassandra_instances))]
  vm_util.RunThreaded(lambda f: f(), db_fns)


def Start(vm):
  """Start Cassandra on a VM.
  Args:
    vm: The target vm. Should already be configured via 'Configure'.
  """
  numa_node_count = vm.CheckLsCpu().numa_node_count
  if numa_node_count > FLAGS.intel_cassandra_instances:
    # Multiple NUMA nodes per Cassandra instance
    numa_nodes_per_instance = numa_node_count / FLAGS.intel_cassandra_instances
    numa_node_counter = 0
    for instance in range(FLAGS.intel_cassandra_instances):
      numa_node_list = []
      for node in range(int(numa_nodes_per_instance)):
        numa_node_list.append(numa_node_counter)
        numa_node_counter += 1
      numactl_arg = ','.join([str(i) for i in numa_node_list])
      vm.RemoteCommand('export CASSANDRA_HOME={1}{2} NUMACTL_ARGS=\'-m {0} -N {0}\' '
                       '&& nohup {1}{2}/bin/cassandra -R &'.format(numactl_arg, CASSANDRA_DIR, instance))
  else:
    # One or more Cassandra instances per NUMA node
    cassandra_global_id = 0
    numa_node_count = vm.CheckLsCpu().numa_node_count
    instances_per_node = int(FLAGS.intel_cassandra_instances / numa_node_count)

    for node in range(int(FLAGS.intel_cassandra_instances / instances_per_node)):
      for _ in range(instances_per_node):
        vm.RemoteCommand('export CASSANDRA_HOME={1}{2} NUMACTL_ARGS=\'-m {0} -N {0}\' && nohup {1}{2}/bin/cassandra -R &'.format(node, CASSANDRA_DIR, cassandra_global_id))
        cassandra_global_id += 1

  time.sleep(20)

  found_cassandra_instances, _ = vm.RemoteCommand('sudo netstat -tulnp | grep 7000 | wc -l')
  if int(found_cassandra_instances.strip()) != FLAGS.intel_cassandra_instances:
    raise Exception('At least one Cassandra instance failed to start! Stopping everything')
  else:
    logging.info("Found {0} Cassandra instances OK to go!".format(FLAGS.intel_cassandra_instances))


def GetConcurrentReads(vm):
  if FLAGS.intel_cassandra_concurrent_reads == 0:
    reads = vm.num_cpus * 2
    logging.info("Calculating concurrent reads based on CPUs (2x): {}".format(reads))
    return reads
  else:
    return FLAGS.intel_cassandra_concurrent_reads


def GetRateThreads(vm):
  if FLAGS.intel_cassandra_rate_threads == 0:
    rate_threads = vm.num_cpus * 2
    logging.info("Calculating rate_threads based on CPUs (2x): {}".format(rate_threads))
    return rate_threads
  else:
    return FLAGS.intel_cassandra_rate_threads


def GetHeapConfiguration(vm):
  total_memory_gb = vm.total_memory_kb / 1024 ** 2
  if not FLAGS.intel_cassandra_xmx:
    xmx = int(total_memory_gb / 3)
    # If calculated xmx is between 32-48, the effective heap
    # is much smaller due to Compressed OOPs, therefore, add
    # some buffer to get be in the correct range for Cassandra
    if (32 <= xmx <= 48):
      xmx += 8
    xms = xmx
    logging.info("Calculating heap size based on system memory, xms/xmx: {}/{}".format(xms, xmx))
  else:
    xms = FLAGS.intel_cassandra_xms
    xmx = FLAGS.intel_cassandra_xmx
    if xmx < xms:
      raise Exception('Configured xmx must be greater than or equal to xms!')
    if int(xmx) * FLAGS.intel_cassandra_instances > total_memory_gb:
      raise Exception('Total JVM xmx is greater than system memory! Stopping Everything!')
  return ["{}G".format(xms), "{}G".format(xmx)]


def Stop(vm):
  """Stops Cassandra on vm"""
  cmd = "ps -aux | grep cassandra | grep -v grep | awk '{print $2}'"
  pids = vm.RemoteCommand(cmd)
  logging.info(pids)
  for pid in pids[0].split():
    vm.RemoteCommand('kill -9 {0}'.format(int(pid.strip())), ignore_failure=True)


def CleanNode(vm):
  vm.RemoteCommand('rm -rf {0}* && '
                   'rm -rf {1}/jdk'.format(CASSANDRA_DIR, INSTALL_DIR))


def CleanServer(vm):
  """Remove Cassandra data from 'server vm'.
  Args:
    vm: VirtualMachine to clean.
  """

  for instance in range(FLAGS.intel_cassandra_instances):
    try:
      data_path = posixpath.join(vm.GetScratchDir(disk_num=instance), 'cassandra')
      vm.RemoteCommand('rm -rf {0}'.format(data_path))
      CleanNode(vm)
    except errors.Error as e:
      logging.info(str(e))


def StartCluster(vms):
  """Starts a Cassandra cluster.
  Args:
    vms: list of VirtualMachines which should be started.
  """
  # Cassandra setup
  for i, vm in enumerate(vms):
    time.sleep(NODE_START_SLEEP)
    logging.info('Starting VM %d/%d.', i + 1, len(vms))
    Start(vm)


def TryS3(vm, bucket, s3_path, dest):
  s3_url_curl_command_template = 'curl https://{0}.s3.amazonaws.com/{1} -o {2} --write-out "%{{http_code}}" --silent'
  s3_url_curl_command_to_vm = s3_url_curl_command_template.format(bucket, s3_path, dest)
  s3_cp_command = "aws s3 cp s3://{0}/{1} {2}".format(bucket, s3_path, dest)
  try:
    vm.Install('aws_credentials')
    vm.Install('awscli')
    _, _, retcode = vm.RemoteCommandWithReturnCode(s3_cp_command)
    return True
  except (data.ResourceNotFound, errors.VirtualMachine.RemoteCommandError, RuntimeError):
    logging.warning('Could not pull {} from bucket {} using S3 cp!'.format(s3_path, bucket))
  curl_http_code, _, retcode = vm.RemoteCommandWithReturnCode(s3_url_curl_command_to_vm, ignore_failure=True)
  if curl_http_code == '200':
    return True
  else:
    logging.warning('Could not pull {} from bucket {} using curl!'.format(s3_path, bucket))
    filename = os.path.basename(dest)
    local_path = posixpath.join(FLAGS.temp_dir, filename)
    if not os.path.exists(local_path):
      curl_http_code, _, retcode = vm_util.IssueCommand(
          s3_url_curl_command_template.format(bucket, s3_path, local_path).split(), timeout=18000)
      # IssueCommand differs from vm.RemoteCommand and will add escaped quotes around curl's --write-out arg
      if curl_http_code != '\"200\"':
        logging.warning('Could not pull {} from bucket {} to PKB host using curl!'.format(s3_path, bucket))
        raise Exception('All attempts to download database from s3 bucket {} failed!'.format(bucket))
    vm.PushFile(local_path, dest)
    vm_util.IssueCommand(['rm', local_path])
    return True


def InstallDatabase(filename, server_vms):
  if FLAGS['aws_preprovisioned_data_bucket'].present:
    s3_bucket = FLAGS.aws_preprovisioned_data_bucket
  else:
    s3_bucket = DEFAULT_CASSANDRA_AWS_BUCKET
  s3_path = 'intel_cassandra_stress/{}'.format(filename)
  for vm in server_vms:
    dest = posixpath.join(vm.GetScratchDir(), filename)
    TryS3(vm, s3_bucket, s3_path, dest)
    path, file = os.path.split(dest)
    checksum = vm.GetSha256sum(path, file)
    for instance in range(FLAGS.intel_cassandra_instances):
      cmd = 'cd {0} && tar -xvf {1}'.format(vm.GetScratchDir(disk_num=instance), dest)
      vm.RemoteCommand(cmd)
    # cleaningup the tar file to make room for compaction
    vm.RemoteCommand('rm {}'.format(dest))
    # Clear page cache after extracting database
    vm.DropCaches()
    return checksum
