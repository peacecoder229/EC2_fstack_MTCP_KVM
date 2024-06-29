"""Module containing Phoronix Test Suite installation, cleanup, parsing functions."""
import logging

from perfkitbenchmarker import errors
from absl import flags
from perfkitbenchmarker import vm_util
from perfkitbenchmarker.linux_packages import INSTALL_DIR

GIT_REPO = 'https://github.com/phoronix-test-suite/phoronix-test-suite.git'
GIT_TAG = 'v8.6.1'


def _GetInstallList(base_os_type):
  """This avoids separate methods for each package manager and should be easier to template"""
  """Add BASE_OS_TYPE and package list here"""
  switcher = {
      "debian": "php-cli php-xml php-gd git zip",
      "rhel": "php-cli php-xml php-json php-gd git zip",
      "clear": "phoronix-test-suite"
  }
  return switcher.get(base_os_type, None)


def Install(vm):
  """Install PTS and dependencies"""
  pkg_list = _GetInstallList(vm.BASE_OS_TYPE)
  if pkg_list:
    vm.InstallPackages(pkg_list)
  else:
    logging.error("{0} is not supported by this package.".format(vm.BASE_OS_TYPE))
  """Clone into home directory"""
  vm.RemoteCommand("git clone {0}".format(GIT_REPO))
  vm.RemoteCommand("cd phoronix-test-suite && git checkout {0}".format(GIT_TAG))
  vm.RemoteCommand("cd phoronix-test-suite && sudo ./install-sh")


def Uninstall(vm):
  # We are in the user's home dir
  vm.RemoteCommand('rm -rf phoronix-test-suite; rm -rf .phoronix-test-suite')
