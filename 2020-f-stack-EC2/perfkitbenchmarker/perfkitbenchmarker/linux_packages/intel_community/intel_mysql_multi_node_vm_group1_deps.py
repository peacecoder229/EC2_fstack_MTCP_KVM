import posixpath
import logging

from absl import flags
from perfkitbenchmarker.linux_packages import INSTALL_DIR


BENCHMARK_NAME = "intel_mysql_multi_node"
BENCHMARK_DATA_DIR = "intel_mysql_multi_node_benchmark"
BENCHMARK_DIR = posixpath.join(INSTALL_DIR, BENCHMARK_DATA_DIR)
GROUP_NAME = "vm_group1"
FLAGS = flags.FLAGS



flags.DEFINE_string("intel_mysql_multi_node_deps_centos_mysql_vm_group1_ver", "5.7.22",
                    "Version of mysql package")
flags.DEFINE_string("intel_mysql_multi_node_deps_ubuntu_mysql_vm_group1_ver", "5.7.22",
                    "Version of mysql package")


def YumInstall(vm):
  from perfkitbenchmarker.linux_benchmarks.intel_mysql_multi_node_benchmark import INSTALLED_PACKAGES
  pkg = "Mysql"
  pkg_dict = {"name": pkg}
  if FLAGS.intel_mysql_multi_node_deps_centos_mysql_vm_group1_ver:
    ver = FLAGS.intel_mysql_multi_node_deps_centos_mysql_vm_group1_ver
    pkg_dict["version"] = ver
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./mysql_packages_centos7_vmgroup1.sh install")
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./mysql_multi_node_setup.sh {0}".format(FLAGS.intel_mysql_multi_node_install_path))


def YumUninstall(vm):
  """
  Uninstall Packages
  """
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./mysql_packages_centos7_vmgroup1.sh remove")



def AptInstall(vm):
  from perfkitbenchmarker.linux_benchmarks.intel_mysql_multi_node_benchmark import INSTALLED_PACKAGES
  pkg = "Mysql"
  pkg_dict = {"name": pkg}
  if FLAGS.intel_mysql_multi_node_deps_ubuntu_mysql_vm_group1_ver:
    ver = FLAGS.intel_mysql_multi_node_deps_ubuntu_mysql_vm_group1_ver
    pkg_dict["version"] = ver
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./mysql_packages_ubuntu1804_vmgroup1.sh install")
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./mysql_multi_node_setup.sh {0}".format(FLAGS.intel_mysql_multi_node_install_path))


def AptUninstall(vm):
  """
  Uninstall Packages
  """
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./mysql_packages_ubuntu1804_vmgroup1.sh remove")
