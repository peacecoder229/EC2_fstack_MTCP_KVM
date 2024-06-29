import json
import logging
import time
from perfkitbenchmarker import vm_util


FSX_INSTALL_CMDS = ['sudo wget https://fsx-lustre-client-repo-public-keys.s3.amazonaws.com/'
                    'fsx-rpm-public-key.asc -O /tmp/fsx-rpm-public-key.asc',
                    'sudo rpm --import /tmp/fsx-rpm-public-key.asc',
                    'sudo wget https://fsx-lustre-client-repo.s3.amazonaws.com/el/7/'
                    'fsx-lustre-client.repo -O /etc/yum.repos.d/aws-fsx.repo',
                    'sudo yum install -y kmod-lustre-client lustre-client']


# We cannot import intel_hpc_utils because then we get a circullar refference error
def _IsTemplateVm(vm):
  MARKER_FILE = "/opt/INTEL_HPC_TEMPLATE"
  _, _, retcode = vm.RemoteCommandWithReturnCode('file -f {0}'.format(MARKER_FILE),
                                                 ignore_failure=True, suppress_warning=True)
  marker_found = retcode == 0
  if marker_found:
    logging.info("Marker file for template found")
  else:
    logging.info("Marker file for template not found")
  return marker_found


def _Install(head_node):
  vms = [head_node] + head_node.compute_nodes

  capacity = '1200'
  subnet = head_node.network.subnet.id
  region = head_node.region

  # these are required to make the package portable for ANY workload
  vm_util.RunThreaded(lambda vm: vm.Install('aws_credentials'), vms)
  vm_util.RunThreaded(lambda vm: vm.Install('awscli'), vms)

  head_node.RemoteCommand(
      'aws fsx create-file-system --file-system-type LUSTRE --storage-capacity {0} '
      '--subnet-ids {1} --region {2} --output json'.format(capacity, subnet, region))

  # FSX needs time to create the file shared system: ~10min
  availability = True
  while availability:
    stdout, _ = head_node.RemoteCommand('aws fsx describe-file-systems --output json --region {0}'
                                        .format(head_node.region))
    file_system_details = json.loads(stdout)
    file_system_details = json.loads(json.dumps(file_system_details))
    for filesystem in file_system_details['FileSystems']:
      if subnet in filesystem['SubnetIds']:
        if filesystem['Lifecycle'] == 'CREATING':
          time.sleep(20)
        else:
          availability = False

  MNT_DIR = "/scratch"

  for vm in vms:
    vm.RemoteCommand('cd {0} && sudo chown -R ${{USER:=$(/usr/bin/id -run)}}:$USER  {0}'.
                     format(MNT_DIR))
    stdout, _ = head_node.RemoteCommand('aws fsx describe-file-systems --output json --region {0}'
                                        .format(head_node.region))
    file_system_details = json.loads(stdout)
    file_system_details = json.loads(json.dumps(file_system_details))
    for filesystem in file_system_details['FileSystems']:
      if subnet in filesystem['SubnetIds']:
        vm.RemoteCommand('sudo mount -t lustre {0}@tcp:/fsx /scratch'.format(filesystem['DNSName']))


def YumInstall(head_node):
  if not _IsTemplateVm(head_node):
    vms = [head_node] + head_node.compute_nodes
    vm_util.RunThreaded(lambda vm: vm.InstallEpelRepo(), vms)
    vm_util.RunThreaded(lambda vm: vm.RemoteCommand(" && ".join(FSX_INSTALL_CMDS)), vms)
    vm_util.RunThreaded(lambda vm: vm.Reboot(), vms)
  _Install(head_node)


def AptInstall(head_node):
  pass


def Uninstall(head_node):
  vms = [head_node] + head_node.compute_nodes
  stdout, _ = head_node.RemoteCommand('aws fsx describe-file-systems --output json --region {0}'
                                      .format(head_node.region))
  file_system_details = json.loads(stdout)
  file_system_details = json.loads(json.dumps(file_system_details))
  subnet = head_node.network.subnet.id
  for vm in vms:
    vm.RemoteCommand('sudo umount /scratch')
  for filesystem in file_system_details['FileSystems']:
    if subnet in filesystem['SubnetIds']:
      head_node.RemoteCommand('aws fsx delete-file-system --file-system-id {0} --region {1}'
                              .format(filesystem['FileSystemId'], head_node.region))
