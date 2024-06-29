import posixpath
import logging

from absl import flags
from perfkitbenchmarker.linux_packages import INSTALL_DIR


BENCHMARK_NAME = "mpich_compile_multi_node"
BENCHMARK_DATA_DIR = "mpich_compile_multi_node_benchmark"
BENCHMARK_DIR = posixpath.join(INSTALL_DIR, BENCHMARK_DATA_DIR)
GROUP_NAME = "compute_nodes"
FLAGS = flags.FLAGS



flags.DEFINE_string("mpich_compile_multi_node_deps_ubuntu_wget_compute_nodes_ver", None,
                    "Version of wget package")
flags.DEFINE_string("mpich_compile_multi_node_deps_centos_wget_compute_nodes_ver", "1.14-18.el7.x86_64",
                    "Version of wget package")


def AptInstall(vm):
  from perfkitbenchmarker.linux_benchmarks.mpich_compile_multi_node_benchmark import INSTALLED_PACKAGES
  pkg = "wget"
  pkg_dict = {"name": pkg}
  if FLAGS.mpich_compile_multi_node_deps_ubuntu_wget_compute_nodes_ver:
    ver = FLAGS.mpich_compile_multi_node_deps_ubuntu_wget_compute_nodes_ver
    pkg_dict["version"] = ver
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./compute_nodes_ubuntu1604.sh install")


def AptUninstall(vm):
  """
  Uninstall Packages
  """



def YumInstall(vm):
  from perfkitbenchmarker.linux_benchmarks.mpich_compile_multi_node_benchmark import INSTALLED_PACKAGES
  pkg = "wget"
  pkg_dict = {"name": pkg}
  if FLAGS.mpich_compile_multi_node_deps_centos_wget_compute_nodes_ver:
    ver = FLAGS.mpich_compile_multi_node_deps_centos_wget_compute_nodes_ver
    pkg_dict["version"] = ver
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./compute_nodes_centos7.sh install")


def YumUninstall(vm):
  """
  Uninstall Packages
  """
