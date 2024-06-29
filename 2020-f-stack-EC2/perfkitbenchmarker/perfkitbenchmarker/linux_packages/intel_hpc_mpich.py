from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import intel_hpc_utils

MPI_VERSION = '3.3'
MPI_512_HASH = ('1ed6d8d30db4923fd1bd39b6e9622f0db939a45edf8d9f8bdbccfa619fde7f'
                'b920c5a0d3f2442f0dd63cf8fda823dbd2983ac5f7c16308bc79e04f61d8e119be')


def Install(head_node):
  if intel_hpc_utils.IsTemplateVm(head_node):
    vms = [head_node]
  else:
    vms = [head_node] + head_node.compute_nodes

  names = ["head_node"]

  # Install build dependencies
  vm_util.RunThreaded(lambda vm: vm.Install('build_tools'), vms)
  vm_util.RunThreaded(lambda vm: vm.InstallPackages('wget'), vms)

  cmds = [
      'cd {0}'.format(INSTALL_DIR),
      'wget -q http://www.mpich.org/static/downloads/{v}/mpich-{v}.tar.gz'.format(v=MPI_VERSION)
  ]
  cmd = ' && '.join(cmds)
  vm_util.RunThreaded(lambda vm: vm.RemoteCommand(cmd), vms)

  for vm in vms:
    hash, _ = vm.RemoteCommand('sha512sum {0}/mpich-{v}.tar.gz | cut -d " " -f 1'
                               .format(INSTALL_DIR, v=MPI_VERSION))
    # Install MPICH on all nodes
    if MPI_512_HASH == hash.strip():
      cmds = [
          'cd {0}'.format(INSTALL_DIR),
          'tar xvf mpich-{0}.tar.gz'.format(MPI_VERSION),
          'cd {0}/mpich-{1}'.format(INSTALL_DIR, MPI_VERSION),
          './configure --disable-fortran',
          'make -j `cat /proc/cpuinfo | grep processor | wc -l`',
          'sudo make install'
      ]
      cmd = ' && '.join(cmds)
      vm.RemoteCommand(cmd)
    else:
      raise Exception('MPICH hashes do not correspond to each other')

  for name in names:
    head_node.RemoteCommand("ssh-keyscan {0} >> ~/.ssh/known_hosts".format(name))
