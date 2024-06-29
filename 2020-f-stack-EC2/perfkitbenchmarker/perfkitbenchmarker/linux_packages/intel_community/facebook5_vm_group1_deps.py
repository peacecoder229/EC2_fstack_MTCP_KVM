import posixpath
import logging

from absl import flags
from perfkitbenchmarker.linux_packages import INSTALL_DIR


BENCHMARK_NAME = "facebook5"
BENCHMARK_DATA_DIR = "facebook5_benchmark"
BENCHMARK_DIR = posixpath.join(INSTALL_DIR, BENCHMARK_DATA_DIR)
GROUP_NAME = "vm_group1"
FLAGS = flags.FLAGS
flags.DEFINE_string("facebook5_deps_ubuntu_tar_vm_group1_ver", None,
                    "Version of tar package")
flags.DEFINE_string("facebook5_deps_ubuntu_python_setuptools_vm_group1_ver", None,
                    "Version of python-setuptools package")
flags.DEFINE_string("facebook5_deps_ubuntu_numactl_vm_group1_ver", None,
                    "Version of numactl package")


def AptInstall(vm):
  from perfkitbenchmarker.linux_benchmarks.facebook5_benchmark import OS_INFO, INSTALLED_PACKAGES
  OS_INFO[GROUP_NAME]["os_name"] = "Ubuntu"
  OS_INFO[GROUP_NAME]["os_ver"] = "18.04"
  OS_INFO[GROUP_NAME]["os_kernel"] = "5.3.0-40-generic"
  pkg = "tar"
  pkg_dict = {"name": pkg}
  if FLAGS.facebook5_deps_ubuntu_tar_vm_group1_ver:
    ver = FLAGS.facebook5_deps_ubuntu_tar_vm_group1_ver
    pkg_dict["expected_version"] = ver
    if vm.HasPackage(pkg + "=" + ver):
      pkg = pkg + "=" + ver
    else:
      logging.info("Could not install version {0} of package {1}, installing latest".format(FLAGS.facebook5_deps_ubuntu_tar_vm_group1_ver, "tar"))
  vm.InstallPackages(pkg)
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  vm.RemoteCommand("cd {0} && ".format(BENCHMARK_DIR) + "./install_ansible.sh")
  pkg = "python-setuptools"
  pkg_dict = {"name": pkg}
  if FLAGS.facebook5_deps_ubuntu_python_setuptools_vm_group1_ver:
    ver = FLAGS.facebook5_deps_ubuntu_python_setuptools_vm_group1_ver
    pkg_dict["expected_version"] = ver
    if vm.HasPackage(pkg + "=" + ver):
      pkg = pkg + "=" + ver
    else:
      logging.info("Could not install version {0} of package {1}, installing latest".format(FLAGS.facebook5_deps_ubuntu_python_setuptools_vm_group1_ver, "python-setuptools"))
  vm.InstallPackages(pkg)
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
  pkg = "numactl"
  pkg_dict = {"name": pkg}
  if FLAGS.facebook5_deps_ubuntu_numactl_vm_group1_ver:
    ver = FLAGS.facebook5_deps_ubuntu_numactl_vm_group1_ver
    pkg_dict["expected_version"] = ver
    if vm.HasPackage(pkg + "=" + ver):
      pkg = pkg + "=" + ver
    else:
      logging.info("Could not install version {0} of package {1}, installing latest".format(FLAGS.facebook5_deps_ubuntu_numactl_vm_group1_ver, "numactl"))
  vm.InstallPackages(pkg)
  INSTALLED_PACKAGES[GROUP_NAME].append(pkg_dict)
