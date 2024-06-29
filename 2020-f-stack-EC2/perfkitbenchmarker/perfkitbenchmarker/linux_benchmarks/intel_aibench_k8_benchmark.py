# See the License for the specific language governing permissions and
# limitations under the License.


"""AIBench benchmark
Code: https://github.intel.com/Data-Center-E2E-Benchmarks/AIBench
This benchmark supports the running of Artificial Intelligence/Deep Learning inference workloads
"""

import logging
import os
import uuid
import posixpath
import yaml
import sys
import json
import time
import datetime

from subprocess import call
from absl import flags
from perfkitbenchmarker import configs
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import sample
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import data
from perfkitbenchmarker import errors
from perfkitbenchmarker import intel_aibench_utils

FLAGS = flags.FLAGS

BENCHMARK_NAME = 'intel_aibench_k8'
BENCHMARK_CONFIG = """
intel_aibench_k8:
  description: Runs AIBench.
  vm_groups:
    target:
      vm_spec: *default_single_core
      disk_spec: *default_500_gb
      #vm_count: null
      disk_count: 0
"""
AIBENCH_HARNESS_SETTINGS = {}
AIBENCH_DIR = '/'
LOG_DIR = '/tmp/aibench/runs'
SETUP_COMMANDS = []
NUMA_RUN_COMMANDS = []


def GetConfig(user_config):
  """ Reads the AIBench run time configration file - harness_settings """
  logging.info('AIBench GetConfig')
  intel_aibench_utils.CheckConfigFile(FLAGS.aibench_harness_yaml)

  harness_settings_file_path = FLAGS.aibench_harness_yaml
  with open(harness_settings_file_path) as f:
    global AIBENCH_HARNESS_SETTINGS
    AIBENCH_HARNESS_SETTINGS = yaml.safe_load(f)

  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
  return config


def Prepare(benchmark_spec):
  """Prepare k8-pods to run AIBench

  Args:
      benchmark_spec: The benchmark specification.
  """
  logging.info('AIBench Prepare')
  vms = benchmark_spec.vms

  namespace = FLAGS.run_uri
  scenario = FLAGS.aibench_scenario
  virtual_instances = (AIBENCH_HARNESS_SETTINGS['scenarios'][scenario]
                                               ['virtual-instances']).split(',')
  multi_node = intel_aibench_utils.IsMultiNode(len(virtual_instances))
  logging.info('Scenario: {s}'.format(s=scenario))
  logging.info('Virtual instances of scenario: {vi}'.format(vi=virtual_instances))

  logging.info('Installing basic dependencies')
  vm_util.RunThreaded(lambda vm: vm.Install('intel_aibench_k8'), vms)


  for vi in virtual_instances:
    if multi_node:
      if 'inference' in vi:
        vm = benchmark_spec.vm_groups['target'][0]
      elif 'broker' in vi:
        vm = benchmark_spec.vm_groups['vm_kafka'][0]
      else:
        vm = benchmark_spec.vm_groups['vm_producer'][0]
    else:
      vm = benchmark_spec.vm_groups['target'][0]
    if FLAGS.os_type.startswith('ubuntu'):
      intel_aibench_utils.SetUpNonInteractiveBash(vm)
    vm.RemoteHostCommand('echo "export VI={vi}" >> ~/.bashrc'.format(vi=vi))

  for vm in vms:
    vi = intel_aibench_utils.GetEnvValue(vm, 'VI')
    logging.info('Preparing VM {VM} for {vi}'.format(VM=vm.ip_address, vi=vi))
    vi_alias = vi

    log_dir = '{log_dir}/{ns}/'.format(log_dir=LOG_DIR, ns=namespace)
    run_log = '{log_dir}{vi}-application.log'.format(log_dir=log_dir, vi=vi)
    instances = 1
    cores = 'all'
    numa_options = None
    kmp_blocktime_override = True

    AIBENCH_HARNESS_SETTINGS['shares']['logs-location'] = log_dir
    intel_aibench_utils.ReplaceAllVariables(AIBENCH_HARNESS_SETTINGS, AIBENCH_HARNESS_SETTINGS)

    logging.info('Set up ENV and other variables')
    for key, value in AIBENCH_HARNESS_SETTINGS['virtual-instances'][vi].items():
      if key == 'cores':
        cores = value
        print(cores)
      elif key == 'repeat-count':
        instances = int(value)
      elif key == 'alias':
        vi_alias = value

    vm.RemoteHostCommand('echo "export NAMESPACE={ns}" >> ~/.bashrc'.format(ns=namespace))
    vm.RemoteHostCommand('echo "export LOG_DIR={log_dir}" >> ~/.bashrc'.format(log_dir=log_dir))
    vm.RemoteHostCommand('echo "export RUN_LOG={run_log}" >> ~/.bashrc'.format(run_log=run_log))
    vm.RemoteHostCommand('echo "export INSTANCES={instances}" >> ~/.bashrc'
                         .format(instances=instances))
    for key, value in AIBENCH_HARNESS_SETTINGS['virtual-instances'][vi]['env'].items():
      if key == 'NUMA_OPTIONS':
        numa_options = value
      elif key == 'KMP_BLOCKTIME':
        kmp_blocktime_override = False
      vm.RemoteHostCommand('echo "export {key}={value}" >> ~/.bashrc'.format(key=key, value=value))

    logging.info('Downloading data required for {vi} from Cumulus S3 bucket'.format(vi=vi))
    data_dir = os.path.join(AIBENCH_HARNESS_SETTINGS['shares']['shared-storage-partition'], 'Data')
    intel_aibench_utils.PullData(vm, vi_alias, data_dir)

    logging.info('Creating log directory to store run artifacts')
    intel_aibench_utils.CreateDirectory(vm, log_dir)

    logging.info('Generating setup commands')
    SETUP_COMMANDS.append([vm, 'cd / && ./h-setup-scenario.sh >> {run_log} 2>&1'
                           .format(run_log=run_log)])

    logging.info('Generating NUMACTL run commands')
    for i in range(0, instances):
      instance_log_dir = '{log_dir}{vi}-{instance}'.format(log_dir=log_dir, vi=vi, instance=i)
      intel_aibench_utils.CreateDirectory(vm, instance_log_dir)
      base_cmd = 'cd / && '
      print(cores)
      cpus, mem = intel_aibench_utils.GetCpusAndMem(vm, vi, i, instances, cores, numa_options,
                                                    kmp_blocktime_override, instance_log_dir)
      numa_cmd = 'numactl --physcpubind={0} --membind={1} '.format(cpus, mem)
      vm.RemoteHostCommand('echo "\nNUMA Command: \n{cmd}" >> {log_dir}/numa_core_calculation.log'
                           .format(cmd=numa_cmd, log_dir=instance_log_dir))
      numa_cmd += './h-start-scenario.sh {log}'.format(log=instance_log_dir)
      NUMA_RUN_COMMANDS.append([vm, base_cmd + numa_cmd])

    logging.info('Running setup scripts')
    vm_util.RunThreaded(intel_aibench_utils.Run, SETUP_COMMANDS)


def Run(benchmark_spec):
  """Run AIBench scenario and gather results

  Args:
      benchmark_spec: The benchmark specification.

  Returns:
      A list of sample. Sample objects.
  """

  logging.info("AIBench Run")
  vms = benchmark_spec.vms

  namespace = FLAGS.run_uri
  scenario = FLAGS.aibench_scenario
  virtual_instances = AIBENCH_HARNESS_SETTINGS['scenarios'][scenario]['virtual-instances']
  virtual_instances = virtual_instances.split(',')
  nodes = len(virtual_instances)
  multi_node = intel_aibench_utils.IsMultiNode(nodes)
  parser = AIBENCH_HARNESS_SETTINGS['scenarios'][scenario]['parser']
  result_dir = vm_util.PrependTempDir(scenario)
  metadata = {}
  results = []

  logging.info('Running {s}'.format(s=scenario))
  vm_util.RunThreaded(intel_aibench_utils.Run, NUMA_RUN_COMMANDS)

  os.mkdir(result_dir)
  for vm in vms:
    vi = intel_aibench_utils.GetEnvValue(vm, 'VI')
    logging.info('Downloading results of {vi} from VM {VM}'.format(vi=vi, VM=vm.ip_address))
    intel_aibench_utils.DownloadResults_k8(vm, vi, namespace, LOG_DIR, result_dir)

  logging.info('Parsing logs')
  vm_parse = benchmark_spec.vm_groups['target'][0]
  vm_parse.RemoteHostCommand('mkdir -p /parser && chmod 777 /parser')
  vm_parse.RemoteHostCommand('mv {aibench_dir}/{parser} /parser/'
                             .format(aibench_dir=AIBENCH_DIR, parser=parser))
  vm_parse.PullFile(vm_util.GetTempDir(), '/parser/')
  call(['python', vm_util.PrependTempDir(parser), '-d', result_dir])

  logging.info('Creating metadata dictionary')
  metadata['scenario'] = scenario
  metadata['virtual_instances'] = virtual_instances
  metadata['number of nodes'] = nodes
  metadata['workload_type'] = 'multi-node' if multi_node else 'single-node'
  metadata['SUT logs'] = '{log_dir}/{ns}'.format(log_dir=LOG_DIR, ns=namespace)
  for vm in vms:
    vi = intel_aibench_utils.GetEnvValue(vm, 'VI')
    metadata['{vi} config'.format(vi=vi)] = '{i} instance(s), {c} core(s), {cpi} core(s) per instance' \
        .format(i=intel_aibench_utils.GetEnvValue(vm, 'INSTANCES'),
                c=intel_aibench_utils.GetEnvValue(vm, 'CORES_USED'),
                cpi=intel_aibench_utils.GetEnvValue(vm, 'TF_INTRA_OP'))

  results = intel_aibench_utils.CreateMetadataDict(metadata, results, result_dir)
  return results


def Cleanup(benchmark_spec):
  logging.info("AIBench Cleanup")
  logging.info("Nothing to cleanup in AIBench!")
