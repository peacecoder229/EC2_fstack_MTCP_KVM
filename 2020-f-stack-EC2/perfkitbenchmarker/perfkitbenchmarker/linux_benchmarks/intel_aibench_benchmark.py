# Copyright 2014 PerfKitBenchmarker Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""AIBench benchmark
This benchmark enables the running of end-to-end, data center-focussed Machine Learning and
Deep Learning inference workloads on Virtual Machines.
AIBench Wiki: http://goto.intel.com/AIBench
AIBench Code: https://github.intel.com/Data-Center-E2E-Benchmarks/AIBench/tree/project-cumulus
"""
import itertools
import json
import logging
import os
import sys
import yaml
from subprocess import call
from perfkitbenchmarker import configs
from absl import flags
from perfkitbenchmarker import sample
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import intel_aibench_utils
from perfkitbenchmarker.linux_packages import INSTALL_DIR


FLAGS = flags.FLAGS
flags.DEFINE_string('aibench_scenario', 'transformer-nmt-standalone-inference',
                    'The scenario to be run remotely by AIBench.')
flags.DEFINE_string('aibench_harness_yaml', 'perfkitbenchmarker/data/intel_aibench/'
                    'harness-settings-transformer-nmt-standalone-inference.yaml',
                    'The runtime configuration file of scenario to run.')

BENCHMARK_NAME = 'intel_aibench'
BENCHMARK_CONFIG = """
intel_aibench:
  description: Runs AIBench
  vm_groups:
    target:
      vm_spec: *default_single_core
      disk_spec: *default_500_gb
      disk_count: 0
"""

AIBENCH_HARNESS_SETTINGS = {}
AIBENCH_DIR = '{install_dir}/aibench'.format(install_dir=INSTALL_DIR)
LOG_DIR = '/tmp/aibench/runs'
INSTALL_COMMANDS = []
SETUP_COMMANDS = []
NUMA_RUN_COMMANDS = []
broker_hostname = ""


def GetConfig(user_config):
  """Reads the AIBench run time configration file - harness_settings"""
  logging.info('AIBench GetConfig')
  intel_aibench_utils.CheckConfigFile(FLAGS.aibench_harness_yaml)

  with open(FLAGS.aibench_harness_yaml) as f:
    global AIBENCH_HARNESS_SETTINGS
    AIBENCH_HARNESS_SETTINGS = yaml.safe_load(f)

  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
  scenario = FLAGS.aibench_scenario
  virtual_instances = AIBENCH_HARNESS_SETTINGS['scenarios'][scenario]['virtual-instances']
  config = intel_aibench_utils.GetConfig(config, virtual_instances)
  return config


def Prepare(benchmark_spec):
  """Prepare VM to run AIBench

  Args:
      benchmark_spec: The benchmark specification. Contains all data that is required
      to run the benchmark.
  """
  logging.info('AIBench Prepare')
  benchmark_spec.always_call_cleanup = True
  vms = benchmark_spec.vms

  namespace = FLAGS.run_uri
  scenario = FLAGS.aibench_scenario
  virtual_instances = AIBENCH_HARNESS_SETTINGS['scenarios'][scenario]['virtual-instances']
  virtual_instances = virtual_instances.split(',')
  multi_node = intel_aibench_utils.IsMultiNode(len(virtual_instances))
  logging.info('Scenario: {s}'.format(s=scenario))
  logging.info('Virtual instances of scenario: {vi}'.format(vi=virtual_instances))

  intel_aibench_utils.ValidateMachines(vms, virtual_instances)

  logging.info('Installing basic dependencies')
  vm_util.RunThreaded(lambda vm: vm.Install('intel_aibench'), vms)

  logging.info('Assigning virtual instances to VMs')
  for vi, vm in zip(virtual_instances, vms):
    if FLAGS.os_type.startswith('ubuntu'):
      intel_aibench_utils.SetUpNonInteractiveBash(vm)
    vm.RemoteHostCommand('echo "export VI={vi}" >> ~/.bashrc'.format(vi=vi))
    if multi_node and 'broker' in vi:
      global broker_hostname
      broker_hostname = intel_aibench_utils.PrepareMultiNode(vi, vm)

  for vm in vms:
    vi = intel_aibench_utils.GetEnvValue(vm, 'VI')
    logging.info('Preparing VM {VM} for {vi}'.format(VM=vm.ip_address, vi=vi))
    vi_alias = vi

    if multi_node:
      intel_aibench_utils.AddHost(vm, broker_hostname)

    intel_aibench_utils.IncreaseSSHConnections(vm, 10000, FLAGS.os_type)

    logging.info('Downloading AIBench code from Cumulus S3 bucket')
    intel_aibench_utils.PullAIBenchCode(vm, INSTALL_DIR)
    intel_aibench_utils.EnablePermission(vm, AIBENCH_DIR)

    log_dir = '{log_dir}/{ns}/'.format(log_dir=LOG_DIR, ns=namespace)
    run_log = '{log_dir}{vi}-application.log'.format(log_dir=log_dir, vi=vi)
    instances = 1
    cores = 'all'
    numa_options = None
    kmp_blocktime_override = True

    AIBENCH_HARNESS_SETTINGS['shares']['logs-location'] = log_dir
    intel_aibench_utils.ReplaceAllVariables(AIBENCH_HARNESS_SETTINGS, AIBENCH_HARNESS_SETTINGS)
    vm.RemoteHostCommand('cd / && ls | sudo dd of=root_files.txt')

    logging.info('Set up ENV and other variables')
    for key, value in AIBENCH_HARNESS_SETTINGS['virtual-instances'][vi].items():
      if key == 'cores':
        cores = value
      elif key == 'repeat-count':
        instances = int(value)
      elif key == 'alias':
        vi_alias = value
    vi_template = '{aibench_dir}/templates/{vi}'.format(aibench_dir=AIBENCH_DIR, vi=vi_alias)
    vm.RemoteHostCommand('echo "export NAMESPACE={ns}" >> ~/.bashrc'.format(ns=namespace))
    if 'broker' in vi:
      vm.RemoteHostCommand('echo "export LOG_DIR={log_dir}/{vi}-0" >> ~/.bashrc'
                           .format(log_dir=log_dir, vi=vi))
    else:
      vm.RemoteHostCommand('echo "export LOG_DIR={log_dir}" >> ~/.bashrc'.format(log_dir=log_dir))
    vm.RemoteHostCommand('echo "export RUN_LOG={run_log}" >> ~/.bashrc'.format(run_log=run_log))
    vm.RemoteHostCommand('echo "export INSTANCES={instances}" >> ~/.bashrc'
                         .format(instances=instances))
    vm.RemoteHostCommand('echo "export USERNAME={uname}" >> ~/.bashrc'
                         .format(uname=intel_aibench_utils.GetEnvValue(vm, 'USER')))
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

    logging.info('Resolving references in scripts')
    vm.RemoteHostCommand('python {d}/reference_resolver.py -t {t}/ -g {d}/generator-settings.yaml '
                         '>> {run_log} 2>&1'.format(d=AIBENCH_DIR, t=vi_template, run_log=run_log))

    logging.info('Copying scripts to root directory')
    vm.RemoteHostCommand('cd {vi_template}/build_scripts/ && sudo cp -p -r * /'
                         .format(vi_template=vi_template))
    vm.RemoteHostCommand('cd {vi_template}/workload_scripts/ && sudo cp -p -r * /'
                         .format(vi_template=vi_template))
    vm.RemoteHostCommand('cd {aibench_dir}/templates/common/ && sudo cp -p -r * /'
                         .format(aibench_dir=AIBENCH_DIR))

    logging.info('Generating commands to install workload dependencies')
    INSTALL_COMMANDS.append([vm, 'cd / && sudo ./init.sh >> {run_log} 2>&1'
                             .format(run_log=run_log)])

    logging.info('Generating setup commands')
    SETUP_COMMANDS.append([vm, 'cd / && ./h-setup-scenario.sh >> {run_log} 2>&1'
                           .format(run_log=run_log)])

    logging.info('Generating NUMACTL run commands')
    for i in range(0, instances):
      instance_log_dir = '{log_dir}{vi}-{instance}'.format(log_dir=log_dir, vi=vi, instance=i)
      intel_aibench_utils.CreateDirectory(vm, instance_log_dir)
      base_cmd = 'cd / && '
      cpus, mem = intel_aibench_utils.GetCpusAndMem(vm, vi, i, instances, cores, numa_options,
                                                    kmp_blocktime_override, instance_log_dir)
      numa_cmd = 'numactl --physcpubind={0} --membind={1} '.format(cpus, mem)
      vm.RemoteHostCommand('echo "\nNUMA Command: \n{cmd}" >> {log_dir}/numa_core_calculation.log'
                           .format(cmd=numa_cmd, log_dir=instance_log_dir))
      numa_cmd += './h-start-scenario.sh {log}'.format(log=instance_log_dir)
      NUMA_RUN_COMMANDS.append([vm, base_cmd + numa_cmd])

  logging.info('Installing workload dependencies')
  vm_util.RunThreaded(intel_aibench_utils.Run, INSTALL_COMMANDS)

  logging.info('Running setup scripts')
  vm_util.RunThreaded(intel_aibench_utils.Run, SETUP_COMMANDS)


def Run(benchmark_spec):
  """Run AIBench scenario and gather results

  Args:
      benchmark_spec: The benchmark specification. Contains all data that is required
      to run the benchmark.

  Returns:
      A list of sample. Sample objects.
  """
  logging.info('AIBench Run')
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
    intel_aibench_utils.DownloadResults(vm, vi, namespace, LOG_DIR, result_dir)

  logging.info('Parsing logs')
  (benchmark_spec.vm_groups['target'][0]).PullFile(vm_util.GetTempDir(),
                                                   '{aibench_dir}/scripts/{parser}'
                                                   .format(aibench_dir=AIBENCH_DIR, parser=parser))
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
  """Cleans up AIBench from vm.

  Args:
      benchmark_spec: The benchmark specification. Contains all data that is required
      to run the benchmark.
  """
  logging.info('AIBench Cleanup')
  vms = benchmark_spec.vms

  namespace = FLAGS.run_uri
  scenario = FLAGS.aibench_scenario
  virtual_instances = AIBENCH_HARNESS_SETTINGS['scenarios'][scenario]['virtual-instances']
  multi_node = intel_aibench_utils.IsMultiNode(len(virtual_instances.split(',')))
  result_dir = vm_util.PrependTempDir(scenario)
  parser = AIBENCH_HARNESS_SETTINGS['scenarios'][scenario]['parser']
  shared_storage = AIBENCH_HARNESS_SETTINGS['shares']['shared-storage-partition']

  for vm in vms:
    vi = intel_aibench_utils.GetEnvValue(vm, 'VI')
    logging.info('Cleaning up artifacts of {vi} on VM {VM}'.format(vi=vi, VM=vm.ip_address))
    run_log = '{log_dir}/{ns}/{vi}-application.log'.format(log_dir=LOG_DIR, ns=namespace, vi=vi)

    if multi_node:
      intel_aibench_utils.RemoveHost(vm, broker_hostname)
      if 'broker' in vi:
        vm.RemoveFile('/opt/kafka')

    vm.RemoteHostCommand('cd / && ./h-stop-scenario.sh >> {run_log} 2>&1'.format(run_log=run_log))
    vm.RemoteHostCommand('cd / && ./h-destroy-scenario.sh >> {run_log} 2>&1'
                         .format(run_log=run_log))
    vm.RemoteHostCommand('cd / && ./h-stop-container.sh >> {run_log} 2>&1'.format(run_log=run_log))
    vm.RemoteHostCommand('cd / && python cleanup-vm.py >> {run_log} 2>&1'.format(run_log=run_log))
    vm.RemoteHostCommand('#!/bin/bash && source ~/.bashrc')
    vm.RemoteHostCommand('sed -i -e "/^unset/ d" ~/.bashrc')
    vm.RemoveFile(shared_storage[:shared_storage.rindex('/')])

  logging.info('Copying run settings file to result dir')
  call(['cp', FLAGS.aibench_harness_yaml, result_dir])

  logging.info('Cleaning up remains of run on PKB host')
  call(['sudo', 'rm', '-rf', vm_util.PrependTempDir(parser)])
  for file in os.listdir(result_dir):
    if 'tar.gz' in file:
      call(['sudo', 'rm', '-rf', os.path.join(result_dir, file)])

  logging.info('AIBench Cleanup done!')
