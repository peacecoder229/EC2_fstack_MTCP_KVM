import logging
import collections
import yaml
import re
from perfkitbenchmarker import data
from absl import flags
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import flag_util
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker.linux_packages import aws_fsx

FLAGS = flags.FLAGS
CC_NODE_FILE = "/tmp/nodefile"


def MarkVmAsTemplate(vm):
  MARKER_FILE = "/opt/INTEL_HPC_TEMPLATE"
  vm.RemoteCommand("sudo touch {0}".format(MARKER_FILE))


def IsTemplateVm(vm):
  MARKER_FILE = "/opt/INTEL_HPC_TEMPLATE"
  _, _, retcode = vm.RemoteCommandWithReturnCode('file -f {0}'.format(MARKER_FILE),
                                                 ignore_failure=True, suppress_warning=True)
  marker_found = retcode == 0
  if marker_found:
    logging.info("Marker file for template found")
  else:
    logging.info("Marker file for template not found")
  return marker_found


def CheckPrerequisites(workload):
  yaml_data = GetHpcBenchmarksConfig()
  allowed_apps = yaml_data.keys()
  if workload not in allowed_apps:
    raise Exception("{0} not supported. Available ones: {1}".format(workload, str(allowed_apps)))


def GetConfig(pkb_config, intel_hpc_nodes):
  logging.info("Intel HPC GetConfig")
  if not IsClusterMode(intel_hpc_nodes):
    pkb_config["vm_groups"]["head_node"]["vm_count"] = 0
    pkb_config["vm_groups"]["compute_nodes"]["vm_count"] = 1
    logging.info("Running in SINGLE NODE")
  else:
    pkb_config["vm_groups"]["head_node"]["vm_count"] = 1
    pkb_config["vm_groups"]["compute_nodes"]["vm_count"] = intel_hpc_nodes
    logging.info("Running in MULTI NODE")
  return pkb_config


def Prepare(benchmark_spec, nodes, workload, image_type, image_version, fss_type,
            use_cluster_checker, cloud):
  benchmark_spec.software_config_metadata = {
      'benchmark_version': image_version,
      'num_of_nodes': nodes,
      'singularity_version': FLAGS.intel_hpc_singularity_version,
      'go_version': FLAGS.intel_hpc_go_version}

  if workload == "head_node":
    _PrepareHeadNode(benchmark_spec, 1, workload, image_type, fss_type, use_cluster_checker, cloud)
    return

  if IsClusterMode(nodes):
    benchmark_spec.always_call_cleanup = True
    head_node = benchmark_spec.vm_groups['head_node'][0]
    compute_nodes = benchmark_spec.vm_groups['compute_nodes']
    head_node.compute_nodes = compute_nodes
    for compute_node in compute_nodes:
      compute_node.head_node = head_node
    _PrepareMultiNode(head_node, compute_nodes, workload, image_type, image_version, fss_type,
                      use_cluster_checker, cloud)
  else:
    vm = benchmark_spec.vms[0]
    _PrepareSingleNode(vm, workload, image_type, image_version)


def GetNodeArchives(head_node, vm, workload, use_cluster_checker):
  filename = '{intel_hpc_appnames}_results.tar.gz'.format(intel_hpc_appnames=workload)
  archive = '{0}/{filename}'.format(INSTALL_DIR, filename=filename)
  vm.RemoteCommand('tar -czf {archive} -C $HOME/ {intel_hpc_appnames}*'
                   .format(archive=archive, intel_hpc_appnames=workload))
  vm.PullFile(vm_util.GetTempDir(), archive)
  if use_cluster_checker:
    cluster_checker = 'pkb_cluster_checker'
    filename = '{0}_results.tar.gz'.format(cluster_checker)
    archive = '{0}/{filename}'.format(INSTALL_DIR, filename=filename)
    head_node.RemoteCommand('tar -czf {archive} -C $HOME/ {pkb_cluster_checker}*'
                            .format(archive=archive, pkb_cluster_checker=cluster_checker))
    head_node.PullFile(vm_util.GetTempDir(), archive)


def Cleanup(benchmark_spec, nodes, workload, fss_type, cloud, use_cluster_checker):
  if IsClusterMode(nodes):
    head_node = benchmark_spec.vm_groups['head_node'][0]
    vms = [head_node] + head_node.compute_nodes
    _CleanRunArtifacts(head_node, workload)
    if use_cluster_checker:
      cmds = [
          'sudo rm -f {0}'.format(CC_NODE_FILE),
          'sudo rm -rf  ~/pkb_cluster_checker'
      ]
      cmd = ' && '.join(cmds)
      head_node.RemoteCommand(cmd)
    if fss_type == 'NFS':
      cmds = [
          'cat /etc/security/limits_backup.conf | sudo tee /etc/security/limits.conf',
          'sudo rm -f /etc/security/limits_backup.conf'
      ]
      cmd = ' && '.join(cmds)
      vm_util.RunThreaded(lambda compute_node: compute_node.RemoteCommand(cmd), vms)
      cmds = [
          'sudo rm -f /etc/exports',
          'sudo mv /etc/exports_backup /etc/exports',
          'sudo rm -f {0}/hosts'.format(head_node.GetScratchDir())
      ]
      cmd = ' && '.join(cmds)
      head_node.RemoteCommand(cmd)
    cmds = [
        'sudo rm -f /etc/hosts',
        '[ -f /etc/hosts_backup ] && sudo mv /etc/hosts_backup /etc/hosts'
    ]
    cmd = ' && '.join(cmds)
    vm_util.RunThreaded(lambda compute_node: compute_node.RemoteCommand(cmd), vms)
    if cloud == 'AWS' and fss_type == 'FSX':
      aws_fsx.Uninstall(head_node)
  else:
    vm = benchmark_spec.vms[0]
    _CleanRunArtifacts(vm, workload)


def IsClusterMode(intel_hpc_nodes):
  if intel_hpc_nodes == 1:
    return False
  return True


def GetHpcBenchmarksConfig():
  hpc_benchmarks_config_file = 'intel_hpc/intel_hpc_config.yaml'
  with open(data.ResourcePath(hpc_benchmarks_config_file)) as f:
    config = yaml.safe_load(f)
  return config


def GetVmCpuinfo(vm):
  out, _ = vm.RemoteCommand("lscpu | sed -n 's/Socket(s):[ \t]*//p'")
  sockets = int(out.strip())

  out, _ = vm.RemoteCommand("lscpu | sed -n 's/Core(s) per socket:[ \t]*//p'")
  cores_per_socket = int(out.strip())

  out, _ = vm.RemoteCommand("lscpu | sed -n 's/Thread(s) per core:[ \t]*//p'")
  threads_per_core = int(out.strip())

  result = collections.namedtuple('result', [
      "sockets",
      "cores_per_socket",
      "threads_per_core",
      "num_cores",
      "omp_num_threads",
  ])

  result.sockets = sockets
  result.cores_per_socket = cores_per_socket
  result.threads_per_core = threads_per_core
  result.num_cores = sockets * cores_per_socket
  result.omp_num_threads = threads_per_core
  return result


def _InstallAWSEFA(vm):
  vm.RemoteCommand('sudo yum update -y')
  vm.RemoteCommand('cd ~/aws-efa-installer && sudo  ./efa_installer.sh -y --minimal')


def _PrepareHeadNode(benchmark_spec, nodes, workload, image_type, fss_type, use_cluster_checker,
                     cloud):
  vm = benchmark_spec.vms[0]

  # Mark the image as a template image
  MarkVmAsTemplate(vm)

  # Install requirements
  vm.Install('aws_credentials')
  vm.Install('awscli')
  vm.Install('intel_hpc_singularity')
  vm.RemoteCommand('sudo yum -y install yum-utils')
  vm.Install('intel_parallel_studio_runtime')
  vm.Install('intel_hpc_head_node_cluster_check')

  if cloud == 'AWS':
    if flags.FLAGS.aws_efa:
      _InstallAWSEFA(vm)
      vm.RemoteCommand("echo -e '\nFI_PROVIDER=efa' | tee -a ~/.bashrc")
    if fss_type == 'FSX':
      vm.InstallEpelRepo()
      vm.RemoteCommand(' && '.join(aws_fsx.FSX_INSTALL_CMDS))


def _PrepareSingleNode(vm, workload, image_type, image_version):
  if IsTemplateVm(vm):
    # Overwrite the credentials from the template image
    flags.FLAGS.aws_credentials_overwrite = True
    vm.Install('aws_credentials')
  else:
    # Install requirements
    vm.Install('intel_hpc_singularity')
    vm.InstallEpelRepo()

  imageName = '{0}.{1}.{2}.simg'.format(workload, image_type, image_version)

  # If user wants to push images from PKB host to SUT
  if "data_search_paths" in flag_util.GetProvidedCommandLineFlags():
    localImagePath = data.ResourcePath(imageName)
    destPath = INSTALL_DIR + '/{0}.simg'.format(workload)
    # Push image from local PKB host machine to VM
    vm.PushFile(localImagePath, destPath)
  else:
    # Run on Bare metal
    if vm.CLOUD == "Static":
      # Save the full image path
      container_image_uri = GetHpcBenchmarksConfig()["image-uri"]
      s3_image_path = '{0}/{1}'.format(container_image_uri, imageName)

      _, _, retcode = vm.RemoteCommandWithReturnCode('wget {0} -O {1}/{2}.simg'.format
                                                     (s3_image_path, INSTALL_DIR, workload),
                                                     ignore_failure=True)
    # Run on Clouds
    else:
      vm.Install('aws_credentials')
      vm.Install('awscli')

      # Save the full image path
      container_image_path = GetHpcBenchmarksConfig()["image-bucket"]
      s3_image_path = '{0}/{1}'.format(container_image_path, imageName)

      # Check if the image exists on the S3 bucket
      _, _, retcode = vm.RemoteCommandWithReturnCode('aws s3 ls {0}'.format(s3_image_path),
                                                     ignore_failure=True)

      # If it exists on S3 copy from S3 to VM
      if retcode == 0:
        vm.RemoteCommand('aws s3 cp {0} {1}/{2}.simg'.format(s3_image_path, INSTALL_DIR, workload))


def _PrepareMultiNode(head_node, compute_nodes, workload, image_type, image_version, fss_type,
                      use_cluster_checker, cloud):
  vms = [head_node] + compute_nodes

  if IsTemplateVm(head_node):
    # Overwrite the credentials from the template image
    flags.FLAGS.aws_credentials_overwrite = True
    vm_util.RunThreaded(lambda vm: vm.Install('aws_credentials'), vms)
  else:
    # Install requirements
    vm_util.RunThreaded(lambda vm: vm.RemoteCommand('sudo yum -y install yum-utils'), vms)
    vm_util.RunThreaded(lambda vm: vm.Install('intel_parallel_studio_runtime'), vms)
    vm_util.RunThreaded(lambda vm: vm.Install('intel_hpc_singularity'), vms)

    if use_cluster_checker:
      vm_util.RunThreaded(lambda vm: vm.Install('intel_hpc_head_node_cluster_check'), vms)

    if cloud == 'AWS':
      if flags.FLAGS.aws_efa:
        vm_util.RunThreaded(lambda vm: _InstallAWSEFA(vm), vms)
        vm_util.RunThreaded(lambda vm:
                            vm.RemoteCommand("echo -e '\nFI_PROVIDER=efa' | tee -a ~/.bashrc"), vms)
      vm_util.RunThreaded(lambda vm: vm.Reboot(), vms)

  # Enable passwordless SSH from the head_node to all compute_nodes
  _EnablePasswordlessSsh(head_node)

  # Enable the required networking backend
  if cloud == 'AWS' and fss_type == 'FSX':
    head_node.Install('aws_fsx')
  else:
    head_node.Install('intel_hpc_nfs')

  # Adding support for TCP on Azure
  if cloud == 'Azure':
    head_node.RemoteCommand("echo -e '\nFI_PROVIDER=tcp' | tee -a ~/.bashrc")
    head_node.RemoteCommand("echo -e '\nFI_TCP_IFACE=eth0' | tee -a ~/.bashrc")

  mnt_dir = head_node.GetScratchDir()

  # make a /scratch/hosts without head_node
  mnt_hosts_content = ''
  for index, compute_node in enumerate(compute_nodes):
    mnt_hosts_content += 'node{0}\n'.format(str(index + 2))
  head_node.RemoteCommand('echo -e "{0}" | sudo tee -a {1}/hosts'.format(mnt_hosts_content, mnt_dir))

  imageName = '{0}.{1}.{2}.simg'.format(workload, image_type, image_version)

  # Run on Bare Metal
  if head_node.CLOUD == 'Static':
    # Save the full image path
    container_image_uri = GetHpcBenchmarksConfig()["image-uri"]
    s3_image_path = '{0}/{1}'.format(container_image_uri, imageName)

    _, _, retcode = head_node.RemoteCommandWithReturnCode('wget {0} -O /{1}/{2}.simg'
                                                          .format(s3_image_path, mnt_dir, workload),
                                                          ignore_failure=True)
  # Run on Clouds
  else:
    vm_util.RunThreaded(lambda vm: vm.InstallEpelRepo(), vms)
    vm_util.RunThreaded(lambda vm: vm.Install('aws_credentials'), vms)
    vm_util.RunThreaded(lambda vm: vm.Install('awscli'), vms)
    # Save the full image path
    container_image_path = GetHpcBenchmarksConfig()["image-bucket"]
    s3_image_path = '{0}/{1}'.format(container_image_path, imageName)

    # Check if the image exists on the S3 bucket
    _, _, retcode = head_node.RemoteCommandWithReturnCode('aws s3 ls {0}'.format(s3_image_path),
                                                          ignore_failure=True)
    # If the image is present on S3, copy from S3 to head_node
    if retcode == 0:
      head_node.RemoteCommand('aws s3 cp {0} {1}/{2}.simg'.format(s3_image_path,
                                                                  INSTALL_DIR, workload))
      head_node.RemoteCommand('sudo mv {0}/{1}.simg {2}'.format(INSTALL_DIR, workload, mnt_dir))

  # For Baremetal / Cloud - If image doesn't exist on S3, copy it from HPC Image server
  if retcode != 0:
    localImagePath = data.ResourcePath(imageName)
    destPath = INSTALL_DIR + '/{0}.simg'.format(workload)
    # Push image from local PKB host machine to VM
    head_node.PushFile(localImagePath, destPath)
    head_node.RemoteCommand('sudo mv {0}/{1}.simg {2}'.format(INSTALL_DIR, workload, mnt_dir))

  # Configure Cluster Checker and check the cluster health
  if use_cluster_checker:
    pkb_clck_dir = 'pkb_cluster_checker'
    frameworks = ['intel_hpc_platform_compat-hpc-2018.0', 'health_base', 'health_extended_user']

    head_node.Install('intel_hpc_cluster_check')
    head_node.RemoteCommand('echo -e "\n export CLCK_SHARED_TEMP_DIR={0}" | tee -a ~/.bashrc'
                            .format(mnt_dir))
    head_node.RemoteCommand('sudo chown -R ${{USER:=$(/usr/bin/id -run)}}:$USER {0}'.format(mnt_dir))

    head_node.RemoteCommand('mkdir -p {0}'.format(pkb_clck_dir))
    output = "\n"
    for framework in frameworks:
      head_node.RemoteCommand('. /opt/intel/clck/2019.8/bin/clckvars.sh && '
                              'clck -f {0} -F {1}'.format(CC_NODE_FILE, framework))
      head_node.RemoteCommand('mv clck_results.log {0}_results.log'.format(framework))
      head_node.RemoteCommand('mv clck_execution_warnings.log {0}_warnings.log'.format(framework))
      head_node.RemoteCommand('mv *.log {0}/'.format(pkb_clck_dir))
      head_node.RemoteCommand('cp ~/.clck/2019.8/clck.db ~/{0}/'.format(pkb_clck_dir))

    for framework in frameworks:
      output = output + framework + " - "
      CC_PASS = "No issues found"
      CC_WARNINGS = "Could not run all tests."
      stdout, _ = head_node.RemoteCommand("cat ~/{0}/{1}_results.log | "
                                          " grep Result:".format(pkb_clck_dir, framework))
      for line in stdout.splitlines():
        found = re.search(r"Overall Result: (.*)", line)
        if found:
          if found.group(1) == CC_PASS:
            output = output + "Cluster Checker PASSED\n"
          elif found.group(1) == CC_WARNINGS:
            output = output + "Cluster Checker PASSED with warnings\n"
          else:
            output = (output + "Cluster Checker Validation FAILED\t" +
                      "Please check pkb.log for more details\n")
    logging.info("Cluster Checker Output")
    logging.info(output)


def _EnablePasswordlessSsh(head_node):
  vms = [head_node] + head_node.compute_nodes

  # Create the SSH keys
  vm_util.RunThreaded(lambda vm: vm.RemoteCommand('ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa'), vms)

  # Enable full-mesh SSH
  for vm in vms:
    ssh_key, _ = vm.RemoteCommand("cat ~/.ssh/id_rsa.pub")
    vm_util.RunThreaded(lambda wm: wm.RemoteCommand("echo '{0}' >> ~/.ssh/authorized_keys"
                                                    .format(ssh_key)), vms)
    vm_util.RunThreaded(lambda wm: wm.RemoteCommand('echo -e "\nStrictHostKeyChecking no \n" '
                                                    '| sudo tee -a /etc/ssh/ssh_config'), vms)

  # Add entries to /etc/hosts
  cmds = ['sudo cp /etc/hosts /etc/hosts_backup']
  for i, vm in enumerate(vms):
    cmds.append("echo '{0} node{1}' | sudo tee -a /etc/hosts".format(vm.internal_ip, str(i + 1)))
  cmd = " ; ".join(cmds)
  vm_util.RunThreaded(lambda vm: vm.RemoteCommand(cmd), vms)


def _CleanRunArtifacts(vm, workload):
  filename = '{intel_hpc_appnames}_results.tar.gz'.format(intel_hpc_appnames=workload)
  archive = '{0}/{filename}'.format(INSTALL_DIR, filename=filename)
  vm.RemoteCommand("rm -f %s" % archive)
  vm.RemoteCommand("rm -rf $HOME/%s*" % workload)


def RunSysinfo(vm, dir, workload):
  vm.RemoteCommand('for app in sysinfo appinfo ; do '
                   'singularity run --app $app {0}/{1}.simg ; '
                   'done'.format(dir, workload))
