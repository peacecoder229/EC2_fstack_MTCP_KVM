import posixpath
import os

from perfkitbenchmarker import configs
from perfkitbenchmarker import sample
from perfkitbenchmarker import vm_util
from absl import flags
from perfkitbenchmarker import data
from perfkitbenchmarker.linux_packages import INSTALL_DIR

INSTALLED_PACKAGES = {}
BENCHMARK_NAME = "intel_mysql"
BENCHMARK_DATA_DIR = "intel_mysql_benchmark"
BENCHMARK_DIR = posixpath.join(INSTALL_DIR, BENCHMARK_DATA_DIR)
BENCHMARK_CONFIG = """
intel_mysql:
  description: Runs a sample benchmark.
  vm_groups:
    vm_group1:
      os_type: centos7
      vm_spec:
        AWS:
          machine_type: m5.xlarge
          zone: us-east-2
          boot_disk_size: 100
        GCP:
          machine_type: n1-standard-4
          zone: us-central1-a
          image: null
        Azure:
          machine_type: Standard_F2s_v2
          zone: eastus2
          image: null
"""

FLAGS = flags.FLAGS

""" Configuration flags """
flags.DEFINE_string("intel_mysql_host", "127.0.0.1", "IP address of Mysql server listen ")
flags.DEFINE_integer("intel_mysql_port", 6306, "Port of Mysql server listen ",
                     lower_bound=6000, upper_bound=7000)
flags.DEFINE_string("intel_mysql_tag", "intel", "tag for the log")
flags.DEFINE_string("intel_mysql_install_path", "/opt/pkb/", "The path Mysql installed")


""" Tunable flags """
flags.DEFINE_integer("intel_mysql_thread_count_start", 100, "The min thread num for the Sysbench",
                     lower_bound=0, upper_bound=2000)
flags.DEFINE_integer("intel_mysql_thread_count_step", 100, "The step to increase thread_count_start",
                     lower_bound=0, upper_bound=1000)
flags.DEFINE_integer("intel_mysql_thread_count_end", 1000, "The max thread num for the Sysbench",
                     lower_bound=0, upper_bound=2000)
flags.DEFINE_enum("intel_mysql_testtype", "ps", ('ps', 'rw'), "Test type for the Sysbench,ps:only search, rw:read and write")
flags.DEFINE_integer("intel_mysql_sysbench_table_size", 2000000, "The number of rows of each table used in the oltp tests")
flags.DEFINE_integer("intel_mysql_sysbench_tables", 10, "The number of tables used in sysbench oltp.lua tests")
flags.DEFINE_integer("intel_mysql_sysbench_duration", 120, "The duration of the actual run in seconds",
                     lower_bound=20, upper_bound=200)
flags.DEFINE_integer("intel_mysql_sysbench_latency_percentile", 99, "The latency percentile we ask sysbench to compute",
                     lower_bound=1, upper_bound=100)
flags.DEFINE_integer("intel_mysql_sysbench_report_interval", 10, "The interval in seconds that we ask sysbench to report results",
                     lower_bound=1, upper_bound=100)



def _GetInternalResources(vm, urls):
  if urls:
    dir_name = "internal_resources_{0}".format(vm.name)
    internal_dir = vm_util.PrependTempDir(dir_name)
    vm_util.IssueCommand("mkdir -p {0}".format(internal_dir).split())
    os.chdir(os.path.abspath(internal_dir))
    for url in urls:
      vm_util.IssueCommand("curl -O {0}".format(url).split(), timeout=None)
    archive_name = "{0}.tar.gz".format(dir_name)
    archive_path = vm_util.PrependTempDir(archive_name)
    remote_archive_path = posixpath.join(BENCHMARK_DIR, archive_name)
    vm_util.IssueCommand("tar czf {0} -C {1} .".format(archive_path, internal_dir).split())
    vm.RemoteCopy(archive_path, remote_archive_path)
    vm.RemoteCommand("tar xf {0} -C {1}".format(remote_archive_path, BENCHMARK_DIR))


def _ConvertNumericValue(val):
  converted_val = val
  try:
    converted_val = int(val)
  except BaseException:
    try:
      converted_val = float(val)
    except BaseException:
      if val.lower().startswith('0x'):
        try:
          converted_val = int(val, 16)
        except BaseException:
          pass
  return converted_val


def _InitFlags(benchmark_spec):
  pass


def GetConfig(user_config):
  """Returns the configuration of a benchmark."""
  return configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)


def Prepare(benchmark_spec):
  """Prepares the VMs and other resources for running the benchmark.

  This is a good place to download binaries onto the VMs, create any data files
  needed for a benchmark run, etc.

  Args:
    benchmark_spec: The benchmark spec for this sample benchmark.
  """
  all_vms = [vm for group, vms in benchmark_spec.vm_groups.items() for vm in vms]
  source_dir = data.ResourcePath("intel_community/" + BENCHMARK_DATA_DIR)
  vm_util.RunThreaded(lambda vm: vm.RemoteCopy(source_dir, INSTALL_DIR), all_vms)
  vm_util.RunThreaded(lambda vm: vm.RemoteCommand("sudo chmod -R +x {0}".format(INSTALL_DIR)), all_vms)
  _InitFlags(benchmark_spec)
  vm_group_vm_group1 = benchmark_spec.vm_groups["vm_group1"]
  INSTALLED_PACKAGES["vm_group1"] = []
  vm_util.RunThreaded(lambda vm: vm.Install("{0}_{1}_deps".format(BENCHMARK_NAME, "vm_group1")), vm_group_vm_group1)


def Run(benchmark_spec):
  """Runs the benchmark and returns a dict of performance data.

  It must be possible to run the benchmark multiple times after the Prepare
  stage.

  Args:
    benchmark_spec: The benchmark spec for this sample benchmark.

  Returns:
    A list of performance samples.
  """
  vm_group_vm_group1 = benchmark_spec.vm_groups["vm_group1"]
  results = []
  metadata = {
      "type": "DB",
      "load": "Peak",
  }
  packages_versions = GetInstalledPackageVersions(benchmark_spec.vm_groups)
  if packages_versions:
    metadata["packages"] = packages_versions
  run_cmd = "cd {0} && ".format(BENCHMARK_DIR) + "./mysql_test.sh {0} {1} {2} {3} {4} {5} {6} {7} {8} {9} {10} {11} {12}".format(FLAGS.intel_mysql_host, FLAGS.intel_mysql_port, FLAGS.intel_mysql_tag, FLAGS.intel_mysql_install_path, FLAGS.intel_mysql_thread_count_start, FLAGS.intel_mysql_thread_count_step, FLAGS.intel_mysql_thread_count_end, FLAGS.intel_mysql_testtype, FLAGS.intel_mysql_sysbench_table_size, FLAGS.intel_mysql_sysbench_tables, FLAGS.intel_mysql_sysbench_duration, FLAGS.intel_mysql_sysbench_latency_percentile, FLAGS.intel_mysql_sysbench_report_interval)
  vm_group_vm_group1[0].RemoteCommand(run_cmd)
  metadata["goal"] = "Sustain"
  vm = vm_group_vm_group1[0]
  out, _ = vm.RemoteCommand("grep -rn 'Threads:' {0}/sysbench/logs/result.log | awk '{{print $3}}'".format(FLAGS.intel_mysql_install_path))
  val = out.strip()
  results.append(sample.Sample("Threads with best QPS", val, "threads", metadata))
  metadata["goal"] = "Increase"
  vm = vm_group_vm_group1[0]
  out, _ = vm.RemoteCommand("grep -rn 'TPS:' {0}/sysbench/logs/result.log | awk '{{print $3}}'".format(FLAGS.intel_mysql_install_path))
  val = out.strip()
  results.append(sample.Sample("TPS", val, "tps", metadata))
  metadata["goal"] = "Increase"
  vm = vm_group_vm_group1[0]
  out, _ = vm.RemoteCommand("grep -rn 'QPS:' {0}/sysbench/logs/result.log | awk '{{print $3}}'".format(FLAGS.intel_mysql_install_path))
  val = out.strip()
  results.append(sample.Sample("QPS", val, "qps", metadata))
  metadata["goal"] = "Decrease"
  vm = vm_group_vm_group1[0]
  out, _ = vm.RemoteCommand("grep -rn 'Latency min:' {0}/sysbench/logs/result.log | awk '{{print $4}}'".format(FLAGS.intel_mysql_install_path))
  val = out.strip()
  results.append(sample.Sample("Latency min time", val, "ms", metadata))
  metadata["goal"] = "Decrease"
  vm = vm_group_vm_group1[0]
  out, _ = vm.RemoteCommand("grep -rn 'Latency avg:' {0}/sysbench/logs/result.log | awk '{{print $4}}'".format(FLAGS.intel_mysql_install_path))
  val = out.strip()
  results.append(sample.Sample("Latency avg time", val, "ms", metadata))
  metadata["goal"] = "Decrease"
  vm = vm_group_vm_group1[0]
  out, _ = vm.RemoteCommand("grep -rn 'Latency max:' {0}/sysbench/logs/result.log | awk '{{print $4}}'".format(FLAGS.intel_mysql_install_path))
  val = out.strip()
  results.append(sample.Sample("Latency max time", val, "ms", metadata))
  metadata["goal"] = "Decrease"
  vm = vm_group_vm_group1[0]
  out, _ = vm.RemoteCommand("grep -rn 'Latency percentile:' {0}/sysbench/logs/result.log | awk '{{print $4}}'".format(FLAGS.intel_mysql_install_path))
  val = out.strip()
  results.append(sample.Sample("Latency {0} th percentile time".format(FLAGS.intel_mysql_sysbench_latency_percentile), val, "ms", metadata))
  vm_group_vm_group1[0].RemoteCopy(vm_util.GetTempDir(), "{0}/sysbench/logs".format(FLAGS.intel_mysql_install_path), False)
  return results


def Cleanup(benchmark_spec):
  """Cleans up after the benchmark completes.

  The state of the VMs should be equivalent to the state before Prepare was
  called.

  Args:
    benchmark_spec: The benchmark spec for this sample benchmark.
  """
  vm_group_vm_group1 = benchmark_spec.vm_groups["vm_group1"]
  vm_util.RunThreaded(lambda vm: vm.Uninstall("{0}_{1}_deps".format(BENCHMARK_NAME, "vm_group1")), vm_group_vm_group1)
  target = vm_group_vm_group1[0]
  print(list)
  if isinstance(target, list):
    vm_util.RunThreaded(lambda vm: vm.RemoteCommand("sudo rm -rf {0}".format(FLAGS.intel_mysql_install_path)), target)
  else:
    target.RemoteCommand("sudo rm -rf {0}".format(FLAGS.intel_mysql_install_path))
  target = vm_group_vm_group1[0]
  print(list)
  if isinstance(target, list):
    vm_util.RunThreaded(lambda vm: vm.RemoteCommand("sudo rm -f $(which sysbench)"), target)
  else:
    target.RemoteCommand("sudo rm -f $(which sysbench)")


def GetInstalledPackageVersions(vm_groups):
  packages = INSTALLED_PACKAGES
  packages_diff_versions = {}
  for group, pkgs in packages.items():
    local_pkgs = []
    for pkg in pkgs:
      local_pkgs.append(pkg)
    if local_pkgs:
      packages_diff_versions[group] = local_pkgs
  return packages_diff_versions
