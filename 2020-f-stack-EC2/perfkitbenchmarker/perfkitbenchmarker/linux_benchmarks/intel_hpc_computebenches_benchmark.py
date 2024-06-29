import logging
import re
from absl import flags
from perfkitbenchmarker import configs
from perfkitbenchmarker import sample
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import intel_hpc_utils

SUB_WORKLOADS = ['hpl', 'hpcg', 'gemms', 'all']

FLAGS = flags.FLAGS
flags.DEFINE_integer('intel_hpc_computebenches_nodes', '1',
                     'The number of nodes to use', lower_bound=1)
flags.DEFINE_string('intel_hpc_computebenches_image_type', 'avx512',
                    'Image type for computeBenches')
flags.DEFINE_string('intel_hpc_computebenches_image_version', 'Feb2021',
                    'Image version for computeBenches')
flags.DEFINE_string('intel_hpc_computebenches_fss_type', 'NFS',
                    'File Shared System type: FSX or NFS')
flags.DEFINE_boolean('intel_hpc_computebenches_CC', False,
                     'If benchmark runs or not with Cluster Checker')
flags.DEFINE_enum('intel_hpc_computebenches_sub_workload', 'all',
                  SUB_WORKLOADS,
                  'Choose the workload type')

BENCHMARK_NAME = 'intel_hpc_computebenches'
BENCHMARK_CONFIG = """
intel_hpc_computebenches:
  description: Runs HPC Micro benchmarks - SGEMM, DGEMM, HPL and HPCG
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
workload = "computeBenches"


###############################################################################
def CheckPrerequisites(config):
  intel_hpc_utils.CheckPrerequisites(workload)


def GetConfig(user_config):
  # Load the benchmark configuration
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
  if intel_hpc_utils.IsClusterMode(FLAGS.intel_hpc_computebenches_nodes):
    raise Exception("MultiNode run is not supported for ComputeBenches.")
  else:
    config = intel_hpc_utils.GetConfig(config, FLAGS.intel_hpc_computebenches_nodes)
  return config


def Prepare(benchmark_spec):
  logging.info("Intel HPC Prepare")
  benchmark_spec.workload_name = "HPC Computebenches"
  benchmark_spec.sut_vm_group = "compute_nodes"
  intel_hpc_utils.Prepare(benchmark_spec, FLAGS.intel_hpc_computebenches_nodes, workload,
                          FLAGS.intel_hpc_computebenches_image_type,
                          FLAGS.intel_hpc_computebenches_image_version,
                          FLAGS.intel_hpc_computebenches_fss_type,
                          FLAGS.intel_hpc_computebenches_CC, FLAGS.cloud)


def _RunHPL(vm, workload, sub_workload, results):
  vm.RemoteCommand('singularity run --writable-tmpfs --app hpl {0}/{1}.simg'
                   .format(INSTALL_DIR, workload))
  stdout, _ = vm.RemoteCommand("cat {0}/{1}*.results".format(workload, sub_workload))
  found_hpl = re.search(r'(HPL): ([0-9]*\.[0-9]*\w\W\d+) (\w+\/\w)', stdout)
  if found_hpl:
    results.append(sample.Sample(found_hpl.group(1), found_hpl.group(2),
                                 'GF/s', {'primary_sample': True}))


def _RunGemms(vm, workload, sub_workload, results):
  vm.RemoteCommand('singularity run --writable-tmpfs --app gemms {0}/{1}.simg'
                   .format(INSTALL_DIR, workload))
  stdout, _ = vm.RemoteCommand("cat {0}/{1}*.results | grep Performance "
                               .format(workload, sub_workload))
  found_sgemm = re.search(r'(SGEMM) Performance N =\s+[0-9]* :\s+([0-9]*\.[0-9]*) (\w+)',
                          stdout)
  if found_sgemm:
    results.append(sample.Sample(found_sgemm.group(1), found_sgemm.group(2),
                                 found_sgemm.group(3), {}))
  found_dgemm = re.search(r'(DGEMM) Performance N =\s+[0-9]* :\s+([0-9]*\.[0-9]*) (\w+)',
                          stdout)
  if found_dgemm:
    results.append(sample.Sample(found_dgemm.group(1), found_dgemm.group(2),
                                 found_dgemm.group(3), {}))


def _RunHPCG(vm, workload, sub_workload, results):
  vm.RemoteCommand('singularity run --writable-tmpfs --app hpcg {0}/{1}.simg'
                   .format(INSTALL_DIR, workload))
  stdout, _ = vm.RemoteCommand("cat {0}/{1}*.results ".format(workload, sub_workload))
  found_hpcg = re.search(r'(HPCG): ([0-9]*\.[0-9]*) (\w+\/\w)', stdout)
  if found_hpcg:
    results.append(sample.Sample(found_hpcg.group(1), found_hpcg.group(2),
                                 found_hpcg.group(3), {}))


def Run(benchmark_spec):
  logging.info("Intel HPC Run")
  # PKB bug: If the results array contains no Sample, PKB will execute
  # the Run() method again after the Teardown
  results = []
  benchmark_spec.software_config_metadata = {
      'sub_workload': FLAGS.intel_hpc_computebenches_sub_workload}

  vm = benchmark_spec.vms[0]

  if (FLAGS.intel_hpc_computebenches_sub_workload == "hpl" or
      FLAGS.intel_hpc_computebenches_sub_workload == "all"):
    _RunHPL(vm, workload, 'hpl', results)
  if (FLAGS.intel_hpc_computebenches_sub_workload == "hpcg" or
      FLAGS.intel_hpc_computebenches_sub_workload == "all"):
    _RunHPCG(vm, workload, 'hpcg', results)
  if (FLAGS.intel_hpc_computebenches_sub_workload == "gemms" or
      FLAGS.intel_hpc_computebenches_sub_workload == "all"):
    _RunGemms(vm, workload, 'gemms', results)

  vm.RemoteCommand('singularity run --writable-tmpfs --app sysinfo {0}/{1}.simg'
                   .format(INSTALL_DIR, workload))
  intel_hpc_utils.GetNodeArchives(vm, vm, workload, FLAGS.intel_hpc_computebenches_CC)

  if len(results) == 0:
    raise Exception("No results were collected. Please check the log files for possible errors.")
  return results


def Cleanup(benchmark_spec):
  logging.info("Intel HPC Clean")
  intel_hpc_utils.Cleanup(benchmark_spec, FLAGS.intel_hpc_computebenches_nodes, workload,
                          FLAGS.intel_hpc_computebenches_fss_type, FLAGS.cloud,
                          FLAGS.intel_hpc_computebenches_CC)
