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

"""Module to install, uninstall, and parse results for SPEC CPU 2017.
"""

import itertools
import logging
import os
import posixpath

from perfkitbenchmarker import data
from perfkitbenchmarker import errors
from absl import flags
from perfkitbenchmarker.linux_packages import build_tools

FLAGS = flags.FLAGS

_VM_STATE_ATTR = 'speccpu_vm_state'


class SpecInstallConfigurations(object):
  """Configs for SPEC CPU run that must be preserved between PKB stages.

  Specifies directories to look for install files and tracks install locations.

  An instance of this class is attached to the VM as an attribute and is
  therefore preserved as part of the pickled BenchmarkSpec between PKB stages.

  Each attribute represents a possible file or directory that may be created on
  the remote machine as part of running the benchmark.

  Attributes:
    benchmark_name: String. Either speccpu2006 or speccpu2017.
    cfg_file_path: Optional string. Path of the cfg file on the remote machine.
    base_mount_dir: Optional string. Base directory where iso file is mounted.
    mount_dir: Optional string. Path where the iso file is mounted on the
        remote machine.
    base_spec_dir: Optional string. Base directory where spec files are located.
    spec_dir: Optional string. Path of a created directory on the remote machine
        where the SPEC files are stored.
    base_iso_file_path: Optional string. Base directory of iso file.
    iso_file_path: Optional string. Path of the iso file on the remote machine.
    base_tar_file_path: Optional string. Base directory of tar file.
    tar_file_path: Optional string. Path of the tar file on the remote machine.
    required_members: List. File components that must exist for spec to run.
  """

  def __init__(self):
    self.benchmark_name = None
    self.cfg_file_path = None
    self.base_mount_dir = None
    self.mount_dir = None
    self.base_spec_dir = None
    self.spec_dir = None
    self.base_iso_file_path = None
    self.iso_file_path = None
    self.base_tar_file_path = None
    self.tar_file_path = None
    self.required_members = None


def _UploadFileToScratchDir(vm, base_file_path):
  """ Uploads the specified file into the scratch dir. Return
      full path to file in scratch dir.
  """
  scratch_dir = vm.GetScratchDir()
  vm.PushFile(data.ResourcePath(base_file_path), scratch_dir)
  return posixpath.join(scratch_dir, base_file_path)


def _CopyFileToScratchDir(vm, base_file_path):
  """ Copies pre-provisioned (in cloud storage) file to scratch
      dir. Return full path to file in scratch dir.
  """
  speccpu_vm_state = getattr(vm, _VM_STATE_ATTR, None)
  scratch_dir = vm.GetScratchDir()
  vm.InstallPreprovisionedBenchmarkData(speccpu_vm_state.benchmark_name,
                                        [base_file_path],
                                        scratch_dir)
  return posixpath.join(scratch_dir, base_file_path)


def _InstallDependencies(vm):
  vm.InstallPackages('numactl build-essential gawk unzip autoconf automake libtool gcc g++')
  vm.Install('fortran')
  vm.Install('build_tools')
  vm.Install('multilib')


def _MountISO(vm, mount=True):
  """ Mount or Un-mount the ISO """
  scratch_dir = vm.GetScratchDir()
  speccpu_vm_state = getattr(vm, _VM_STATE_ATTR, None)
  mount_dir = posixpath.join(
      scratch_dir, speccpu_vm_state.base_mount_dir)
  if mount:
    vm.RemoteCommand('mkdir -p {0}'.format(mount_dir))
    vm.RemoteCommand('sudo mount -t iso9660 -o loop {0} {1}'.format(
        speccpu_vm_state.iso_file_path, mount_dir))
  else:
    vm.RemoteCommand('sudo umount {0}'.format(mount_dir))
    vm.RemoteCommand('rmdir {0}'.format(mount_dir))
  return mount_dir


def _InstallFromISO(vm, install=True):
  """ Install or Un-install SPECCPU """
  speccpu_vm_state = getattr(vm, _VM_STATE_ATTR, None)
  install_dir = speccpu_vm_state.spec_dir
  mount_dir = speccpu_vm_state.mount_dir
  if install:
    vm.RemoteCommand('cd {0} && ./install.sh -d {1} -f'.format(mount_dir, install_dir))
  else:
    vm.RemoteCommand('sudo rm -rf {0}'.format(install_dir))


def _OverlayPreBuilt(vm):
  """ Extracts pre-built binaries in tar file over the SPECCPU installation """
  speccpu_vm_state = getattr(vm, _VM_STATE_ATTR, None)
  vm.RemoteCommand('cd {install_dir} && tar -xvf {tar} && chmod +x *.sh'
                   .format(install_dir=speccpu_vm_state.spec_dir,
                           tar=speccpu_vm_state.tar_file_path))


def Install(vm, speccpu_vm_state):
  """Installs SPEC 2017 on the target vm.

  Args:
    vm: Vm on which speccpu is installed.
    speccpu_vm_state: SpecInstallConfigurations. Install configuration for spec.
  """
  setattr(vm, _VM_STATE_ATTR, speccpu_vm_state)
  scratch_dir = vm.GetScratchDir()
  vm.RemoteCommand('chmod 751 {0}'.format(scratch_dir))
  speccpu_vm_state.spec_dir = \
      posixpath.join(scratch_dir, speccpu_vm_state.base_spec_dir)
  try:
    speccpu_vm_state.iso_file_path = \
        _UploadFileToScratchDir(vm, speccpu_vm_state.base_iso_file_path)
  except:
    speccpu_vm_state.iso_file_path = \
        _CopyFileToScratchDir(vm, speccpu_vm_state.base_iso_file_path)
  try:
    speccpu_vm_state.tar_file_path = \
        _UploadFileToScratchDir(vm, speccpu_vm_state.base_tar_file_path)
  except:
    speccpu_vm_state.tar_file_path = \
        _CopyFileToScratchDir(vm, speccpu_vm_state.base_tar_file_path)
  _InstallDependencies(vm)
  speccpu_vm_state.mount_dir = \
      _MountISO(vm)
  _InstallFromISO(vm)
  _OverlayPreBuilt(vm)


def Uninstall(vm):
  """Removes SPECCPU from the target vm.

  Args:
    vm: The vm on which SPECCPU is uninstalled.
  """
  _InstallFromISO(vm, False)
  _MountISO(vm, False)
  speccpu_vm_state = getattr(vm, _VM_STATE_ATTR, None)
  vm.RemoteCommand('rm {0}'.format(speccpu_vm_state.iso_file_path))
  vm.RemoteCommand('rm {0}'.format(speccpu_vm_state.tar_file_path))
