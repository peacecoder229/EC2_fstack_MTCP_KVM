import datetime
import json
import logging
import time
from absl import flags
from perfkitbenchmarker import configs
from perfkitbenchmarker import sample
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import intel_hpc_utils
from perfkitbenchmarker.providers.gcp import util

FLAGS = flags.FLAGS
flags.DEFINE_integer('intel_hpc_head_node_nodes', '1', 'The number of nodes to use', lower_bound=1)
flags.DEFINE_string('intel_hpc_head_node_image_type', 'avx512', 'Image type for head_node')
flags.DEFINE_string('intel_hpc_head_node_image_version', 'July', 'Image version for head_node')
flags.DEFINE_string('intel_hpc_head_node_fss_type', 'FSX', 'File Shared System type: FSX or NFS')
flags.DEFINE_boolean('intel_hpc_head_node_CC', False, 'If benchmark runs or not with Cluster Checker')

BENCHMARK_NAME = 'intel_hpc_head_node'
BENCHMARK_CONFIG = """
intel_hpc_head_node:
  description: Runs HPC head_node
  vm_groups:
    head_node:
      os_type: centos7
      vm_spec:
        AWS:
          machine_type: c5.9xlarge
          zone: us-east-2
          image: null
          boot_disk_size: 200
        GCP:
          machine_type: n1-highcpu-36
          zone: us-central1-a
          image: null
          boot_disk_size: 200
        Azure:
          machine_type: Standard_F72s_v2
          zone: eastus2
          image: null
          boot_disk_size: 200
    compute_nodes:
      os_type: centos7
      vm_spec:
        AWS:
          machine_type: c5.18xlarge
          zone: us-east-2
          image: null
          boot_disk_size: 200
        GCP:
          machine_type: n1-highcpu-96
          zone: us-central1-a
          image: null
          boot_disk_size: 200
        Azure:
          machine_type: Standard_F72s_v2
          zone: eastus2
          image: null
          boot_disk_size: 200
  flags:
    enable_transparent_hugepages: false
"""
workload = "head_node"


###############################################################################
def CheckPrerequisites(config):
  intel_hpc_utils.CheckPrerequisites(workload)


def GetConfig(user_config):
  # Load the benchmark configuration
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
  config = intel_hpc_utils.GetConfig(config, FLAGS.intel_hpc_head_node_nodes)
  return config


def Prepare(benchmark_spec):
  logging.info("Intel HPC Prepare")
  intel_hpc_utils.Prepare(benchmark_spec, 1, workload, FLAGS.intel_hpc_head_node_image_type,
                          FLAGS.intel_hpc_head_node_image_version, FLAGS.intel_hpc_head_node_fss_type,
                          FLAGS.intel_hpc_head_node_CC, FLAGS.cloud)


def Run(benchmark_spec):
  logging.info("Intel HPC Run")
  vm = benchmark_spec.vms[0]
  timestamp = datetime.datetime.today().strftime("%Y%m%d%H%M%S%f")
  final_image_id = ""

  # Make sure that everyhing is saved from RAM to DISK!
  # Otherwise the image might save with corrupted files
  vm.RemoteCommand("sudo sync")

  if FLAGS.cloud == 'AWS':
    instance_id = vm.id
    region = vm.region
    # Create the image
    image_state_available = False
    while not image_state_available:
      # Trigger the image snapshot creation
      cmd = 'aws ec2 create-image --instance-id {0} --name HPC_TPL_{1}_{2} --description HPC_TEMPLATE ' \
            '--no-reboot --region {3}'.format(instance_id, FLAGS.run_uri, timestamp, region).split(" ")
      out, _, _ = vm_util.IssueCommand(cmd)
      image_id = json.loads(out.strip())
      image_id = json.loads(json.dumps(image_id))

      # Wait for the image to become available
      available = False
      cmd = 'aws ec2 describe-images --owners self --region {0}'.format(region).split(" ")
      while not available:
        stdout, _, _ = vm_util.IssueCommand(cmd)
        image_details = json.loads(stdout)
        image_details = json.loads(json.dumps(image_details))
        for image in image_details['Images']:
          if image_id['ImageId'] in image['ImageId']:
            if image['State'] == 'pending':
              time.sleep(10)
            elif image['State'] == 'available':
              available = True
              image_state_available = True
              final_image_id = "{0}".format(image_id['ImageId'])
            elif image['State'] == 'failed':
              cmd = 'aws ec2 deregister-image --image-id {0} --region us-east-2'.format(
                  image_id).split(" ")
              vm_util.IssueCommand(cmd)
              break
  elif FLAGS.cloud == 'Azure':
    # sudo is mandatory
    vm.RemoteCommand('sudo waagent -deprovision+user -force')

    # Make a backup resource group for Azure Image
    backup_group = 'HPC_Template_{0}'.format(timestamp)
    vm_util.IssueCommand('az group create -l {0} -n {1}'.format(vm.zone, backup_group).split())

    # Azure vm info
    powerstate = 'VM deallocating'
    azure_image_id = ""
    resourcegroup_name = ""
    vm_name = ""
    cmd = 'az group list'.split()
    out, _, _ = vm_util.IssueCommand(cmd)
    azure_groups = json.loads(out.strip())
    azure_groups = json.loads(json.dumps(azure_groups))
    for group in azure_groups:
      if FLAGS.run_uri in group['name']:
        resourcegroup_name = group['name']

    cmd = 'az vm list'.split()
    out, _, _ = vm_util.IssueCommand(cmd)
    azure_vms = json.loads(out.strip())
    azure_vms = json.loads(json.dumps(azure_vms))
    for az_vm in azure_vms:
      if FLAGS.run_uri in az_vm['name']:
        vm_name = az_vm['name']

    # Make the image itself
    # WARNING: The deallocate command will shutdown the VM!
    image_name = 'HPC_TPL_{0}_{1}'.format(FLAGS.run_uri, timestamp)
    vm_util.IssueCommand('az vm deallocate -g {0} -n {1}'.format(resourcegroup_name, vm_name).split(), timeout=None)

    # Make sure it waits untill vm is deallocated
    while powerstate == 'VM deallocating':
      time.sleep(30)
      cmd = 'az vm list -d'.split()
      out, _, _ = vm_util.IssueCommand(cmd)
      azure_vms = json.loads(out.strip())
      azure_vms = json.loads(json.dumps(azure_vms))
      for az_vm in azure_vms:
        if vm_name == az_vm['name']:
          powerstate = az_vm['powerState']

    vm_util.IssueCommand('az vm generalize -g {0} -n {1}'.format(resourcegroup_name, vm_name).split())
    vm_util.IssueCommand('az image create --name {0} -g {1} --source {2} --l {3}'
                         .format(image_name, resourcegroup_name, vm_name, vm.zone).split())

    # Move the image to the backup group because
    # the original resource group will be deleted with the vm
    cmd = 'az image list'.split()
    out, _, _ = vm_util.IssueCommand(cmd)
    azure_images = json.loads(out.strip())
    azure_images = json.loads(json.dumps(azure_images))
    for image in azure_images:
      if image['name'] == image_name:
        azure_image_id = image['id']

    vm_util.IssueCommand('az resource move --destination-group {0} --ids {1}'
                         .format(backup_group, azure_image_id).split())

    # Get the final id of image
    cmd = 'az image list'.split()
    out, _, _ = vm_util.IssueCommand(cmd)
    azure_images = json.loads(out.strip())
    azure_images = json.loads(json.dumps(azure_images))
    for image in azure_images:
      if image['name'] == image_name:
        final_image_id = image['id']
  elif FLAGS.cloud == 'GCP':
    image_name = 'hpc-tpl-{0}-{1}'.format(FLAGS.run_uri, timestamp)
    cmd = 'gcloud compute instances describe {0} --format json --quiet --project {1} --zone {2}'\
          .format(vm.name, util.GetDefaultProject(), vm.zone).split(" ")

    out, _, _ = vm_util.IssueCommand(cmd)
    disks = json.loads(out.strip())
    disks = json.loads(json.dumps(disks))
    disks = disks['disks']
    for diskInfo in disks:
       sourceDisk = diskInfo['source']

    # Create the image
    logging.info("Creating the image")
    cmd = 'gcloud compute images create {0} --source-disk {1} ' \
          '--source-disk-zone {2} --force'.format(image_name, sourceDisk, vm.zone).split(" ")
    out, _, _ = vm_util.IssueCommand(cmd)
    final_image_id = image_name

  # Print the Azure Image id to the user
  logging.info("=" * 80)
  logging.info("IMAGE ID = {0}".format(final_image_id))
  logging.info("=" * 80)

  # We need to return something.
  # With this you can run all the stages from the benchmark
  return [sample.Sample("IMAGE ID", 0, final_image_id, {})]


def Cleanup(benchmark_spec):
  logging.info("Intel HPC Clean")
