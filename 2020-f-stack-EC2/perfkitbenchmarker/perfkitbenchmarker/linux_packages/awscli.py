# Copyright 2016 PerfKitBenchmarker Authors. All rights reserved.
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

"""Package for installing the AWS CLI."""

from perfkitbenchmarker import errors


def Install(vm):
  """Installs the awscli package on the VM."""
  vm.InstallPackages('python3-pip')
  vm.RemoteCommand('sudo pip3 install awscli --upgrade')


def YumInstall(vm):
  """Installs the awscli package on the VM."""
  # amazon linux 2 has awscli pre-installed. Check to see if it exists and
  # install it if it does not.
  try:
    vm.RemoteCommand('yum list installed awscli')
  except errors.VirtualMachine.RemoteCommandError:
    if vm.OS_TYPE == 'centos8':
      vm.InstallPackages('python3-pip elfutils-libelf-devel')
      cmd = 'sudo python3 -m pip install awscli'
      stdout, stderr, retcode = vm.RemoteCommandWithReturnCode('{}'.format(cmd), ignore_failure=True)
      if retcode != 0:
        err_str = 'Failed in installing awscli: ' \
                  'cmd ({}), stdout ({]), stderr({}), retcode ({}).' \
                  .format(cmd, stdout, stderr, retcode)
        raise RuntimeError(err_str)
    else:
      Install(vm)


def AptInstall(vm):
  """Installs the awscli package on the VM."""
  Install(vm)


def Uninstall(vm):
  vm.RemoteCommand('/usr/bin/yes | sudo pip3 uninstall awscli')
