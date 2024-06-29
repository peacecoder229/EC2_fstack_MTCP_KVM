from perfkitbenchmarker import vm_util
from absl import flags


def YumInstall(head_node):
  vms = [head_node] + head_node.compute_nodes

  node_file = '{0}        # role: head'.format(head_node.hostname)
  for vm in head_node.compute_nodes:
    node_file += '\n{0}        # role: compute'.format(vm.hostname)

  suppressFile = '/opt/intel/clck/2019.8/etc/clck.xml'
  addSuppress = ('\\\n\t<suppressions>\\\n\t\t<suppress>\\\n\t\t\t<id>ethtool-data-error</id>'
                 '\\\n\t\t</suppress>\\\n\t</suppressions>\\\n')

  for vm in vms:
    cmds = [
        'echo "{0}" | sudo tee -a /tmp/nodefile'.format(node_file),
        'echo "\nexport PATH=$PATH:/opt/intel" | sudo tee -a /etc/bash.bashrc',
        "echo -e '\nPATH=/opt/intel/intelpython2/bin/:$PATH' | tee -a ~/.bashrc",
        "echo -e '\nPATH=/opt/intel/intelpython3/bin/:$PATH' | tee -a ~/.bashrc",
        "echo -e '\nsource /opt/intel/psxe_runtime/linux/bin/psxevars.sh' | tee -a ~/.bashrc",
        "echo -e '\nsource /opt/intel/psxe_runtime/linux/mpi/intel64/bin/mpivars.sh' "
        " | tee -a ~/.bashrc",
        "echo -e '\nsource /opt/intel/psxe_runtime/linux/mkl/bin/mklvars.sh intel64' "
        " | tee -a ~/.bashrc",
        "echo -e '\nPATH=/usr/sbin:$PATH' | tee -a ~/.bashrc",
        "sudo sed -i '41i {addSuppress}'  {suppressFile}".format(suppressFile=suppressFile,
                                                                 addSuppress=addSuppress)]
    vm.RemoteCommand(" && ".join(cmds))

    if flags.FLAGS.aws_efa:
      vm.RemoteCommand("echo -e '\nFI_PROVIDER=efa' | tee -a ~/.bashrc")


def AptInstall(head_node):
  raise Exception("APT base installer not available for Cluster Checker")
