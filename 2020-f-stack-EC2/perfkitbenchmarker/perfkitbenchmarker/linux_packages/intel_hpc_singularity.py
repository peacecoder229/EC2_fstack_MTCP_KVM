from perfkitbenchmarker.linux_packages import INSTALL_DIR
from absl import flags


FLAGS = flags.FLAGS

flags.DEFINE_string('intel_hpc_go_version', '1.13', 'GO Version')
flags.DEFINE_string('intel_hpc_singularity_version', '3.5.0', 'Singlarity Version')

OS_TYPE = 'linux'
ARCH = 'amd64'


def Install(vm):
  """Install singularity on the VM."""

  # pre-reqs
  vm.Install('build_tools')
  vm.InstallPackages('wget cryptsetup openssl-devel libuuid-devel')
  # install singularity
  cmds = [
      'cd {0}'.format(INSTALL_DIR),
      'wget https://dl.google.com/go/go{0}.{1}-{2}.tar.gz'.format(FLAGS.intel_hpc_go_version,
                                                                  OS_TYPE, ARCH),
      'sudo tar -C /usr/local -xzvf go{0}.{1}-{2}.tar.gz'.format(FLAGS.intel_hpc_go_version,
                                                                 OS_TYPE, ARCH),
      'echo "export PATH=/usr/local/go/bin:$PATH" >> ~/.bashrc',
      'source ~/.bashrc',

      'cd {0}'.format(INSTALL_DIR),
      'wget https://github.com/hpcng/singularity/releases/download/v{0}/'
      'singularity-{0}.tar.gz'.format(FLAGS.intel_hpc_singularity_version),
      'tar -xzf singularity-{0}.tar.gz'.format(FLAGS.intel_hpc_singularity_version),
      'cd {0}/singularity'.format(INSTALL_DIR),
      './mconfig',
      'make -C builddir',
      'sudo make -C builddir install'
  ]
  vm.RemoteCommand(' && '.join(cmds))
