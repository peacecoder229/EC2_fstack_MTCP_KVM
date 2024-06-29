import posixpath
import os

from perfkitbenchmarker import configs
from perfkitbenchmarker import sample
from perfkitbenchmarker import vm_util
from absl import flags
from perfkitbenchmarker import data
from perfkitbenchmarker.linux_packages import INSTALL_DIR

INSTALLED_PACKAGES = {}
BENCHMARK_NAME = "intel_python_django"
BENCHMARK_DATA_DIR = "intel_python_django_benchmark"
BENCHMARK_DIR = posixpath.join(INSTALL_DIR, BENCHMARK_DATA_DIR)
BENCHMARK_CONFIG = """
intel_python_django:
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

""" Configuration flags """
flags.DEFINE_string("intel_python_django_version", "v1.1.1", "The Python Django Workload version to be used. Cmd line parameter passed to the workload install script.")
flags.DEFINE_string("intel_python_django_webtier_version", "v1.0.4", "The Webtier-provisioning version to be used. Cmd line parameter passed to the workload install script.")
flags.DEFINE_enum("intel_python_django_https_enabled", "False", ('True', 'False'), "If True, Python Django will run using HTTPS. The default is False, defaulting to HTTP")
flags.DEFINE_enum("intel_python_django_https_tls_version", "TLSv1.3", ('TLSv1.2', 'TLSv1.3'), "TLS version to be used by the workload with HTTPS mode. Default is TLSv1.3.")
flags.DEFINE_string("intel_python_django_https_cipher", "None", "Cipher to be used by the workload with HTTPS mode. Only ciphers in TLSv1.2 can be specified.")


""" Tunable flags """
flags.DEFINE_integer("intel_python_django_run_count", 1, "Number of times the WL is run. Default is 1.",
                     lower_bound=1, upper_bound=20)
flags.DEFINE_integer("intel_python_django_client_concurrency", 185, "Number of Siege client workers. Default is 185.",
                     lower_bound=50, upper_bound=1024)
flags.DEFINE_integer("intel_python_django_uwsgi_workers", None, "Number of uWSGI server workers. Default is equal to the number of vCPUs.",
                     lower_bound=1, upper_bound=512)



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
  """ If  there are any flags which will be assigned a value
      based on some operations on the host/SUT, they will be initilaized here
  """
  vm_group_vm_group1 = benchmark_spec.vm_groups["vm_group1"]
  if not FLAGS["intel_python_django_uwsgi_workers"].present:
    out, _ = vm_group_vm_group1[0].RemoteCommand("'nproc'")
    val = out.strip()
    val = _ConvertNumericValue(val)
    FLAGS.intel_python_django_uwsgi_workers = val


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
  target = vm_group_vm_group1[0]
  if not isinstance(target, list):
    target = [target]
  res = ['"https://gitlab.devtools.intel.com/DCSP/Python/django-workload-internal/-/archive/{0}/django-workload-internal-{0}.zip".format(FLAGS.intel_python_django_version)', '"https://gitlab.devtools.intel.com/DCSP/CWA/webtier-provisioning/-/archive/{0}/webtier-provisioning-{0}.zip".format(FLAGS.intel_python_django_webtier_version)']
  res = [eval(r) for r in res]
  if isinstance(target, list):
    vm_util.RunThreaded(lambda vm: _GetInternalResources(vm, res), target)
  else:
    _GetInternalResources(target, res)
  if isinstance(target, list):
    vm_util.RunThreaded(lambda vm: vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./install_django_wl.sh {0} {1}".format(FLAGS.intel_python_django_version, FLAGS.intel_python_django_webtier_version)), target)
  else:
    target.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./install_django_wl.sh {0} {1}".format(FLAGS.intel_python_django_version, FLAGS.intel_python_django_webtier_version))


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
      "type": "workload category - Web",
      "load": "Unknown",
  }
  packages_versions = GetInstalledPackageVersions(benchmark_spec.vm_groups)
  if packages_versions:
    metadata["packages"] = packages_versions
  run_cmd = "~/python-django/src/django-workload/data-collection/run.sh -v ~/python-django/venv -o {0} -c {1} --https {2} --run_count={3} --uwsgi_workers={4} --https_tls_version={5} --https_cipher={6}".format("~/python-django/results/", FLAGS.intel_python_django_client_concurrency, FLAGS.intel_python_django_https_enabled, FLAGS.intel_python_django_run_count, FLAGS.intel_python_django_uwsgi_workers, FLAGS.intel_python_django_https_tls_version, FLAGS.intel_python_django_https_cipher)
  vm_group_vm_group1[0].RemoteCommand(run_cmd)
  metadata["goal"] = "Increase"
  vm = vm_group_vm_group1[0]
  out, _ = vm.RemoteCommand("cat {0}/run/run_log.txt | grep 'Transaction rate:' | awk '{{ print $3 }}'".format("~/python-django/results/"))
  val = out.strip()
  results.append(sample.Sample("Transaction rate", val, "trans/sec", metadata))
  vm_group_vm_group1[0].RemoteCopy(vm_util.GetTempDir(), "~/python-django/results/", False)
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
    vm_util.RunThreaded(lambda vm: vm.RemoteCommand("sudo rm -rf $install_path"), target)
  else:
    target.RemoteCommand("sudo rm -rf $install_path")


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
