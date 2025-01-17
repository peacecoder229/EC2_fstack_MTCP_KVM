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

"""Module containing multilib installation and cleanup functions."""

import logging


def YumInstall(vm):
  """Installs multilib packages on the VM."""
  vm.InstallPackages('glibc-devel.i686 libstdc++-devel.i686')


def AptInstall(vm):
  """Installs multilib packages on the VM."""
  deps = ['gcc-multilib', 'g++-multilib']
  arch = vm.CheckLsCpu().data["Vendor ID"]
  logging.info('Checking the architecture: {}'.format(arch))
  if arch == 'ARM':
    deps = [item + '-arm-linux-gnueabi' for item in deps]
  vm.InstallPackages(' '.join(deps))
