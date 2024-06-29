import posixpath
import os

from perfkitbenchmarker import configs
from perfkitbenchmarker import sample
from perfkitbenchmarker import vm_util
from absl import flags
from perfkitbenchmarker import data
from perfkitbenchmarker.linux_packages import intel_k8s
from perfkitbenchmarker.linux_packages import INSTALL_DIR

INSTALLED_PACKAGES = {}
OS_INFO = {}
BENCHMARK_NAME = "intel_cnb_data_cloud"
BENCHMARK_DATA_DIR = "intel_cnb_data_cloud_benchmark"
BENCHMARK_DIR = posixpath.join(INSTALL_DIR, BENCHMARK_DATA_DIR)

BENCHMARK_CONFIG = """
intel_cnb_data_cloud:
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
          machine_type: c2-standard-8
          zone: us-central1-a
          image: null
        Azure:
          machine_type: Standard_F2s_v2
          zone: eastus2
          image: null

"""

BENCHMARK_URL = "https://cumulus.s3.us-east-2.amazonaws.com/cloud_expert/CloudXPRT_v1.10_data-analytics.tar.gz"
BENCHMARK_TAR = "CloudXPRT_v1.10_data-analytics.tar.gz"
BENCHMARK_SUT_DIR = "CloudXPRT_v1.10_data-analytics"
PARSE_SCRIPT = "parse_result.py"
DATA_CFG = "cnb-analytics_config.json"

FLAGS = flags.FLAGS


def _GetInternalResources(vm, url):
  if url:
    dir_name = "internal_resources_{0}".format(vm.name)
    internal_dir = vm_util.PrependTempDir(dir_name)
    vm_util.IssueCommand("mkdir -p {0}".format(internal_dir).split())
    curl_dest_path = posixpath.join(internal_dir, BENCHMARK_TAR)
    vm_util.IssueCommand("curl -o {0} {1}".format(curl_dest_path, url).split(),
                         timeout=60)
    archive_name = "{0}.tar.gz".format(dir_name)
    archive_path = vm_util.PrependTempDir(archive_name)
    remote_archive_path = posixpath.join(BENCHMARK_DIR, archive_name)
    vm_util.IssueCommand("tar czf {0} -C {1} .".format(archive_path,
                                                       internal_dir).split())
    vm.RemoteCommand("mkdir -p {0}".format(BENCHMARK_DIR))
    vm.RemoteCopy(archive_path, remote_archive_path)
    vm.RemoteCommand("tar xf {0} -C {1}".format(remote_archive_path,
                                                BENCHMARK_DIR))


def _ConvertNumericValue(val):
  converted_val = val
  try:
    converted_val = int(val)
  except BaseException:
    try:
      converted_val = float(val)
    except BaseException:
      if val.lower().startswith("0x"):
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
  vms = benchmark_spec.vms
  target = vms[0]
  _GetInternalResources(target, BENCHMARK_URL)

  source_dir = data.ResourcePath("intel_community/" + BENCHMARK_DATA_DIR)
  target.RemoteCopy(source_dir, INSTALL_DIR)
  target.RemoteCommand("sudo chmod -R +x {0}".format(INSTALL_DIR))
  target.RemoteCommand("cd {0} && tar -xf {1}".format(BENCHMARK_DIR, BENCHMARK_TAR))

  remote_run_path = posixpath.join(BENCHMARK_DIR, BENCHMARK_SUT_DIR, "cnbrun")
  target.RemoteCommand(("cd {0} && cp {1} {2}").format(BENCHMARK_DIR, PARSE_SCRIPT, remote_run_path))
  target.RemoteCommand(("cd {0} && cp {1} {2}").format(BENCHMARK_DIR, DATA_CFG, remote_run_path))

  _InitFlags(benchmark_spec)
  OS_INFO["vm_group1"] = {}
  INSTALLED_PACKAGES["vm_group1"] = []

  vms = benchmark_spec.vms
  intel_k8s.InstallK8sCSP(vms[0], vms[1:], False)

  remote_setup_path = posixpath.join(BENCHMARK_DIR, BENCHMARK_SUT_DIR, "setup")
  if isinstance(target, list):
    vm_util.RunThreaded(
        lambda vm: vm.RemoteCommand("cd {0} && ".format(remote_setup_path) +
                                    "sudo ./cnb-analytics_setup.sh"),
        target,
    )
  else:
    target.RemoteCommand("cd {0} && ".format(remote_setup_path) +
                         "sudo ./cnb-analytics_setup.sh")


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
      "metadata_type": "workload category - Web",
      "metadata_load": "Unknown",
  }
  packages_versions = GetInstalledPackageVersions(benchmark_spec.vm_groups)
  if packages_versions:
    metadata["packages"] = packages_versions
    metadata["os"] = GetOsInfo(benchmark_spec.vm_groups)

  vm = vm_group_vm_group1[0]
  remote_run_path = posixpath.join(BENCHMARK_DIR, BENCHMARK_SUT_DIR, "cnbrun")
  remote_output_path = posixpath.join(BENCHMARK_DIR, BENCHMARK_SUT_DIR,
                                      "cnbrun/output")
  run_cmd = "cd {0} && ".format(remote_run_path) + "sudo ./cnbrun"
  vm.RemoteCommand(run_cmd)
  metadata["goal"] = "Increase"

  vm.RemoteCommand(
      "cd {0} && ".format(remote_run_path) +
      "./cnb-analytics_parse-all-results.sh | sed -e 's/\s\+/,/g' > results.csv"
  )
  out, _ = vm.RemoteCommand("cd {0} && ".format(remote_run_path) +
                            "python3 parse_result.py")

  val = out.strip()
  results.append(
      sample.Sample("Throughput", val, "transactions per minute", metadata))
  vm.RemoteCopy(vm_util.GetTempDir(), remote_output_path, False)
  return results


def Cleanup(benchmark_spec):
  """Cleans up after the benchmark completes.

    The state of the VMs should be equivalent to the state before Prepare was
    called.

    Args:
      benchmark_spec: The benchmark spec for this sample benchmark.
    """


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
      parsed_os_info[group]["expected_os_kernel_ver"] = OS_INFO[group][
          "os_kernel"]
    parsed_os_info[group]["os_name"] = OS_INFO[group]["os_name"]
  return parsed_os_info
