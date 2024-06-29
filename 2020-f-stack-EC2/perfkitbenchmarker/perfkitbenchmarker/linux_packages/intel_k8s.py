import logging
import posixpath

from perfkitbenchmarker import errors
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import vm_util

INSTALLK8S_TAR = "installk8scsp.tar.gz"
INSTALLK8S_DIR = "{0}/installk8scsp".format(INSTALL_DIR)


def _GetInstallPackage(vm, url):
  """
  Download k8s installation package
  """
  if url:
    dir_name = "internal_resources_installk8s"
    internal_dir = vm_util.PrependTempDir(dir_name)
    vm_util.IssueCommand("mkdir -p {0}".format(internal_dir).split())
    curl_dest_path = posixpath.join(internal_dir, INSTALLK8S_TAR)
    vm_util.IssueCommand("curl -o {0} {1}".format(curl_dest_path, url).split(),
                         timeout=60)
    vm.RemoteCopy(curl_dest_path, INSTALL_DIR)


def InstallK8sCSP(controller_vm, worker_vms, taint_controller=True):
  """
  Install Kubernetes cluster on CSP VMs
  """
  all_ips = [controller_vm.internal_ip]
  for vm in worker_vms:
    all_ips.append(vm.internal_ip)

  vm = controller_vm
  vm.Install('docker_ce')

  sshkey = vm_util.GetPrivateKeyPath()
  vm.RemoteCopy(sshkey, "~/.ssh/id_rsa")

  res = "https://cumulus.s3.us-east-2.amazonaws.com/install_k8s/installk8scsp.tar.gz"
  _GetInstallPackage(vm, res)

  vm.RemoteCommand("cd {0} && tar xfz {1}".format(INSTALL_DIR, INSTALLK8S_TAR))
  vm.RemoteCommand("cd {0} && python3 create_cfg.py {1}".format(
                   INSTALLK8S_DIR, ' '.join(all_ips)))

  logging.info('Setup k8s cluster:')
  vm.RemoteCommand("cd {0} && sudo ./prepare-cluster.sh".format(INSTALLK8S_DIR))
  stdout, _ = vm.RemoteCommand("cd {0} && sudo ./create-cluster.sh".format(INSTALLK8S_DIR))

  if "successfully" not in stdout:
    raise errors.Benchmarks.PrepareException('Kubernetes cluster installation failed!')
  else:
    logging.info('Kubernetes cluster has been installed successfully!')
    if taint_controller:
      stdout, _ = vm.RemoteCommand("kubectl taint nodes node1 controller=true:NoSchedule")
      if "node/node1 tainted" not in stdout:
        raise errors.Benchmarks.PrepareException('Kubernetes controller node taint failed!')
