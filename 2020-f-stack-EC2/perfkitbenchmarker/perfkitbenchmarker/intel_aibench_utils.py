# Copyright 2015 PerfKitBenchmarker Authors. All rights reserved.
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

"""Helper functions for running AIBench on VMs and K8s"""
import boto3
import json
import logging
import os
import sys
from collections import OrderedDict
from subprocess import call
from perfkitbenchmarker import sample
from perfkitbenchmarker.linux_packages import INSTALL_DIR


AIBENCH_DIR = '{install_dir}/aibench'.format(install_dir=INSTALL_DIR)
s3 = boto3.resource('s3')
bucket = s3.Bucket('cumulus')
INTERNAL_REFERENCE_START = '${'
INTERNAL_REFERENCE_END = '}'
SCRIPT_CODE = """#!/bin/bash
source ~/.bashrc
{s}
"""
SCRIPT_IN_FORMAT = 'echo "{script_code}" > {directory}/{script}; chmod +x {directory}/{script}'


def GetConfig(pkb_config, virtual_instances):
  """Edit benchmark config for workload"""
  vi_count = len(virtual_instances.split(','))
  pkb_config['vm_groups']['target']['vm_count'] = vi_count
  return pkb_config


def IsMultiNode(vi_count):
  """Check if workload is single or multi node"""
  if vi_count > 1:
    return True
  return False


def CheckConfigFile(yaml_file):
  """Check if config file is present"""
  if not os.path.exists(yaml_file):
    raise IOError('YAML file not found: {y}'.format(y=yaml_file))


def ValidateMachines(vms, virtual_instances):
  """Check if number of virtual instances match the VMs available"""
  if len(vms) != len(virtual_instances):
    raise ValueError('Scenario has {0} virtual instances, but found {1} VMs. Count of virtual'
                     'instances and VMs must match.'.format(len(virtual_instances), len(vms)))


def PrepareMultiNode(vi, vm):
  """Establish communication to broker"""
  broker_hostname_alias = None
  broker_hostname, _ = vm.RemoteHostCommand('cat /etc/hostname')
  broker_ip, _ = vm.RemoteHostCommand('hostname -i')
  broker_ip = broker_ip.split(' ')[(len(broker_ip.split(' '))) - 1]
  broker_hostname_alias = '{ip}\t{hostname}\t{vi}-0'.format(ip=broker_ip.strip(),
                                                            hostname=broker_hostname.strip(), vi=vi)
  if broker_hostname_alias is None:
    raise Exception('Unable to setup multi-node communication.')
  else:
    return broker_hostname_alias


def AddHost(vm, host_alias):
  """Add to /etc/hosts file"""
  vm.RemoteHostCommand('echo "{s}" | sudo tee -a /etc/hosts'.format(s=host_alias))


def RemoveHost(vm, host_alias):
  """Remove from /etc/hosts"""
  search_pattern = ''
  for h in host_alias.split(' '):
    if h.strip() != '':
      search_pattern += h + '\\t'
  search_pattern = search_pattern[:-2]
  vm.RemoteHostCommand('sudo sed -i "/{search}/d" /etc/hosts'.format(search=search_pattern))


def IncreaseSSHConnections(vm, max_ssh, os_type):
  """Increase maximum number of SSH connections on VM"""
  vm.RemoteHostCommand(r'sudo sed -i -e "s/.*MaxSessions.*/MaxSessions {0}/" '
                       '/etc/ssh/sshd_config'.format(max_ssh))
  vm.RemoteHostCommand(r'sudo sed -i -e "s/.*MaxStartups.*/MaxStartups {0}/" '
                       '/etc/ssh/sshd_config'.format(max_ssh))
  if os_type.startswith('ubuntu'):
    vm.RemoteCommand('sudo service ssh restart')
  elif os_type.startswith('centos'):
    vm.RemoteHostCommand('sudo systemctl restart sshd.service')


def SetUpNonInteractiveBash(vm):
  """Enable sourcing bashrc in Ubuntu when run non-interactively"""
  vm.RemoteHostCommand('sed -i "/case \$- in/,+3 d" ~/.bashrc')
  vm.RemoteHostCommand("sed -i '/\[ -z \"$PS1\" \]/ d' ~/.bashrc")


def EnablePermission(vm, directory):
  """Give full permission to directory"""
  vm.RemoteHostCommand('sudo chmod -R 777 {d}'.format(d=directory))


def CreateDirectory(vm, directory):
  """Create directory and give full permission"""
  vm.RemoteHostCommand('sudo mkdir -p {d}'.format(d=directory))
  EnablePermission(vm, directory)


def PullAIBenchCode(vm, install_dir):
  """Pull AIBench code from S3 bucket"""
  code_tar = 'aibench/Code/aibench.tar.gz'
  obj = list(bucket.objects.filter(Prefix=code_tar))
  if len(obj) > 0:
    logging.info('Downloading aibench.tar.gz')
    vm.RemoteHostCommand('cd {install_dir} && aws s3 cp s3://cumulus/aibench/Code/aibench.tar.gz '
                         'aibench.tar.gz --region=us-east-1'.format(install_dir=install_dir))
    vm.RemoteHostCommand('cd {install_dir} && sudo tar -xvf aibench.tar.gz'
                         .format(install_dir=install_dir))
  else:
    raise Exception('No AIBench code found on Cumulus S3 bucket, cannot run workload.')


def PullData(vm, vi, data_dir):
  """Pull data required by virtual instance from S3 bucket"""
  if 'broker' in vi:
    logging.info('No data required for {vi} from Cumulus S3 bucket'.format(vi=vi))
  else:
    data_tar = 'aibench/Data/{vi}.tar.gz'.format(vi=vi)
    obj = list(bucket.objects.filter(Prefix=data_tar))
    if len(obj) > 0:
      logging.info('Downloading {vi}.tar.gz'.format(vi=vi))
      CreateDirectory(vm, data_dir)
      vm.RemoteHostCommand('cd {data_dir} && aws s3 cp s3://cumulus/aibench/Data/'
                           '{vi}.tar.gz {vi}.tar.gz --region=us-east-1'
                           .format(data_dir=data_dir, vi=vi))
      vm.RemoteHostCommand('cd {data_dir} && sudo tar -xvf {vi}.tar.gz'.format(vi=vi,
                                                                               data_dir=data_dir))
      EnablePermission(vm, data_dir)
    else:
      raise Exception('No data found for {vi} on Cumulus S3 bucket, cannot run workload.'
                      .format(vi=vi))


def GetEnvValue(vm, env_variable):
  """Get value of ENV variable"""
  CreateDirectory(vm, AIBENCH_DIR)
  script = 'env-{var}.sh'.format(var=env_variable)
  variable = '\${var}'.format(var=env_variable)
  command = '"echo {var}"'.format(var=variable)
  script_code = SCRIPT_CODE.format(s=command)
  vm.RemoteHostCommand(SCRIPT_IN_FORMAT.format(script_code=script_code,
                                               directory=AIBENCH_DIR, script=script))
  vm.RemoteHostCommand('sudo cp -p {directory}/{script} /'.format(directory=AIBENCH_DIR,
                                                                  script=script))
  val, _ = vm.RemoteHostCommand('cd / && ./{script}'.format(script=script))
  return val.strip()


def _GenerateCoreList(inputstr=""):
  """Generates a list of cores based on cores assigned"""
  selection = set()
  invalid = set()
  tokens = [x.strip() for x in inputstr.split(',')]
  for i in tokens:
    if len(i) > 0:
      if i[:1] == '<':
        i = '1-{s}'.format(s=i[1:])

    try:
      selection.add(int(i))
    except:
      try:
        token = [int(k.strip()) for k in i.split('-')]
        if len(token) > 1:
          token.sort()
          first = token[0]
          last = token[len(token) - 1]
          for x in range(first, last + 1):
            selection.add(x)
      except:
        invalid.add(i)
  if len(invalid) > 0:
    raise Exception('Invalid Set: {s}'.format(s=str(invalid)))
  return selection


def _DetermineCoresList(vm, cores_assigned, instance_number, instances, cores_available, log_dir):
  """Determines cores for an instance"""
  MAXIMUM_LEGITIMATE_CORE = int(cores_available[-1][-1])

  if cores_assigned == 'all':
    end_core = int(cores_available[-1][-1]) + 1
    set_of_cores = set(range(0, end_core))
    set_of_cores = list(set_of_cores)
  else:
    set_of_cores = _GenerateCoreList(cores_assigned)
    set_of_cores = list(set_of_cores)
    set_of_cores.sort()
    set_of_cores = list(OrderedDict.fromkeys(set_of_cores))
    if set_of_cores[-1] > MAXIMUM_LEGITIMATE_CORE:
      while True:
        err = 'Illegitimate number of cores provided.'
        vm.RemoteHostCommand('echo "{err}" >> {log_dir}/numa_core_calculation.log'
                             .format(err=err, log_dir=log_dir))
        raise ValueError(err)

  chunk = len(set_of_cores) // instances
  your_set = set_of_cores[chunk * instance_number:chunk * (instance_number + 1)]
  return your_set


def _DetermineMemoryAllocationPolicy(numa_options, cores_set, cores_available):
  """Determines memory binding policy"""
  if numa_options is None or numa_options == '':
    nodecount = []
    for node in cores_available:
      nodecount.append(0)
    for core in cores_set:
      for node in range(0, len(cores_available)):
        if core in cores_available[node]:
          nodecount[node] += 1
    numa_options = ''
    for node in range(0, len(nodecount)):
      if nodecount[node] > 0:
        numa_options += str(node) + ','
    numa_options = numa_options[0:-1]
  else:
    numa_options.split('=')[1]
  return numa_options


def _GenerateTensorFlowVariables(vm, cores_set, cores_available, kmp_blocktime_override, instances,
                                 log_dir, export=False):
  """Exports and logs TF variables"""
  inter_op = 1
  intra_op = len(cores_set)
  omp_num_threads = len(cores_set)
  kmp_affinity = 'granularity=fine,compact'

  vm.RemoteHostCommand('echo "\nTensorFlow Variables Overriden:" >> '
                       '{log_dir}/numa_core_calculation.log'
                       .format(log_dir=log_dir))
  vm.RemoteHostCommand('echo "INTER_OP = {inter_op}" >> {log_dir}/numa_core_calculation.log'
                       .format(inter_op=inter_op, log_dir=log_dir))
  vm.RemoteHostCommand('echo "INTRA_OP = {intra_op}" >> {log_dir}/numa_core_calculation.log'
                       .format(intra_op=intra_op, log_dir=log_dir))
  vm.RemoteHostCommand('echo "OMP_NUM_THREADS = {num_threads}" >> {log_dir}/'
                       'numa_core_calculation.log'.format(num_threads=omp_num_threads,
                                                          log_dir=log_dir))
  vm.RemoteHostCommand('echo "KMP_AFFINITY = {kmp_affinity}" >> {log_dir}/numa_core_calculation.log'
                       .format(kmp_affinity=kmp_affinity, log_dir=log_dir))
  if kmp_blocktime_override:
    kmp_blocktime = len(cores_available)
    vm.RemoteHostCommand('echo "KMP_BLOCKTIME = {kmp_blocktime}" >> {log_dir}/'
                         'numa_core_calculation.log'.format(kmp_blocktime=kmp_blocktime,
                                                            log_dir=log_dir))

  if export:
    vm.RemoteHostCommand('echo "export TF_INTER_OP=1" >> ~/.bashrc')
    vm.RemoteHostCommand('echo "export TF_INTRA_OP={intra_op}" >> ~/.bashrc'
                         .format(intra_op=intra_op))
    vm.RemoteHostCommand('echo "export OMP_NUM_THREADS={num_threads}" >> ~/.bashrc'
                         .format(num_threads=omp_num_threads))
    vm.RemoteHostCommand('echo "export KMP_AFFINITY=\'{kmp_affinity}\'" >> ~/.bashrc'
                         .format(kmp_affinity=kmp_affinity))
    vm.RemoteHostCommand('echo "export CORES_USED={c}" >> ~/.bashrc'
                         .format(c=(instances * omp_num_threads)))
    if kmp_blocktime_override:
      vm.RemoteHostCommand('echo "export KMP_BLOCKTIME=\'{kmp_blocktime}\'" >> ~/.bashrc'
                           .format(kmp_blocktime=kmp_blocktime))


def GetCpusAndMem(vm, virtual_instance, instance_number, instances, cores_assigned, numa_options,
                  kmp_blocktime_override, log_dir):
  """Generates CPU IDs and memory policy for instance"""
  stdout, _ = vm.RemoteHostCommand('numactl -H')
  numactl_lines = (str(stdout)).split('\n')
  vm.RemoteHostCommand('echo "For Instance: {vi}-{i}" >> {log_dir}/numa_core_calculation.log'
                       .format(vi=virtual_instance, i=instance_number, log_dir=log_dir))

  str_node_cores = []
  cores_available = []
  for l in numactl_lines:
    if 'cpus:' in l:
      str_node_cores.append(l.split('cpus:')[1].split(' ')[1:])
  for cores_in_node in str_node_cores:
    newlist = []
    for core in cores_in_node:
      newlist.append(int(core))
    cores_available.append(newlist)

  cores_set = _DetermineCoresList(vm, cores_assigned, instance_number, instances, cores_available,
                                  log_dir)
  if not cores_set:
    err = 'Range of cores is invalid. Unable to generate NUMA run command.'
    vm.RemoteHostCommand('echo "{err}" >> {log_dir}/numa_core_calculation.log'
                         .format(err=err, log_dir=log_dir))
    raise Exception(err)

  memset = _DetermineMemoryAllocationPolicy(numa_options, cores_set, cores_available)

  if instance_number == instances - 1:
    _GenerateTensorFlowVariables(vm, cores_set, cores_available, kmp_blocktime_override, instances,
                                 log_dir, True)
  else:
    _GenerateTensorFlowVariables(vm, cores_set, cores_available, kmp_blocktime_override, instances,
                                 log_dir)
  return ','.join(str(s) for s in cores_set), memset


def Run(run_info):
  """Runs a command on a VM"""
  vm = run_info[0]
  command = run_info[1]
  vm.RemoteHostCommand(command)


def DownloadResults(vm, vi, namespace, remote_log_dir, local_result_dir):
  """Download workload results to host"""
  try:
    vm.RemoteHostCommand('cd {log_dir} && sudo tar -zcf {ns}.tar.gz {ns}'
                         .format(log_dir=remote_log_dir, ns=namespace))
    vm.PullFile(local_result_dir, '{log_dir}/{ns}.tar.gz'.format(log_dir=remote_log_dir,
                                                                 ns=namespace))
    tar_file = os.path.join(local_result_dir, '{ns}.tar.gz'.format(ns=namespace))
    call(['tar', '-xvf', tar_file, '-C', local_result_dir, '--strip-components=1'])
  except:
    logging.info('Unable to download results of {vi} from {vm}'.format(vi=GetEnvValue(vm, 'VI'),
                                                                       vm=vm.ip_address))


def DownloadResults_k8(vm, vi, namespace, remote_log_dir, local_result_dir):
  """Download workload results to host"""
  try:
    vm.RemoteHostCommand('cd {log_dir} && sudo tar -zcf {ns}.tar.gz {ns}'
                         .format(log_dir=remote_log_dir, ns=namespace))
    vm.PullFile(local_result_dir, '{log_dir}/{ns}'.format(log_dir=remote_log_dir,
                                                          ns=namespace))
  except:
    logging.info('Unable to download results of {vi} from {vm}'.format(vi=GetEnvValue(vm, 'VI'),
                                                                       vm=vm.ip_address))


def CreateMetadataDict(metadata, results, result_dir):
  """Create metadata dict to be displayed in run results"""
  try:
    with open(os.path.join(result_dir, 'cumulus_metrics'), 'r') as f:
      content = f.read().replace('\'', '"')
      json_content = json.loads(content)
      if 'additional_data' in json_content.keys():
        for key, val in json_content['additional_data'].items():
          metadata[str(key)] = str(val)
    results.append(sample.Sample(str(json_content['metric']), str(json_content['value']),
                                 str(json_content['unit']), metadata))
    return results
  except:
    raise Exception('Unable to generate metadata dictionary from logs.')


def _ReplaceReference(content, yaml_data, start_pattern, end_pattern):
  """Resolve references in file"""
  start_env_pattern = 'env::'
  start_offset = len(start_pattern)
  end_offset = len(end_pattern)
  start_env_offset = len(start_env_pattern)
  start = content.find(start_pattern)
  pattern_found = False

  while start != -1:
    pattern_found = True
    end = content.find(end_pattern, start)
    template_key = content[start + start_offset:end]
    replace_key = content[start:end + end_offset]
    t = yaml_data
    for key in template_key.split('.'):
      if key in t:
        t = t[key]
      else:
        raise Exception('Key "{k}" was not found in {r}'.format(k=key, r=list(t.keys())))
    value = str(t).strip()
    if value.startswith(start_env_pattern):
      value = '${s}'.format(s=value[start_env_offset:])
    content = content.replace(replace_key, value)
    start = content.find(start_pattern)
  return pattern_found, content


def _CheckAndReplaceInternalReference(yaml_data, location):
  """Get reference content in file"""
  pattern_found, content = _ReplaceReference(content=str(location),
                                             yaml_data=yaml_data,
                                             start_pattern=INTERNAL_REFERENCE_START,
                                             end_pattern=INTERNAL_REFERENCE_END,
                                             )
  return content


def ReplaceAllVariables(yaml_data, location):
  """Check for all references and replace them"""
  if isinstance(location, dict):
    for key, value in location.items():
      if isinstance(value, dict):
        ReplaceAllVariables(yaml_data, location[key])
      else:
        location[key] = _CheckAndReplaceInternalReference(yaml_data, location[key])
  else:
    yaml_data[location] = _CheckAndReplaceInternalReference(yaml_data, yaml_data[location])
  return location
