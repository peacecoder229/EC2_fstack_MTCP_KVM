# Copyright 2018 PerfKitBenchmarker Authors. All rights reserved.
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

"""Module to install dependencies for AIBench"""

PYTHON_PKGS = ['PyYAML==5.1', 'numpy==1.16.4']
CENTOS_PKGS = ['python-pip', 'git', 'numactl', 'python36']
UBUNTU_PKGS = ['python-pip', 'git', 'numactl', 'python', 'python3.6']


def _Install(vm):
  """Installs python packages on VM"""
  vm.RemoteHostCommand('sudo pip install setuptools')
  for pkg in PYTHON_PKGS:
    vm.RemoteHostCommand('sudo pip install {pkg}'.format(pkg=pkg))
  vm.Install('aws_credentials')
  vm.Install('awscli')


def YumInstall(vm):
  """Installs required packages on CentOS VM."""
  vm.InstallEpelRepo()
  vm.InstallPackages('centos-release-scl')
  for pkg in CENTOS_PKGS:
    vm.RemoteHostCommand('sudo yum install -y {pkg}'.format(pkg=pkg))
  _Install(vm)


def AptInstall(vm):
  """Installs required packages on Ubuntu VM."""
  vm.RemoteHostCommand("sudo apt-get install -y software-properties-common")
  vm.RemoteHostCommand("sudo add-apt-repository ppa:deadsnakes/ppa")
  vm.RemoteHostCommand("sudo apt-get update")
  vm.RemoteHostCommand("sudo apt-get install -y gcc")
  for pkg in UBUNTU_PKGS:
    vm.RemoteHostCommand("sudo apt-get install -y {pkg}".format(pkg=pkg))
  _Install(vm)
