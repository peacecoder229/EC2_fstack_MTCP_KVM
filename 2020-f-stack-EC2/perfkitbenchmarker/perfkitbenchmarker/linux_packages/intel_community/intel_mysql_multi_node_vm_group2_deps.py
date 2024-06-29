import posixpath
import logging

from absl import flags
from perfkitbenchmarker.linux_packages import INSTALL_DIR


BENCHMARK_NAME = "intel_mysql_multi_node"
BENCHMARK_DATA_DIR = "intel_mysql_multi_node_benchmark"
BENCHMARK_DIR = posixpath.join(INSTALL_DIR, BENCHMARK_DATA_DIR)
GROUP_NAME = "vm_group2"
FLAGS = flags.FLAGS



flags.DEFINE_string("intel_mysql_multi_node_deps_centos_sysbench_vm_group2_ver", "1.1.0",
                    "Version of sysbench package")
flags.DEFINE_string("intel_mysql_multi_node_deps_ubuntu_sysbench_vm_group2_ver", "1.1.0",
                    "Version of sysbench package")


def YumInstall(vm):
  from perfkitbenchmarker.linux_benchmarks.intel_mysql_multi_node_benchmark import INSTALLED_PACKAGES
  pkg = "sysbench"
  pkg_dict = {"name": pkg}
  if FLAGS.intel_mysql_multi_node_deps_centos_sysbench_vm_group2_ver:
    ver = FLAGS.intel_mysql_multi_node_deps_centos_sysbench_vm_group2_ver
    pkg_dict["version"] = ver
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./mysql_packages_centos7_vmgroup2.sh install")
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./sysbench_install.sh {0}".format(FLAGS.intel_mysql_multi_node_install_path))


def YumUninstall(vm):
  """
  Uninstall Packages
  """
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./mysql_packages_centos7_vmgroup2.sh remove")



def AptInstall(vm):
  from perfkitbenchmarker.linux_benchmarks.intel_mysql_multi_node_benchmark import INSTALLED_PACKAGES
  pkg = "sysbench"
  pkg_dict = {"name": pkg}
  if FLAGS.intel_mysql_multi_node_deps_ubuntu_sysbench_vm_group2_ver:
    ver = FLAGS.intel_mysql_multi_node_deps_ubuntu_sysbench_vm_group2_ver
    pkg_dict["version"] = ver
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./mysql_packages_ubuntu1804_vmgroup2.sh install")
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./sysbench_install.sh {0}".format(FLAGS.intel_mysql_multi_node_install_path))


def AptUninstall(vm):
  """
  Uninstall Packages
  """
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./mysql_packages_ubuntu1804_vmgroup2.sh remove")
