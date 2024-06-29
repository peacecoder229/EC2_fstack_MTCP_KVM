import logging
import re
from absl import flags
from perfkitbenchmarker import configs
from perfkitbenchmarker import sample
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import intel_hpc_utils

FLAGS = flags.FLAGS
flags.DEFINE_integer('intel_hpc_namd_nodes', '1', 'The number of nodes to use', lower_bound=1)
flags.DEFINE_string('intel_hpc_namd_image_type', 'avx512', 'Image type for namd')
flags.DEFINE_string('intel_hpc_namd_image_version', 'Feb2021', 'Image version for namd')
flags.DEFINE_string('intel_hpc_namd_fss_type', 'NFS', 'File Shared System type: FSX or NFS')
flags.DEFINE_boolean('intel_hpc_namd_CC', False, 'If benchmark runs or not with Cluster Checker')

BENCHMARK_NAME = 'intel_hpc_namd'
BENCHMARK_CONFIG = """
intel_hpc_namd:
  description: Runs HPC namd
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
workload = "namd"


###############################################################################
def CheckPrerequisites(config):
  intel_hpc_utils.CheckPrerequisites(workload)


def GetConfig(user_config):
  # Load the benchmark configuration
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
  config = intel_hpc_utils.GetConfig(config, FLAGS.intel_hpc_namd_nodes)
  return config


def Prepare(benchmark_spec):
  logging.info("Intel HPC Prepare")
  benchmark_spec.workload_name = "HPC NAMD"
  benchmark_spec.sut_vm_group = "compute_nodes"
  intel_hpc_utils.Prepare(benchmark_spec, FLAGS.intel_hpc_namd_nodes, workload,
                          FLAGS.intel_hpc_namd_image_type, FLAGS.intel_hpc_namd_image_version,
                          FLAGS.intel_hpc_namd_fss_type, FLAGS.intel_hpc_namd_CC, FLAGS.cloud)


def _GetResultsMNOrAMD(vm, workloads):
  results = []
  output = '\n'
  for sub_wkld in workloads:
    results_list = []
    results_name = []
    stdout, _ = vm.RemoteCommand("cat {0}*/{0}*.results | grep -w {1}"
                                 .format(workload, sub_wkld))
    metadata = {}
    for line in stdout.splitlines():
      found = re.search(r'^' + sub_wkld + r'(.*)\s+([0-9]*\.[0-9]*)'.format(workload), line)
      if found:
        if sub_wkld == 'apoa1':
          metadata = {'primary_sample': True}
        results_list.append(float(found.group(2)))
        results_name.append(sub_wkld + found.group(1))
        output += sub_wkld + found.group(1) + '\t' + found.group(2) + '\n'
    maxValue = max(results_list)
    results.append(sample.Sample('FOM for ' + sub_wkld.upper(), maxValue, 'ns/days', metadata))
  logging.info(output)
  return results


def Run(benchmark_spec):
  logging.info("Intel HPC Run")
  # PKB bug: If the results array contains no Sample, PKB will execute the Run() method
  # again after the Teardown
  results = []

  hpc_benchmarks_config = intel_hpc_utils.GetHpcBenchmarksConfig()
  workloads = hpc_benchmarks_config[workload]["workloads"]

  if intel_hpc_utils.IsClusterMode(FLAGS.intel_hpc_namd_nodes):
    head_node = benchmark_spec.vm_groups['head_node'][0]
    compute_nodes = benchmark_spec.vm_groups['compute_nodes']
    cpuinfo = intel_hpc_utils.GetVmCpuinfo(compute_nodes[0])

    num_mpi_processes = [2, 4, 8]
    physical_cores = cpuinfo.num_cores
    vcpus = physical_cores * cpuinfo.threads_per_core

    mnt_dir = head_node.GetScratchDir()
    hostfile = "{0}/hosts".format(mnt_dir)

    rdma_cmd = ''
    if FLAGS.aws_efa:
      rdma_cmd = ' -B /home/centos/rdma-core:/rdma-core'
    run_cmd = ('source ~/.bashrc;'
               'source /opt/intel/psxe_runtime/linux/mpi/intel64/bin/mpivars.sh;'
               '/opt/intel/psxe_runtime/linux/mpi/intel64/bin/mpiexec.hydra'
               ' -perhost {0} -genv I_MPI_DEBUG=5 -f {1} -n {2} singularity run'
               ' --writable-tmpfs ')

    for wkld in workloads:
      for ppn in num_mpi_processes:
        total_ppn = ppn * FLAGS.intel_hpc_namd_nodes
        head_node.RemoteCommand(run_cmd.format(ppn, hostfile, total_ppn) + rdma_cmd +
                                ' --app multinode {0}/{1}.simg {2} {3} {4} {5}'
                                .format(mnt_dir, workload, wkld, FLAGS.intel_hpc_namd_nodes, ppn,
                                        vcpus), ignore_failure=True)

        head_node.RemoteCommand(run_cmd.format(ppn, hostfile, total_ppn) + rdma_cmd +
                                ' --app multinode {0}/{1}.simg {2} {3} {4} {5}'
                                .format(mnt_dir, workload, wkld, FLAGS.intel_hpc_namd_nodes, ppn,
                                        physical_cores), ignore_failure=True)

        if cpuinfo.threads_per_core > 1:
          head_node.RemoteCommand(run_cmd.format(ppn, hostfile, total_ppn) + rdma_cmd +
                                  ' --app multinode {0}/{1}.simg {2} {3} {4} {5} '
                                  .format(mnt_dir, workload, wkld, FLAGS.intel_hpc_namd_nodes, ppn,
                                          physical_cores) + 'ht', ignore_failure=True)

    compute_nodes[0].RemoteCommand('singularity run --writable-tmpfs --app  multinodeResults {0}/{1}.simg'
                                   .format(mnt_dir, workload))
    results = _GetResultsMNOrAMD(compute_nodes[0], workloads)
    intel_hpc_utils.GetNodeArchives(head_node, compute_nodes[0], workload, FLAGS.intel_hpc_namd_CC)
  else:
    vm = benchmark_spec.vms[0]
    cpuinfo = intel_hpc_utils.GetVmCpuinfo(vm)

    physical_cores = cpuinfo.num_cores
    vcpus = physical_cores * cpuinfo.threads_per_core

    if FLAGS.intel_hpc_namd_image_type == 'amd':
      num_mpi_processes = [1, 2, 4, 8]
      run_cmd = 'singularity run --writable-tmpfs --app namd {0}/{1}.simg {2} {3} {4} {5}'
      for wkld in workloads:
        for ppn in num_mpi_processes:
          vm.RemoteCommand(run_cmd.format(INSTALL_DIR, workload, wkld, FLAGS.intel_hpc_namd_nodes,
                                          ppn, vcpus), ignore_failure=True)

          vm.RemoteCommand(run_cmd.format(INSTALL_DIR, workload, wkld, FLAGS.intel_hpc_namd_nodes,
                                          ppn, physical_cores), ignore_failure=True)

          if cpuinfo.threads_per_core > 1:
            vm.RemoteCommand((run_cmd + ' ht').format(INSTALL_DIR, workload, wkld,
                                                      FLAGS.intel_hpc_namd_nodes,
                                                      ppn, physical_cores), ignore_failure=True)

      vm.RemoteCommand('singularity run --app  multinodeResults {0}/{1}.simg'
                       .format(INSTALL_DIR, workload))
      results = _GetResultsMNOrAMD(vm, workloads)
    else:
      vm.RemoteCommand('singularity run --writable-tmpfs --app namd {0}/{1}.simg'
                       .format(INSTALL_DIR, workload))

      stdout, _ = vm.RemoteCommand("cat {0}*/{0}*.results | grep -A 1 APOA1".format(
                                   workload))
      found_apoa = re.search(r'(FOM for APOA1)\s\w+\s(\w+\/\w+):\n([0-9]*\.[0-9]*)', stdout)
      if found_apoa:
        results.append(sample.Sample(found_apoa.group(1), found_apoa.group(3), found_apoa.group(2),
                                     {'primary_sample': True}))

      stdout, _ = vm.RemoteCommand("cat {0}*/{0}*.results | grep -A 1 STMV".format(
                                   workload))
      found_stmv = re.search(r'(FOM for STMV)\s\w+\s(\w+\/\w+):\n([0-9]*\.[0-9]*)', stdout)
      if found_stmv:
        results.append(sample.Sample(found_stmv.group(1), found_stmv.group(3), found_stmv.group(2),
                                     {}))

      stdout, _ = vm.RemoteCommand("cat {0}*/{0}*.results | grep -A 1 APOA1_2fs".format(
                                   workload))
      found_apoa1_2fs = re.search(r'(FOM for APOA1_2fs)\s\w+\s(\w+\/\w+):\n([0-9]*\.[0-9]*)', stdout)
      if found_apoa1_2fs:
        results.append(sample.Sample(found_apoa1_2fs.group(1), found_apoa1_2fs.group(3), found_apoa1_2fs.group(2),
                                     {}))

      stdout, _ = vm.RemoteCommand("cat {0}*/{0}*.results | grep -A 1 STMV_2fs".format(
                                   workload))
      found_stmv_2fs = re.search(r'(FOM for STMV_2fs)\s\w+\s(\w+\/\w+):\n([0-9]*\.[0-9]*)', stdout)
      if found_stmv_2fs:
        results.append(sample.Sample(found_stmv_2fs.group(1), found_stmv_2fs.group(3), found_stmv_2fs.group(2),
                                     {}))

    intel_hpc_utils.GetNodeArchives(vm, vm, workload, FLAGS.intel_hpc_namd_CC)

  if len(results) == 0:
    raise Exception("No results were collected. Please check the log files for possible errors.")
  return results


def Cleanup(benchmark_spec):
  logging.info("Intel HPC Clean")
  intel_hpc_utils.Cleanup(benchmark_spec, FLAGS.intel_hpc_namd_nodes, workload,
                          FLAGS.intel_hpc_namd_fss_type, FLAGS.cloud, FLAGS.intel_hpc_namd_CC)
