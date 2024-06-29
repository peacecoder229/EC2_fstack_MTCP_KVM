import posixpath
import logging

from absl import flags
from perfkitbenchmarker.linux_packages import INSTALL_DIR


BENCHMARK_NAME = "mpich_compile"
BENCHMARK_DATA_DIR = "mpich_compile_benchmark"
BENCHMARK_DIR = posixpath.join(INSTALL_DIR, BENCHMARK_DATA_DIR)
GROUP_NAME = "vm_group1"
FLAGS = flags.FLAGS



flags.DEFINE_string("mpich_compile_deps_ubuntu_build_essential_vm_group1_ver", "12.1ubuntu2",
                    "Version of build-essential package")
flags.DEFINE_string("mpich_compile_deps_ubuntu_mpich_vm_group1_ver", "3.3",
                    "Version of mpich package")
flags.DEFINE_string("mpich_compile_deps_centos_wget_vm_group1_ver", "1.14-18.el7.x86_64",
                    "Version of wget package")
flags.DEFINE_string("mpich_compile_deps_centos_mpich_vm_group1_ver", "3.3",
                    "Version of mpich package")


def AptInstall(vm):
  from perfkitbenchmarker.linux_benchmarks.mpich_compile_benchmark import INSTALLED_PACKAGES
  pkg = "build-essential"
  pkg_dict = {"name": pkg}
  if FLAGS.mpich_compile_deps_ubuntu_build_essential_vm_group1_ver:
    ver = FLAGS.mpich_compile_deps_ubuntu_build_essential_vm_group1_ver
    pkg_dict["version"] = ver
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  pkg = "mpich"
  pkg_dict = {"name": pkg}
  if FLAGS.mpich_compile_deps_ubuntu_mpich_vm_group1_ver:
    ver = FLAGS.mpich_compile_deps_ubuntu_mpich_vm_group1_ver
    pkg_dict["version"] = ver
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./install_build_deps_ubuntu1604.sh install")
  vm.RemoteCommand("cd /tmp && wget -q http://www.mpich.org/static/downloads/{0}/mpich-3.3.tar.gz && tar xvf mpich-3.3.tar.gz".format(FLAGS.mpich_compile_version))


def AptUninstall(vm):
  """
  Uninstall Packages
  """
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./install_build_deps_ubuntu1604.sh remove")



def YumInstall(vm):
  from perfkitbenchmarker.linux_benchmarks.mpich_compile_benchmark import INSTALLED_PACKAGES
  pkg = "wget"
  pkg_dict = {"name": pkg}
  if FLAGS.mpich_compile_deps_centos_wget_vm_group1_ver:
    ver = FLAGS.mpich_compile_deps_centos_wget_vm_group1_ver
    pkg_dict["version"] = ver
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  pkg = "mpich"
  pkg_dict = {"name": pkg}
  if FLAGS.mpich_compile_deps_centos_mpich_vm_group1_ver:
    ver = FLAGS.mpich_compile_deps_centos_mpich_vm_group1_ver
    pkg_dict["version"] = ver
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./install_build_deps_centos7.sh install")
  vm.RemoteCommand("cd /tmp && wget -q http://www.mpich.org/static/downloads/{0}/mpich-3.3.tar.gz && tar xvf mpich-3.3.tar.gz".format(FLAGS.mpich_compile_version))


def YumUninstall(vm):
  """
  Uninstall Packages
  """
