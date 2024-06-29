import posixpath
import logging

from absl import flags
from perfkitbenchmarker.linux_packages import INSTALL_DIR


BENCHMARK_NAME = "mpich_compile_multi_node"
BENCHMARK_DATA_DIR = "mpich_compile_multi_node_benchmark"
BENCHMARK_DIR = posixpath.join(INSTALL_DIR, BENCHMARK_DATA_DIR)
GROUP_NAME = "master"
FLAGS = flags.FLAGS
flags.DEFINE_string("mpich_compile_multi_node_deps_ubuntu_wget_master_ver", None,
                    "Version of wget package")
flags.DEFINE_string("mpich_compile_multi_node_deps_ubuntu_build_essential_master_ver", "12.1ubuntu2",
                    "Version of build-essential package")
flags.DEFINE_string("mpich_compile_multi_node_deps_centos_wget_master_ver", "1.14-18.el7.x86_64",
                    "Version of wget package")


def AptInstall(vm):
  from perfkitbenchmarker.linux_benchmarks.mpich_compile_multi_node_benchmark import INSTALLED_PACKAGES
  pkg = "wget"
  pkg_dict = {"name": pkg}
  if FLAGS.mpich_compile_multi_node_deps_ubuntu_wget_master_ver:
    ver = FLAGS.mpich_compile_multi_node_deps_ubuntu_wget_master_ver
    pkg_dict["expected_version"] = ver
    if vm.HasPackage(pkg + "=" + ver):
      pkg = pkg + "=" + ver
    else:
      logging.info("Could not install version {0} of package {1}, installing latest".format(FLAGS.mpich_compile_multi_node_deps_ubuntu_wget_master_ver, "wget"))
  vm.InstallPackages(pkg)
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./install_build_deps.sh")
  pkg = "build-essential"
  pkg_dict = {"name": pkg}
  if FLAGS.mpich_compile_multi_node_deps_ubuntu_build_essential_master_ver:
    ver = FLAGS.mpich_compile_multi_node_deps_ubuntu_build_essential_master_ver
    pkg_dict["expected_version"] = ver
    if vm.HasPackage(pkg + "=" + ver):
      pkg = pkg + "=" + ver
    else:
      logging.info("Could not install version {0} of package {1}, installing latest".format(FLAGS.mpich_compile_multi_node_deps_ubuntu_build_essential_master_ver, "build-essential"))
  vm.InstallPackages(pkg)
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  vm.RemoteCommand("echo pre{ver}".format(ver="3.3"))
  vm.RemoteCommand("cd /tmp/ && wget -q http://www.mpich.org/static/downloads/{0}/mpich-{{ver}}.tar.gz && tar xvf mpich-{{ver}}.tar.gz".format(FLAGS.mpich_compile_multi_node_version).format(ver="3.3"))
  vm.RemoteCommand("echo post{ver}".format(ver="3.3"))



def YumInstall(vm):
  from perfkitbenchmarker.linux_benchmarks.mpich_compile_multi_node_benchmark import INSTALLED_PACKAGES
  pkg = "wget"
  pkg_dict = {"name": pkg}
  if FLAGS.mpich_compile_multi_node_deps_centos_wget_master_ver:
    ver = FLAGS.mpich_compile_multi_node_deps_centos_wget_master_ver
    pkg_dict["expected_version"] = ver
    if vm.HasPackage(pkg + "-" + ver):
      pkg = pkg + "-" + ver
    else:
      logging.info("Could not install version {0} of package {1}, installing latest".format(FLAGS.mpich_compile_multi_node_deps_centos_wget_master_ver, "wget"))
  vm.InstallPackages(pkg)
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  vm.RemoteCommand("sudo yum groupinstall -y 'Development Tools'")
  vm.RemoteCommand("echo pre{ver}".format(ver="3.3"))
  vm.RemoteCommand("cd /tmp/ && wget -q http://www.mpich.org/static/downloads/{0}/mpich-{{ver}}.tar.gz && tar xvf mpich-{{ver}}.tar.gz".format(FLAGS.mpich_compile_multi_node_version).format(ver="3.3"))
  vm.RemoteCommand("echo post{ver}".format(ver="3.3"))
