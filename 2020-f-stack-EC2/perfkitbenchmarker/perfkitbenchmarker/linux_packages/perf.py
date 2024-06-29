"""Module for installing the Perf package"""

from perfkitbenchmarker.linux_packages import INSTALL_DIR

APT_PACKAGES = ('linux-tools-common '
                'linux-tools-generic linux-tools-`uname -r`')


def AptInstall(vm):
  """Installs the perf package on the VM."""
  vm.InstallPackages(APT_PACKAGES)


def YumInstall(vm):
  """Raises exception when trying to install on yum-based VMs"""
  raise NotImplementedError(
      'PKB currently only supports the installation of perf on '
      'Debian-based VMs')
