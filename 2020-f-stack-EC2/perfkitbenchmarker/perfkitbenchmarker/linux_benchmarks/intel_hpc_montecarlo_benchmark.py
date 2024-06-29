import logging
import re
from absl import flags
from perfkitbenchmarker import configs
from perfkitbenchmarker import sample
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import intel_hpc_utils

FLAGS = flags.FLAGS
flags.DEFINE_integer('intel_hpc_montecarlo_nodes', 1, 'The number of nodes to use', lower_bound=1)
flags.DEFINE_string('intel_hpc_montecarlo_image_type', 'avx512', 'Image type for montecarlo')
flags.DEFINE_string('intel_hpc_montecarlo_image_version', 'Feb2021', 'Image version for montecarlo')
flags.DEFINE_string('intel_hpc_montecarlo_fss_type', 'NFS', 'File Shared System type: FSX or NFS')
flags.DEFINE_boolean('intel_hpc_montecarlo_CC', False, 'If benchmark runs or not with Cluster Checker')

BENCHMARK_NAME = 'intel_hpc_montecarlo'
BENCHMARK_CONFIG = """
intel_hpc_montecarlo:
  description: Runs HPC montecarlo
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
workload = "montecarlo"


###############################################################################
def CheckPrerequisites(config):
  intel_hpc_utils.CheckPrerequisites(workload)


def GetConfig(user_config):
  # Load the benchmark configuration
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
  if intel_hpc_utils.IsClusterMode(FLAGS.intel_hpc_montecarlo_nodes):
    raise Exception('MulitNode is currently not supported for this workload')
  else:
    config = intel_hpc_utils.GetConfig(config, FLAGS.intel_hpc_montecarlo_nodes)
  return config


def Prepare(benchmark_spec):
  logging.info("Intel HPC Prepare")
  benchmark_spec.workload_name = "HPC Montecarlo"
  benchmark_spec.sut_vm_group = "compute_nodes"
  intel_hpc_utils.Prepare(benchmark_spec, FLAGS.intel_hpc_montecarlo_nodes, workload,
                          FLAGS.intel_hpc_montecarlo_image_type, FLAGS.intel_hpc_montecarlo_image_version,
                          FLAGS.intel_hpc_montecarlo_fss_type,
                          FLAGS.intel_hpc_montecarlo_CC, FLAGS.cloud)


def Run(benchmark_spec):
  logging.info("Intel HPC Run")
  # PKB bug: If the results array contains no Sample, PKB will execute the Run()
  # method again after the Teardown
  results = []
  vm = benchmark_spec.vms[0]

  vm.RemoteCommand('singularity run --writable-tmpfs {0}/{1}.simg'.format(
                   INSTALL_DIR, workload))

  intel_hpc_utils.RunSysinfo(vm, INSTALL_DIR, workload)

  stdout, _ = vm.RemoteCommand("cat {0}*/*.results".format(workload))
  found = re.search(r'(\w+) in (\w+) : ([0-9]*\.[0-9]*)', stdout)
  if found:
    results.append(sample.Sample(found.group(1), float(found.group(3)), found.group(2),
                                 {'primary_sample': True}))
  intel_hpc_utils.GetNodeArchives(vm, vm, workload, FLAGS.intel_hpc_montecarlo_CC)

  if len(results) == 0:
    raise Exception("No results were collected. Please check the log files for possible errors.")
  return results


def Cleanup(benchmark_spec):
  logging.info("Intel HPC Clean")
  intel_hpc_utils.Cleanup(benchmark_spec, FLAGS.intel_hpc_montecarlo_nodes, workload,
                          FLAGS.intel_hpc_montecarlo_fss_type, FLAGS.cloud, FLAGS.intel_hpc_montecarlo_CC)
