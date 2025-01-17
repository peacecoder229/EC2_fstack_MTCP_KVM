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


"""Module containing sysbench installation and cleanup functions."""
# sysbench 1.0 found at:
# https://github.com/akopytov/sysbench


def _Install(vm):
  """Installs the sysbench package on the VM."""
  vm.InstallPackages('sysbench')


def YumInstall(vm):
  """Installs the sysbench package on the VM."""
  vm.RemoteCommand(
      'curl -s '
      'https://packagecloud.io/install/repositories/akopytov/'
      'sysbench/script.rpm.sh '
      '| sudo bash')
  _Install(vm)


def AptInstall(vm):
  """Installs the sysbench package on the VM."""
  vm.RemoteCommand(
      'curl -s '
      'https://packagecloud.io/install/repositories/akopytov/'
      'sysbench/script.deb.sh '
      '| sudo bash')
  _Install(vm)


def YumUninstall(vm):
  vm.RemoteCommand(
      'sudo rm /etc/yum.repos.d/akopytov_sysbench.repo')


def Uninstall(vm):
  vm.RemoteCommand(
      'sudo rm /etc/apt/sources.list.d/akopytov_sysbench.list')
