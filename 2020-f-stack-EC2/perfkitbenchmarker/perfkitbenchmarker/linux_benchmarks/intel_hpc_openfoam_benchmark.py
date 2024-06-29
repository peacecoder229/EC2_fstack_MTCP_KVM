import logging
import re
from absl import flags
from perfkitbenchmarker import configs
from perfkitbenchmarker import sample
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import intel_hpc_utils

FLAGS = flags.FLAGS
flags.DEFINE_integer('intel_hpc_openfoam_nodes', '1', 'The number of nodes to use', lower_bound=1)
flags.DEFINE_string('intel_hpc_openfoam_image_type', 'avx512', 'Image type for openfoam')
flags.DEFINE_string('intel_hpc_openfoam_image_version', 'Feb2021', 'Image version for openfoam')
flags.DEFINE_string('intel_hpc_openfoam_fss_type', 'NFS', 'File Shared System type: FSX or NFS')
flags.DEFINE_boolean('intel_hpc_openfoam_CC', False, 'If benchmark runs or not with Cluster Checker')

BENCHMARK_NAME = 'intel_hpc_openfoam'
BENCHMARK_CONFIG = """
intel_hpc_openfoam:
  description: Runs HPC openfoam
  vm_groups:
    head_node:
      os_type: centos7
      vm_spec: *default_hpc_head_node_vm_spec
      disk_spec: *default_hpc_head_node_disk_spec
    compute_nodes:
      os_type: centos7
      vm_spec: *default_hpc_compute_nodes_vm_spec
      disk_spec: *default_hpc_compute_nodes_disk_spec
  flags:
    enable_transparent_hugepages: false
"""
workload = "openfoam"


###############################################################################
def CheckPrerequisites(config):
  intel_hpc_utils.CheckPrerequisites(workload)


def GetConfig(user_config):
  # Load the benchmark configuration
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
  config = intel_hpc_utils.GetConfig(config, FLAGS.intel_hpc_openfoam_nodes)
  return config


def _GetOpenfoamPkg(vm):
  hpc_benchmarks_config = intel_hpc_utils.GetHpcBenchmarksConfig()
  pkg_name = 'OpenFOAM-Intel.tar.gz'
  mnt_dir = vm.GetScratchDir()
  if vm.CLOUD == 'Static':
    pkg_path = hpc_benchmarks_config["image-uri"]
    _, _, retcode = vm.RemoteCommandWithReturnCode('cd {0} && wget {1}/{2} -O {2}'.format
                                                   (mnt_dir, pkg_path, pkg_name),
                                                   ignore_failure=True)
  else:
    pkg_path = hpc_benchmarks_config["image-bucket"]
    vm.RemoteCommand('aws s3 cp {0}/{1} {2}'.format(pkg_path, pkg_name, mnt_dir))

  vm.RemoteCommand('tar -xzf {0}/{1} -C {0}'.format(mnt_dir, pkg_name))


def Prepare(benchmark_spec):
  logging.info("Intel HPC Prepare")
  benchmark_spec.workload_name = "HPC Openfoam"
  benchmark_spec.sut_vm_group = "compute_nodes"
  intel_hpc_utils.Prepare(benchmark_spec, FLAGS.intel_hpc_openfoam_nodes, workload,
                          FLAGS.intel_hpc_openfoam_image_type,
                          FLAGS.intel_hpc_openfoam_image_version,
                          FLAGS.intel_hpc_openfoam_fss_type,
                          FLAGS.intel_hpc_openfoam_CC, FLAGS.cloud)
  if intel_hpc_utils.IsClusterMode(FLAGS.intel_hpc_openfoam_nodes):
    head_node = benchmark_spec.vm_groups['head_node'][0]
    _GetOpenfoamPkg(head_node)
  else:
    vm = benchmark_spec.vm_groups['compute_nodes'][0]
    _GetOpenfoamPkg(vm)


def Run(benchmark_spec):
  logging.info("Intel HPC Run")
  # PKB bug: If the results array contains no Sample, PKB will execute
  # the Run() method again after the Teardown
  results = []

  hpc_benchmarks_config = intel_hpc_utils.GetHpcBenchmarksConfig()

  if intel_hpc_utils.IsClusterMode(FLAGS.intel_hpc_openfoam_nodes):
    head_node = benchmark_spec.vm_groups['head_node'][0]
    compute_nodes = benchmark_spec.vm_groups['compute_nodes']
    cpuinfo = intel_hpc_utils.GetVmCpuinfo(compute_nodes[0])

    physical_cores_per_node = cpuinfo.sockets * cpuinfo.cores_per_socket
    total_physical_cores = physical_cores_per_node * FLAGS.intel_hpc_openfoam_nodes
    workloads = hpc_benchmarks_config[workload]["workloads"]
    mnt_dir = head_node.GetScratchDir()

    rdma_cmd = ''
    if FLAGS.aws_efa:
      rdma_cmd = '-B /home/centos/rdma-core:/rdma-core'
    singularity_cmd = ('singularity run -B {0}/OpenFOAM-Intel:/WORKSPACE/OpenFOAM-Intel'.format(mnt_dir)
                       + rdma_cmd +
                       ' --writable-tmpfs --app ')

    head_node.RemoteCommand(singularity_cmd + 'setup {0}/{1}.simg {2}'.format(mnt_dir, workload,
                                                                              total_physical_cores))

    mpi_cmd = ('source ~/.bashrc;'
               'source /opt/intel/psxe_runtime/linux/mpi/intel64/bin/mpivars.sh;'
               '/opt/intel/psxe_runtime/linux/mpi/intel64/bin/mpiexec.hydra -hostfile {0}/hosts -n'
               ' {1} -genv I_MPI_DEBUG=5 '.format(mnt_dir, total_physical_cores))

    head_node.RemoteCommand(mpi_cmd + singularity_cmd + 'potentialfoam {0}/{1}.simg'
                            .format(mnt_dir, workload))

    for sub_wkld in workloads:
      head_node.RemoteCommand(mpi_cmd + singularity_cmd + 'solve'
                              ' {0}/{1}.simg {2}'.format(mnt_dir, workload, sub_wkld))

    intel_hpc_utils.RunSysinfo(compute_nodes[0], mnt_dir, workload)

    # To collect the results
    compute_nodes[0].RemoteCommand('singularity run --writable-tmpfs --app multinodeResults {0}/{1}.simg '
                                   .format(mnt_dir, workload))

    for wkld in workloads:
      stdout, _ = compute_nodes[0].RemoteCommand("cat {0}*/{1}*.results".format(workload, wkld))
      match = re.search(r'(ClockTime)\s+=\s+([0-9]*)\s+(\w)', stdout)
      if match:
        if wkld == 'simpleFoam':
          metadata = {'primary_sample': True}
          results.append(sample.Sample('SimpleFoam', match.group(2),
                                       match.group(1) + '(' + match.group(3) + ')', metadata))
        else:
          results.append(sample.Sample(wkld, match.group(2),
                                       match.group(1) + '(' + match.group(3) + ')', {}))

    intel_hpc_utils.GetNodeArchives(head_node, compute_nodes[0], workload, FLAGS.intel_hpc_openfoam_CC)
  else:
    vm = benchmark_spec.vms[0]
    cpuinfo = intel_hpc_utils.GetVmCpuinfo(vm)
    mnt_dir = vm.GetScratchDir()

    vm.RemoteCommand('singularity run -B {0}/OpenFOAM-Intel:/WORKSPACE/OpenFOAM-Intel --writable-tmpfs'
                     ' --app openfoam {1}/{2}.simg '.format(mnt_dir, INSTALL_DIR, workload))

    intel_hpc_utils.RunSysinfo(vm, INSTALL_DIR, workload)

    stdout, _ = vm.RemoteCommand("cat {0}*/*.results | grep SimpleFoam".format(workload))

    match = re.search(r'(ClockTime)\s+= ([0-9]*)\s+(\w)', stdout)

    if match:
      results.append(sample.Sample("SimpleFoam", match.group(2),
                                   match.group(1) + '(' + match.group(3) + ')', {'primary_sample': True}))

    intel_hpc_utils.GetNodeArchives(vm, vm, workload, FLAGS.intel_hpc_openfoam_CC)

  if len(results) == 0:
    raise Exception("No results were collected. Please check the log files for possible errors.")
  return results


def Cleanup(benchmark_spec):
  logging.info("Intel HPC Clean")
  intel_hpc_utils.Cleanup(benchmark_spec, FLAGS.intel_hpc_openfoam_nodes,
                          workload, FLAGS.intel_hpc_openfoam_fss_type, FLAGS.cloud,
                          FLAGS.intel_hpc_openfoam_CC)
