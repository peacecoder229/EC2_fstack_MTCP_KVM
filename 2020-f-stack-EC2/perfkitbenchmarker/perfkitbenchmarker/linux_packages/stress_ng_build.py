# Copyright 2014 PerfKitBenchmarker Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Module containing stress-ng installation and cleanup functions."""

import os

from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import os_types
from perfkitbenchmarker import errors


STRESS_NG_DIR = '{0}/stress_ng'.format(INSTALL_DIR)
GIT_REPO = 'https://github.com/ColinIanKing/stress-ng'
STRESS_NG = os.path.join(STRESS_NG_DIR, 'stress-ng')
GIT_TAG = '72c371f69d5b9354bebb9c560cc7bfdc0b60d7c3'  # V0.10.05


def _Install(vm):
  """Installs the stress-ng package on the VM."""
  vm.RemoteCommand('git clone {0} {1}'.format(GIT_REPO, STRESS_NG_DIR))
  vm.RemoteCommand('cd {0} && git checkout {1}'.format(STRESS_NG_DIR, GIT_TAG))
  vm.RemoteCommand('cd {0} && make'.format(STRESS_NG_DIR))


def YumInstall(vm):
  vm.InstallEpelRepo()
  """Installs the stress-ng package on the VM."""
  # for RHEL 7
  if vm.OS_TYPE == os_types.RHEL:
    raise NotImplementedError

  # for CentOS 7
  vm.Install('build_tools')
  vm.InstallPackages('centos-release-scl')
  vm.InstallPackages('devtoolset-8')
  vm.RemoteCommand('echo "source scl_source enable devtoolset-8" >> ~/.bashrc')

  vm.InstallPackages(
      'libaio-devel libattr-devel libbsd-devel'
      'libcap-devel libgcrypt-devel keyutils-libs'
      'libsctp-devel zlib-devel libattr1-dev'
      'libbsd-dev libcap-dev libgcrypt11-dev'
      'libkeyutils-dev libsctp-dev zlib1g-dev'
  )
  _Install(vm)



def AptInstall(vm):
  vm.Install('build_tools')
  # Get the latest version of GCC to build stress-ng
  try:
    # some distributions/versions will have gcc-8 in their default repository
    # vm.InstallPackages('gcc-8')
    # don't use InstallPackages() because it will retry "many" times
    vm.AptUpdate()
    vm.RemoteCommand('sudo DEBIAN_FRONTEND=\'noninteractive\' /usr/bin/apt-get -y install gcc-8')
  except errors.VirtualMachine.RemoteCommandError:
    # some distributions/version will NOT have gcc-8 in their default repository
    vm.RemoteCommand('sudo add-apt-repository ppa:ubuntu-toolchain-r/test -y && '
                     'sudo apt-get update')
    vm.RemoteCommand('sudo apt-get remove gcc -y', ignore_failure=True)
    vm.InstallPackages('gcc-8')

  vm.RemoteCommand('sudo rm /usr/bin/gcc', ignore_failure=True)
  vm.RemoteCommand('sudo ln -s /usr/bin/gcc-8 /usr/bin/gcc')
  vm.InstallPackages(
      'build-essential libaio-dev libapparmor-dev '
      'libattr1-dev libbsd-dev libcap-dev '
      'libkeyutils-dev libsctp-dev zlib1g-dev'
  )
  _Install(vm)
