import logging
import re
from absl import flags
from perfkitbenchmarker import configs
from perfkitbenchmarker import sample
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import intel_hpc_utils

FLAGS = flags.FLAGS
flags.DEFINE_integer('intel_hpc_lammps_nodes', '1', 'The number of nodes to use', lower_bound=1)
flags.DEFINE_string('intel_hpc_lammps_image_type', 'avx512', 'Image type for lammps')
flags.DEFINE_string('intel_hpc_lammps_image_version', 'Feb2021', 'Image version for lammps')
flags.DEFINE_string('intel_hpc_lammps_fss_type', 'NFS', 'File Shared System type: FSX or NFS')
flags.DEFINE_boolean('intel_hpc_lammps_CC', False, 'If benchmark runs or not with Cluster Checker')

BENCHMARK_NAME = 'intel_hpc_lammps'
BENCHMARK_CONFIG = """
intel_hpc_lammps:
  description: Runs HPC lammps
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
workload = "lammps"


###############################################################################
def CheckPrerequisites(config):
  intel_hpc_utils.CheckPrerequisites(workload)


def GetConfig(user_config):
  # Load the benchmark configuration
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
  config = intel_hpc_utils.GetConfig(config, FLAGS.intel_hpc_lammps_nodes)
  return config


def Prepare(benchmark_spec):
  logging.info("Intel HPC Prepare")
  benchmark_spec.workload_name = "HPC Lammps"
  benchmark_spec.sut_vm_group = "compute_nodes"
  intel_hpc_utils.Prepare(benchmark_spec, FLAGS.intel_hpc_lammps_nodes, workload,
                          FLAGS.intel_hpc_lammps_image_type, FLAGS.intel_hpc_lammps_image_version,
                          FLAGS.intel_hpc_lammps_fss_type,
                          FLAGS.intel_hpc_lammps_CC, FLAGS.cloud)


def Run(benchmark_spec):
  logging.info("Intel HPC Run")
  # PKB bug: If the results array contains no Sample, PKB will execute the Run()
  # method again after the Teardown
  results = []
  metadata = {}

  hpc_benchmarks_config = intel_hpc_utils.GetHpcBenchmarksConfig()
  workloads = hpc_benchmarks_config[workload]["sub_workloads"]
  sub_workload_names = hpc_benchmarks_config[workload]["sub_workload_names"]

  if intel_hpc_utils.IsClusterMode(FLAGS.intel_hpc_lammps_nodes):
    head_node = benchmark_spec.vm_groups['head_node'][0]
    compute_nodes = benchmark_spec.vm_groups['compute_nodes']
    cpuinfo = intel_hpc_utils.GetVmCpuinfo(compute_nodes[0])

    num_cores = cpuinfo.num_cores
    omp_num_threads = cpuinfo.omp_num_threads
    np = num_cores * FLAGS.intel_hpc_lammps_nodes

    mnt_dir = head_node.GetScratchDir()
    rdma_cmd = ''
    if FLAGS.aws_efa:
      rdma_cmd = '-B /home/centos/rdma-core:/rdma-core'

    for wkld in workloads:
      head_node.RemoteCommand('source ~/.bashrc && '
                              'source /opt/intel/psxe_runtime/linux/mpi/intel64/bin/mpivars.sh && '
                              'mpiexec.hydra '
                              '-genv I_MPI_DEBUG 2 '
                              '-hostfile {0}/hosts '
                              '-ppn {1} '
                              '-np {2} '
                              'singularity run --writable-tmpfs '.format(mnt_dir, num_cores, np) +
                              rdma_cmd +
                              ' --app multinode {0}/{1}.simg {2} {3}'
                              .format(mnt_dir, workload, wkld, omp_num_threads))

    intel_hpc_utils.RunSysinfo(compute_nodes[0], mnt_dir, workload)

    compute_nodes[0].RemoteCommand('singularity run --writable-tmpfs --app'
                                   ' multinodeResults {0}/{1}.simg {2}'
                                   .format(mnt_dir, workload, FLAGS.intel_hpc_lammps_image_type))

    for sub_wkld in sub_workload_names:
      stdout, _ = compute_nodes[0].RemoteCommand("cat {0}*/*.results | grep '{1}'"
                                                 .format(workload, sub_wkld))
      found = re.search(r"([0-9]*\.?[0-9]+) * (.*)", stdout)
      if found:
        metadata = {}
        if sub_wkld == 'Polyethelene (airebo)':
          metadata = {'primary_sample': True}
        results.append(sample.Sample(sub_wkld, float(found.group(1)), found.group(2), metadata))

    intel_hpc_utils.GetNodeArchives(head_node, compute_nodes[0], workload,
                                    FLAGS.intel_hpc_lammps_CC)
  else:
    vm = benchmark_spec.vms[0]
    cpuinfo = intel_hpc_utils.GetVmCpuinfo(vm)

    num_cores = cpuinfo.num_cores
    omp_num_threads = cpuinfo.threads_per_core

    vm.RemoteCommand('echo "\nI_MPI_HYDRA_TOPOLIB=ipl" | tee -a ~/.bashrc')
    vm.RemoteCommand('echo "\nI_MPI_FABRIC=shm" | tee -a ~/.bashrc')
    vm.RemoteCommand('singularity run --writable-tmpfs --app lammps {0}/{1}.simg {2} {3}'.format(
                     INSTALL_DIR, workload, num_cores, omp_num_threads))

    intel_hpc_utils.RunSysinfo(vm, INSTALL_DIR, workload)

    for sub_wkld in sub_workload_names:
      stdout, _ = vm.RemoteCommand("cat {0}*/*.results | grep '{1}'".format(workload, sub_wkld))
      found = re.search(r"([0-9]*\.?[0-9]+) * (.*)", stdout)
      if found:
        metadata = {}
        if sub_wkld == 'Polyethelene (airebo)':
          metadata = {'primary_sample': True}
        results.append(sample.Sample(sub_wkld, float(found.group(1)), found.group(2), metadata))

    intel_hpc_utils.GetNodeArchives(vm, vm, workload, FLAGS.intel_hpc_lammps_CC)

  if len(results) == 0:
    raise Exception("No results were collected. Please check the log files for possible errors.")
  return results


def Cleanup(benchmark_spec):
  logging.info("Intel HPC Clean")
  intel_hpc_utils.Cleanup(benchmark_spec, FLAGS.intel_hpc_lammps_nodes, workload,
                          FLAGS.intel_hpc_lammps_fss_type, FLAGS.cloud, FLAGS.intel_hpc_lammps_CC)
