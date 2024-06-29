from perfkitbenchmarker import vm_util
from absl import flags
import time

FLAGS = flags.FLAGS


def _Install(head_node, nfs_service_name):
  vms = [head_node] + head_node.compute_nodes

  # Install build dependencies
  vm_util.RunThreaded(lambda vm: vm.Install('build_tools'), vms)
  set_memory = "*            hard   memlock           unlimited\n*            soft    memlock           unlimited"
  MNT_DIR = "/scratch"
  # To make nfs work with Azure, we need to stop the firewall
  if FLAGS.cloud == 'Azure':
    cmds = [
        'sudo service firewalld stop'
    ]
    cmd = ' && '.join(cmds)
    vm_util.RunThreaded(lambda computeNode: computeNode.RemoteCommand(cmd), vms)

  # Append entries to /etc/security/limits.conf
  cmds = [
      'sudo cp /etc/security/limits.conf /etc/security/limits_backup.conf',
      'sudo cp /etc/exports /etc/exports_backup',
      'echo "{0}" | sudo tee -a /etc/security/limits.conf'.format(set_memory),
      'echo "{0} *(rw,sync,no_root_squash,no_subtree_check)" | sudo tee -a /etc/exports'
      .format(MNT_DIR),
      'sudo exportfs -a',
      'sudo systemctl restart {0}'.format(nfs_service_name),
      'sudo chmod 775 -R {0}'.format(MNT_DIR)
  ]
  head_node.RemoteCommand(' && '.join(cmds))

  # Mount the NFS share on all compute_nodes
  cmds = [
      'sudo cp /etc/security/limits.conf /etc/security/limits_backup.conf',
      'echo "{0}" | sudo tee -a /etc/security/limits.conf'.format(set_memory),
      'sudo mount -t nfs node1:{0} {0}'.format(MNT_DIR),
      'echo "head_node:{0} {0} nfs" | sudo tee -a /etc/fstab'.format(MNT_DIR),
      'sudo chmod 775 -R {0}'.format(MNT_DIR)
  ]
  cmd = ' && '.join(cmds)
  vm_util.RunThreaded(lambda computeNode: computeNode.RemoteCommand(cmd), head_node.compute_nodes)


def YumInstall(head_node):
  vms = [head_node] + head_node.compute_nodes
  vm_util.RunThreaded(lambda vm: vm.InstallPackages('nfs-utils nfs-utils-lib wget'), vms)
  _Install(head_node, "nfs-server")


def AptInstall(head_node):
  vms = [head_node] + head_node.compute_nodes
  head_node.InstallPackages('nfs-kernel-server')
  vm_util.RunThreaded(lambda vm: vm.InstallPackages('nfs-common'), vms)
  _Install(head_node, "nfs-kernel-server")
