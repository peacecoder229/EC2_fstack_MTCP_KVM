import posixpath
import logging

from absl import flags
from perfkitbenchmarker.linux_packages import INSTALL_DIR


BENCHMARK_NAME = "dsb_social_networking "
BENCHMARK_DATA_DIR = "dsb_social_networking_benchmark"
BENCHMARK_DIR = posixpath.join(INSTALL_DIR, BENCHMARK_DATA_DIR)
GROUP_NAME = "vm_group1"
FLAGS = flags.FLAGS
flags.DEFINE_string("dsb_social_networking_deps_ubuntu_luarocks_vm_group1_ver", None,
                    "Version of luarocks package")
flags.DEFINE_string("dsb_social_networking_deps_ubuntu_libssl_dev_vm_group1_ver", None,
                    "Version of libssl-dev package")
flags.DEFINE_string("dsb_social_networking_deps_ubuntu_libz_dev_vm_group1_ver", None,
                    "Version of libz-dev package")
flags.DEFINE_string("dsb_social_networking_deps_ubuntu_python_vm_group1_ver", None,
                    "Version of python package")
flags.DEFINE_string("dsb_social_networking_deps_ubuntu_python3_pip_vm_group1_ver", None,
                    "Version of python3-pip package")


def AptInstall(vm):
  from perfkitbenchmarker.linux_benchmarks.dsb_social_networking_benchmark import OS_INFO, INSTALLED_PACKAGES
  OS_INFO[GROUP_NAME]["os_name"] = "Ubuntu"
  OS_INFO[GROUP_NAME]["os_ver"] = "19.04"
  OS_INFO[GROUP_NAME]["os_kernel"] = "5.0.0-21-generic"
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./install_build_deps.sh")
  pkg = "luarocks"
  pkg_dict = {"name": pkg}
  if FLAGS.dsb_social_networking_deps_ubuntu_luarocks_vm_group1_ver:
    ver = FLAGS.dsb_social_networking_deps_ubuntu_luarocks_vm_group1_ver
    pkg_dict["expected_version"] = ver
    if vm.HasPackage(pkg + "=" + ver):
      pkg = pkg + "=" + ver
    else:
      logging.info("Could not install version {0} of package {1}, installing latest"
                   .format(FLAGS.dsb_social_networking_deps_ubuntu_luarocks_vm_group1_ver,
                           "luarocks"))
  vm.InstallPackages(pkg)
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  pkg = "libssl-dev"
  pkg_dict = {"name": pkg}
  if FLAGS.dsb_social_networking_deps_ubuntu_libssl_dev_vm_group1_ver:
    ver = FLAGS.dsb_social_networking_deps_ubuntu_libssl_dev_vm_group1_ver
    pkg_dict["expected_version"] = ver
    if vm.HasPackage(pkg + "=" + ver):
      pkg = pkg + "=" + ver
    else:
      logging.info("Could not install version {0} of package {1}, installing latest"
                   .format(FLAGS.dsb_social_networking_deps_ubuntu_libssl_dev_vm_group1_ver,
                           "libssl-dev"))
  vm.InstallPackages(pkg)
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  pkg = "libz-dev"
  pkg_dict = {"name": pkg}
  if FLAGS.dsb_social_networking_deps_ubuntu_libz_dev_vm_group1_ver:
    ver = FLAGS.dsb_social_networking_deps_ubuntu_libz_dev_vm_group1_ver
    pkg_dict["expected_version"] = ver
    if vm.HasPackage(pkg + "=" + ver):
      pkg = pkg + "=" + ver
    else:
      logging.info("Could not install version {0} of package {1}, installing latest"
                   .format(FLAGS.dsb_social_networking_deps_ubuntu_libz_dev_vm_group1_ver,
                           "libz-dev"))
  vm.InstallPackages(pkg)
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  pkg = "Python3.8"
  pkg_dict = {"name": pkg}
  if FLAGS.dsb_social_networking_deps_ubuntu_python_vm_group1_ver:
    ver = FLAGS.dsb_social_networking_deps_ubuntu_python_vm_group1_ver
    pkg_dict["expected_version"] = ver
    if vm.HasPackage(pkg + "=" + ver):
      pkg = pkg + "=" + ver
    else:
      logging.info("Could not install version {0} of package {1}, installing latest"
                   .format(FLAGS.dsb_social_networking_deps_ubuntu_python_vm_group1_ver,
                           "Python"))
  vm.InstallPackages(pkg)
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  pkg = "python3-pip"
  pkg_dict = {"name": pkg}
  if FLAGS.dsb_social_networking_deps_ubuntu_python3_pip_vm_group1_ver:
    ver = FLAGS.dsb_social_networking_deps_ubuntu_python3_pip_vm_group1_ver
    pkg_dict["expected_version"] = ver
    if vm.HasPackage(pkg + "=" + ver):
      pkg = pkg + "=" + ver
    else:
      logging.info("Could not install version {0} of package {1}, installing latest"
                   .format(FLAGS.dsb_social_networking_deps_ubuntu_python3_pip_vm_group1_ver,
                           "python3-pip"))
  vm.InstallPackages(pkg)
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  vm.RemoteCommand("sudo pip3 install asyncio && sudo pip3 install aiohttp && sudo luarocks "
                   "install luasocket")
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./prepare_dsb_sn.sh")
