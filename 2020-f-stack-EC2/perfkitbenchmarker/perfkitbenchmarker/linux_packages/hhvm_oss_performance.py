"""Module containing HHVM oss-performance package installation and cleanup functions."""


"""
hhvm_provisioning/hhvm/roles/oss-performance/tasks/main.yml
---
- name: Clone oss-performance
  git:
   repo: 'https://github.com/hhvm/oss-performance'
   dest: "{{git_dir}}/oss-performance"

- name: Prepare composer
  shell: cp {{download_dir}}/composer.phar {{git_dir}}/oss-performance

- name: Install oss-performance
  shell: cd {{git_dir}}/oss-performance && hhvm composer.phar install
  become: yes

- name: Get siege
  get_url:
   url: http://download.joedog.org/siege/{{siege_pk_name}}
   dest: "{{download_dir}}"

- name: Extract and install siege
  shell: |
    cd {{download_dir}}
    tar xzvf {{siege_pk_name}}
    cd {{siege_dir}}
    ./configure
    make
    make install
  become: yes

"""


def YumInstall(vm):
  """Not implemented."""
  raise NotImplementedError('Unsupported Package Manager')


def AptInstall(vm):
  """Installs the HHVM oss-performance package and dependencies on the VM."""
  """
  Also Reference: https://github.com/hhvm/oss-performance/blob/master/scripts/setup.sh
  """
  cmds = ['git clone https://github.com/hhvm/oss-performance',
          'cp composer.phar oss-performance',
          'cd oss-performance',
          'sudo hhvm composer.phar install']
  vm.RemoteHostCommand(' && '.join(cmds))

  """
  Install Siege
  Also Reference: https://www.linode.com/docs/tools-reference/tools/load-testing-with-siege/
  """
  cmds = ['curl -SL http://download.joedog.org/siege/siege-latest.tar.gz -o siege-latest.tar.gz',
          'tar -xzvf siege-latest.tar.gz',
          'cd siege-*/',
          './configure',
          'make',
          'sudo make install']
  vm.RemoteHostCommand(' && '.join(cmds))
