"""Module containing hhvm installation and cleanup functions."""


"""
hhvm_provisioning/hhvm/hhvm_install.yml

#This playbook will add the HHVM repository to your source list and will
#install the last available version of HHVM
---
- name: Add HHVM repository key
  apt_key: keyserver={{hhvm_repo_keyserver}} id={{hhvm_repo_keyserver_id}}
  become: yes

- name: Add HHVM repository
  apt_repository: repo={{hhvm_repo}} state=present
  become: yes

- name: Install HHVM
  apt: name='hhvm' state=present
  become: yes
  """


def YumInstall(vm):
  """Not implemented."""
  raise NotImplementedError('Unsupported Package Manager')


def AptInstall(vm):
  """Installs the hhvm package on the VM."""
  """
  From: https://docs.hhvm.com/hhvm/installation/linux

  apt-get update
  apt-get install software-properties-common apt-transport-https
  apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xB4112585D386EB94

  add-apt-repository https://dl.hhvm.com/ubuntu
  apt-get update
  apt-get install hhvm
  """
  vm.InstallPackages('software-properties-common apt-transport-https')
  cmds = ['sudo apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xB4112585D386EB94',
          'sudo add-apt-repository https://dl.hhvm.com/ubuntu',
          'sudo apt-get update']
  vm.RemoteHostCommand(' && '.join(cmds))
  vm.InstallPackages('hhvm')
