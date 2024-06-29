import posixpath
import os

from perfkitbenchmarker import configs
from perfkitbenchmarker import sample
from perfkitbenchmarker import vm_util
from absl import flags
from perfkitbenchmarker import data
from perfkitbenchmarker.linux_packages import INSTALL_DIR

INSTALLED_PACKAGES = {}
OS_INFO = {}
BENCHMARK_NAME = "facebook5"
BENCHMARK_DATA_DIR = "facebook5_benchmark"
BENCHMARK_DIR = posixpath.join(INSTALL_DIR, BENCHMARK_DATA_DIR)
BENCHMARK_CONFIG = """
facebook5:
  description: Runs a sample benchmark.
  vm_groups:
    vm_group1:
      os_type: ubuntu1804
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




def _GetInternalResources(vm, urls):
  if urls:
    dir_name = "internal_resources_{0}".format(vm.name)
    internal_dir = vm_util.PrependTempDir(dir_name)
    vm_util.IssueCommand("mkdir -p {0}".format(internal_dir).split())
    for url in urls:
      vm_util.IssueCommand("wget -P {0} {1}".format(internal_dir, url).split(), timeout=None)
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
  OS_INFO["vm_group1"] = {}
  INSTALLED_PACKAGES["vm_group1"] = []
  vm_util.RunThreaded(lambda vm: vm.Install("{0}_{1}_deps".format(BENCHMARK_NAME, "vm_group1")), vm_group_vm_group1)
  target = vm_group_vm_group1[0]
  if not isinstance(target, list):
    target = [target]
  res = ['"https://cumulus.s3.us-east-2.amazonaws.com/facebook5/facebook5.tar.gz"']
  res = [eval(r) for r in res]
  if isinstance(target, list):
    vm_util.RunThreaded(lambda vm: _GetInternalResources(vm, res), target)
  else:
    _GetInternalResources(target, res)
  if isinstance(target, list):
    vm_util.RunThreaded(lambda vm: vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./install_facebook5_wl.bash "), target)
  else:
    target.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./install_facebook5_wl.bash ")


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
      "metadata_type": "workload category - synthetic",
      "metadata_load": "Unknown",
  }
  packages_versions = GetInstalledPackageVersions(benchmark_spec.vm_groups)
  if packages_versions:
    metadata["packages"] = packages_versions
    metadata["os"] = GetOsInfo(benchmark_spec.vm_groups)
  run_cmd = "cd {0} && ".format(BENCHMARK_DIR) + "./measure_facebook5_performance.bash "
  vm_group_vm_group1[0].RemoteCommand(run_cmd)
  metadata["goal"] = "Increase"
  vm = vm_group_vm_group1[0]
  out, _ = vm.RemoteCommand("cat /opt/speccpu/result/CINT2006.001.ref.csv | grep 'SPECint_rate_base2006' | awk -F',' '{ print $2 }'")
  val = out.strip()
  results.append(sample.Sample("Ratio ", val, "Ratio", metadata))
  vm_group_vm_group1[0].RemoteCopy(vm_util.GetTempDir(), "/opt/speccpu/result", False)
  return results


def Cleanup(benchmark_spec):
  """Cleans up after the benchmark completes.

  The state of the VMs should be equivalent to the state before Prepare was
  called.

  Args:
    benchmark_spec: The benchmark spec for this sample benchmark.
  """
  vm_group_vm_group1 = benchmark_spec.vm_groups["vm_group1"]
  target = vm_group_vm_group1[0]
  if isinstance(target, list):
    vm_util.RunThreaded(lambda vm: vm.RemoteCommand("echo cleaning up work directories && sudo rm -rf /opt/speccpu"), target)
  else:
    target.RemoteCommand("echo cleaning up work directories && sudo rm -rf /opt/speccpu")


def GetInstalledPackageVersions(vm_groups):
  packages = INSTALLED_PACKAGES
  packages_diff_versions = {}
  for group, pkgs in packages.items():
    vm = vm_groups[group][0]
    if "ubuntu" in vm.OS_TYPE:
      get_ver_cmd = "sudo dpkg -s {0} | grep '^Version' | awk '{{print $NF}}'"
    elif "centos" in vm.OS_TYPE:
      get_ver_cmd = "rpm -q {0} | awk -F '{0}-' '{{print $NF}}'"
    else:
      continue
    local_pkgs = []
    for pkg in pkgs:
      out, _ = vm.RemoteCommand(get_ver_cmd.format(pkg["name"]))
      actual_ver = str(out.strip())
      pkg["actual_version"] = actual_ver
      if "expected_version" in pkg:
        if pkg["actual_version"] == pkg["expected_version"]:
          del pkg["expected_version"]
      local_pkgs.append(pkg)
    if local_pkgs:
      packages_diff_versions[group] = local_pkgs
  return packages_diff_versions


def GetOsInfo(vm_groups):
  parsed_os_info = {group: {} for group in vm_groups}
  for group in parsed_os_info:
    vm = vm_groups[group][0]
    out, _ = vm.RemoteCommand("uname -r")
    actual_kernel_ver = str(out.strip())
    out, _ = vm.RemoteCommand("grep -w 'VERSION' /etc/os-release | "
                              "awk -F '\"' '{print $2}' | awk '{print $1}'")
    actual_os_ver = str(out.strip())
    parsed_os_info[group]["actual_os_ver"] = actual_os_ver
    parsed_os_info[group]["actual_kernel_ver"] = actual_kernel_ver
    if OS_INFO[group]["os_ver"] != actual_os_ver:
      parsed_os_info[group]["expected_os_ver"] = OS_INFO[group]["os_ver"]
    if OS_INFO[group]["os_kernel"] != actual_kernel_ver:
      parsed_os_info[group]["expected_os_kernel_ver"] = OS_INFO[group]["os_kernel"]
    parsed_os_info[group]["os_name"] = OS_INFO[group]["os_name"]
  return parsed_os_info
