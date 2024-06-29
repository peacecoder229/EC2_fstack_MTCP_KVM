"""Module containing ansible installation"""

from perfkitbenchmarker import os_types


def YumInstall(vm):
  vm.InstallEpelRepo()
  vm.InstallPackages('ansible')


def AptInstall(vm):
  if vm.OS_TYPE == os_types.UBUNTU2004:
    vm.RemoteHostCommand('sudo apt-get update')
  else:
    cmds = ['sudo add-apt-repository ppa:ansible/ansible',
            'sudo apt-get update']
    vm.RemoteHostCommand(' && '.join(cmds))
  vm.InstallPackages('ansible')


def SwupdInstall(vm):
  vm.InstallPackages('ansible')
