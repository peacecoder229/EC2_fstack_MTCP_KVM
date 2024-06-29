import posixpath
import logging

from absl import flags
from perfkitbenchmarker.linux_packages import INSTALL_DIR


BENCHMARK_NAME = "intel_python_django"
BENCHMARK_DATA_DIR = "intel_python_django_benchmark"
BENCHMARK_DIR = posixpath.join(INSTALL_DIR, BENCHMARK_DATA_DIR)
GROUP_NAME = "vm_group1"
FLAGS = flags.FLAGS



flags.DEFINE_string("intel_python_django_deps_ubuntu_ansible_vm_group1_ver", None,
                    "Version of ansible package")


def AptInstall(vm):
  from perfkitbenchmarker.linux_benchmarks.intel_python_django_benchmark import INSTALLED_PACKAGES
  pkg = "ansible"
  pkg_dict = {"name": pkg}
  if FLAGS.intel_python_django_deps_ubuntu_ansible_vm_group1_ver:
    ver = FLAGS.intel_python_django_deps_ubuntu_ansible_vm_group1_ver
    pkg_dict["version"] = ver
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./django_packages_ubuntu1804.sh install")
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./install_ansible.sh")


def AptUninstall(vm):
  """
  Uninstall Packages
  """
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./django_packages_ubuntu1804.sh remove")
