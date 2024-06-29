"""Module containing composer installation and cleanup functions."""


"""
hhvm_provisioning/hhvm/roles/composer/tasks/main.yml
---
- name: Create download folder for composer
  file:
   path: "{{download_dir}}"
   state: directory

- name: Downloading composer
  get_url:
   url: http://getcomposer.org/installer
   dest: "{{download_dir}}/composer-setup.php"

- name: Install composer
  shell: cd {{download_dir}} && php composer-setup.php

- name: Copy composer to /usr/bin
  shell: cp {{download_dir}}/composer.phar /usr/bin #Get the var file and make this dynamic
  become: yes
"""


def YumInstall(vm):
  """Not implemented."""
  raise NotImplementedError('Unsupported Package Manager')


def AptInstall(vm):
  """Installs the composer package on the VM."""
  """
  Reference: https://getcomposer.org/doc/faqs/how-to-install-composer-programmatically.md
  """
  cmds = ['curl -SL https://getcomposer.org/installer -o composer-setup.php',
          'php composer-setup.php --quiet',
          'sudo cp composer.phar /usr/bin/']
  vm.RemoteHostCommand(' && '.join(cmds))
