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

"""Utilities for running PHP/HHVM workloads"""

import json
import logging
import os
import re
from six import StringIO
import yaml

from collections import OrderedDict
from perfkitbenchmarker import data
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import sample
from perfkitbenchmarker import os_types
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker.linux_packages import intel_webtier_provisioning
from absl import flags

SERVER_GROUP = 'server'
CLIENT_GROUP = 'client'
DATABASE_GROUP = 'database'

FLAGS = flags.FLAGS
flags.DEFINE_boolean("intel_wordpress_https_enabled", False, "If True, WordPress will run using HTTPS. The default is False, defaulting to HTTP")
flags.DEFINE_enum("intel_wordpress_https_tls_version", "TLSv1.3", ('TLSv1.2', 'TLSv1.3'), "TLS version to be used by the workload with HTTPS mode. Default is TLSv1.3.")
flags.DEFINE_string("intel_wordpress_https_cipher", "TLS_AES_256_GCM_SHA384", "Cipher to be used by the workload with HTTPS mode. Only ciphers in TLSv1.2 can be specified.")
flags.DEFINE_boolean("intel_wordpress_rsamb_enabled", False, "If True, WordPress will run using HTTPS with RSA and multi-buffer optimizations for ICX only. The default is False")
flags.DEFINE_boolean("intel_wordpress_icx_enabled", False, "If True, WordPress will run using HTTPS with RSA, multi-buffer and aes-gcm optimizations for ICX only. The default is False")


def Prepare(benchmark_spec, workload_engine, mt=False):
  """Prepare the virtual machines to run."""
  vm_dict = benchmark_spec.vm_groups
  if mt:
    server_vms = vm_dict[SERVER_GROUP]
    client_vms = vm_dict[CLIENT_GROUP]
    database_vms = vm_dict[DATABASE_GROUP]
    all_vms = server_vms + client_vms + database_vms
  else:
    all_vms = vm_dict['target']
    server_vms = vm_dict['target']

  # Clean up the install dir before any provisioning
  vm_util.RunThreaded(lambda vm: vm.Uninstall('intel_webtier_provisioning'), all_vms)
  # Provision all VMs with hhvm-provisioning and the common pre-req packages
  vm_util.RunThreaded(lambda vm: vm.Install('intel_webtier_provisioning'), all_vms)

  intel_webtier_provisioning.ProvisionVMs(server_vms[0], SERVER_GROUP)
  if mt:
    intel_webtier_provisioning.ProvisionVMs(client_vms[0], CLIENT_GROUP)
    intel_webtier_provisioning.ProvisionVMs(database_vms[0], DATABASE_GROUP)
  intel_webtier_provisioning.OssInstallOnServer(server_vms[0])

  # run the provisioning and choose the playbook
  # according to the wordpress version.
  # Multi-tier only works with wordpress v5.2
  if mt:
    wordpress_version = 'v5.2'
  else:
    wordpress_version = FLAGS.intel_wordpress_version
  webtier_path = os.path.join('webtier-provisioning', 'webtier')
  hosts_path = os.path.join(webtier_path, 'hosts')
  base_cmd = 'cd {inst_dir} && ansible-playbook -i {hosts} {webtier}/'.format(
      inst_dir=INSTALL_DIR,
      hosts=hosts_path,
      webtier=webtier_path)
  server_cmd = base_cmd
  if wordpress_version == 'v5.2':
    server_cmd += 'server_'
  server_cmd += workload_engine + '_pkb.yml'
  server_vms[0].RemoteHostCommand(server_cmd)
  if mt:
    client_cmd = base_cmd + CLIENT_GROUP + '_' + workload_engine + '_pkb.yml'
    client_vms[0].RemoteHostCommand(client_cmd)
    database_cmd = base_cmd + DATABASE_GROUP + '_' + workload_engine + '_pkb.yml'
    database_vms[0].RemoteHostCommand(database_cmd)

    # All etc files related changes are done after provisioning since the ClearLinux OS
    # doesn't come with default etc files and provisioning takes care of creating them
    # for ClearLinux
    # Back up the ssh related files
    client_vms[0].RemoteHostCommand('cp ~/.ssh/authorized_keys ~/.ssh/authorized_keys.original')
    server_vms[0].RemoteHostCommand('sudo cp /etc/ssh/ssh_config /etc/ssh/ssh_config.original')

    # Create the SSH keys if not already present for all VMs for password-less access
    server_vms[0].RemoteCommand('if [ ! -f ~/.ssh/id_rsa ]; \
                                 then ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa; fi')
    server_vms[0].RemoteCommand('echo "StrictHostKeyChecking no" | \
                                 sudo tee -a /etc/ssh/ssh_config')

    # Enable password-less SSH for client-server communication
    ssh_key, _ = server_vms[0].RemoteCommand("cat ~/.ssh/id_rsa.pub")
    client_vms[0].RemoteCommand('echo "{0}" >> ~/.ssh/authorized_keys'.format(ssh_key))

    # Populate server's /etc/hosts file with hostnames of client and db VMs
    # else we see low cpu-utilization because of hostname resolutions.
    # No need to copy server's hostname since its taken care of from the provisioning scripts
    client_host = " ".join([client_vms[0].internal_ip, client_vms[0].hostname])
    database_host = " ".join([database_vms[0].internal_ip, database_vms[0].hostname])
    all_hosts = client_host + '\n' + database_host
    sut_host = " ".join([server_vms[0].internal_ip, server_vms[0].hostname])

    # Back up the etc/hosts file and then modify
    server_vms[0].RemoteCommand('sudo cp /etc/hosts /etc/hosts.original')
    server_vms[0].RemoteCommand(('echo "{0}" | sudo tee -a /etc/hosts').format(all_hosts))

    # Back up the etc/hosts file and then modify
    client_vms[0].RemoteCommand('sudo cp /etc/hosts /etc/hosts.original')
    client_vms[0].RemoteCommand(('echo "{0}" | sudo tee -a /etc/hosts').format(sut_host))
    # Back up the etc/hosts file and then modify
    database_vms[0].RemoteCommand('sudo cp /etc/hosts /etc/hosts.original')
    database_vms[0].RemoteCommand(('echo "{0}" | sudo tee -a /etc/hosts').format(sut_host))


def Run(benchmark_spec,
        target_name,
        workload_engine,
        count,
        server_workers,
        client_workers,
        mt=False):
  """Run Siege and gather the results."""
  vm_dict = benchmark_spec.vm_groups
  workload_name = target_name
  if mt:
    server_vms = vm_dict[SERVER_GROUP]
    client_vms = vm_dict[CLIENT_GROUP]
    database_vms = vm_dict[DATABASE_GROUP]
    workload_name += '5_mt'
  else:
    server_vms = vm_dict['target']
    client_vms = server_vms
    database_vms = server_vms

  # configure hhvm-perf/config.yml
  logging.info("configuring the hhvm-perf workload harness")
  if workload_engine == "php":
    out, _ = server_vms[0].RemoteHostCommand('ls /usr/sbin/php-fpm*')
  elif workload_engine == "hhvm":
    out, _ = server_vms[0].RemoteHostCommand('ls /usr/bin/hhvm*')
  # get actual engine binary name
  engine_path = out.splitlines()[0]

  conf = data.ResourcePath('intel_' + workload_name + '_benchmark/config.yml')
  with open(conf) as stream:
    config = yaml.load(stream, Loader=yaml.FullLoader)

  intel_webtier_provisioning.TuneMariaDB(database_vms[0])

  config['paths']['engine'] = engine_path
  config['run']['count'] = count
  if server_workers is not None:
    config['run']['server_workers'] = str(server_workers)
  config['run']['oss_additional_params'] = ''
  if mt:
    out_user, _ = client_vms[0].RemoteHostCommand('whoami')
    client_user = out_user.splitlines()[0]
    config['run']['oss_additional_params'] = '--i-am-not-benchmarking --db-host=' \
        + database_vms[0].internal_ip + ' --remote-siege=' \
        + client_user + '@' + client_vms[0].internal_ip
    # restart mysql before running the workload
    database_vms[0].RemoteCommand('sudo systemctl restart mariadb', ignore_failure=True)
  if client_workers is not None:
    config['run']['oss_additional_params'] += "--client-threads=" + str(client_workers)

  new_conf = vm_util.PrependTempDir('config.yml')
  with open(new_conf, 'w') as stream:
    yaml.dump(config, stream)

  server_vms[0].RemoteCopy(new_conf, INSTALL_DIR + '/git/hhvm-perf')

  # run the workload
  samples = []
  logging.info("running the workload")
  tls_switch = ""
  cipher_switch = ""
  https_switch = "--https" if FLAGS.intel_wordpress_https_enabled else ''
  rsamb_switch = "--rsamb" if FLAGS.intel_wordpress_rsamb_enabled else ''
  icx_switch = "--icx-opt" if FLAGS.intel_wordpress_icx_enabled else ''
  if FLAGS.intel_wordpress_https_enabled or FLAGS.intel_wordpress_rsamb_enabled or FLAGS.intel_wordpress_icx_enabled:
    tls_switch = "--tls {}".format(FLAGS.intel_wordpress_https_tls_version)
    cipher_switch = "--cipher {}".format(FLAGS.intel_wordpress_https_cipher)
  stdout, _ = server_vms[0].RobustRemoteCommand('cd ' + INSTALL_DIR + '/git/hhvm-perf '
                                                ' && ./run.py {} {} {} {} {}'.format(https_switch, rsamb_switch, icx_switch, tls_switch, cipher_switch))

  logging.info("copying workload output to local run output dir")
  # workload output location is specified on stdout
  workload_output_dir = None
  stdout_io = StringIO(stdout)
  for line in stdout_io:
    sline = line.strip()
    if sline.startswith('Done. Latest results in:'):
      match = re.search(r'Done. Latest results in: (.*)$', line)
      if match is None:
        logging.error("Parsing error -- regex doesn't match for string: %s", line)
      else:
        workload_output_dir = match.group(1)
  # copy workoad output folder from vm to local temp run dir
  tps = 0
  latency = 0
  shortest_transaction = 0
  longest_transaction = 0
  percentiles = {'P50': 0, 'P90': 0, 'P95': 0, 'P99': 0}
  metadata_collected = {}
  metadata_fields = {}
  if workload_output_dir:
    server_vms[0].RemoteCommand('rm -r {}/oss-performance'.format(workload_output_dir))
    local_dir = _GetLocalDir(server_vms[0], os.path.basename(workload_output_dir))
    server_vms[0].RemoteCopy(os.path.join(vm_util.GetTempDir(), local_dir),
                             workload_output_dir, False)
    results_file = os.path.join(local_dir, 'results', target_name, 'run',
                                'Performance-' + target_name + '.json')
    with open(vm_util.PrependTempDir(results_file)) as f:
      json_f = json.loads(f.read())
    software_stack = os.path.join(local_dir, 'results', target_name,
                                  'Software_Stack_' + target_name + '.json')
    with open(vm_util.PrependTempDir(software_stack)) as f:
      metadata_collected = json.loads(f.read())
    if workload_engine == "php":
      metadata_fields['server_threads'] = metadata_collected['PHP Engine']['PHP-FPM Processes']
    elif workload_engine == "hhvm":
      metadata_fields['server_threads'] = metadata_collected['PHP Engine']['Server Threads']
    metadata_fields['execution_count'] = count
    metadata_fields['mariadb_config'] = _RetrieveMariaDBConfig(server_vms[0])
    metadata_fields['hhvm_perf'] = _GetHhvmPerfVersion(server_vms[0])
    metadata_fields['webtier_provisioning'] = _GetWebtierProvisioningVersion(server_vms[0])
    metadata_fields['oss_performance_version'] = _GetOssPerformanceVersion(server_vms[0])
    metadata_fields['wordpress_version'] = metadata_collected['OSS-Performance']['Workload Version']
    metadata_fields['php_version'] = metadata_collected['PHP Engine']['Version']
    metadata_fields['client_threads'] = metadata_collected['OSS-Performance']['Client Threads']
    metadata_fields['mariadb_version'] = metadata_collected['MySQL Server']['Version']
    metadata_fields['nginx_workers'] = metadata_collected['NginxInfo']['Workers']
    metadata_fields['nginx_version'] = metadata_collected['NginxInfo']['Version']
    metadata_fields['https'] = FLAGS.intel_wordpress_https_enabled

    if FLAGS.intel_wordpress_https_enabled or FLAGS.intel_wordpress_rsamb_enabled or FLAGS.intel_wordpress_icx_enabled:
      metadata_fields['tls_version'] = metadata_collected['SSL Enable']['TLS-version']
      metadata_fields['openssl_version'] = _GetOpensslVersion(server_vms[0])
      metadata_fields['cipher'] = metadata_collected['SSL Enable']['Cipher']
      metadata_fields['Optimizations'] = metadata_collected['SSL Enable']['Optimizations']
    tps_entry = json_f['oss-performance results']['Transaction Rate (in trans/sec)']
    tps = tps_entry['Average']
    if tps_entry['RSD']:
      metadata_fields['relative_std_dev'] = str(round(tps_entry['RSD'] * 100, 2)) + '%'
    latency = json_f['oss-performance results']['Response time (in sec)']['Average']
    shortest_transaction = json_f['oss-performance results']['Shortest Transaction (in sec)']['Average']
    longest_transaction = json_f['oss-performance results']['Longest Transaction (in sec)']['Average']
    for p in sorted(percentiles.keys()):
      percentiles[p] = json_f['oss-performance results'][p + ' (in sec)']['Average']

  samples.append(sample.Sample("transaction rate", tps, "transactions/second", metadata_fields))
  samples.append(sample.Sample("average request latency", latency, "seconds", metadata_fields))
  for p in sorted(percentiles.keys()):
    samples.append(sample.Sample(p, percentiles[p], "seconds", metadata_fields))
  samples.append(sample.Sample("longest transaction duration", longest_transaction,
                               "miliseconds", metadata_fields))
  samples.append(sample.Sample("shortest transaction duration", shortest_transaction,
                               "miliseconds", metadata_fields))
  return samples


def _GetLocalDir(vm, target_dir):
  full_dir_path = os.path.join(vm_util.GetTempDir(), target_dir)
  if os.path.exists(full_dir_path):
    idx = 1
    while os.path.exists("{0}-{1}".format(full_dir_path, str(idx))):
      idx += 1
    return "{0}-{1}".format(target_dir, str(idx))
  else:
    return target_dir


def _RetrieveMariaDBConfig(vm):
  mariadb_remote_vars = os.path.join(INSTALL_DIR, 'webtier-provisioning', 'webtier',
                                     'roles', 'mariadb', 'vars', 'main.yml')
  mariadb_local_vars = os.path.join(vm_util.GetTempDir(), "mariadb_vars.yml")
  vm.RemoteCopy(mariadb_local_vars, mariadb_remote_vars, False)
  with open(mariadb_local_vars) as stream:
    config = yaml.load(stream)
  return config['my_cnf']


def _GetHhvmPerfVersion(vm):
  hhvm_perf_version_file = os.path.join(INSTALL_DIR, 'git', 'hhvm-perf', 'version_tag')
  out, _, retcode = vm.RemoteHostCommandWithReturnCode('cat ' + hhvm_perf_version_file,
                                                       ignore_failure=True)
  if retcode == 0:
    return out.strip()
  else:
    return "Error determining hhvm-perf version"


def _GetOpensslVersion(vm):
  out, _, retcode = vm.RemoteHostCommandWithReturnCode('openssl version')
  if retcode == 0:
    return out.strip()
  else:
    return "Error determining openssl version"


def _GetWebtierProvisioningVersion(vm):
  webtier_prov_version_file = os.path.join(INSTALL_DIR, 'webtier-provisioning', 'version_tag')
  out, _, retcode = vm.RemoteHostCommandWithReturnCode('cat ' + webtier_prov_version_file,
                                                       ignore_failure=True)
  if retcode == 0:
    return out.strip()
  else:
    return "Error determining hhvm_provisioning version"


def _GetOssPerformanceVersion(vm):
  oss_perf_version_file = os.path.join(INSTALL_DIR, 'git', 'oss-performance', 'version_tag')
  out, _, retcode = vm.RemoteHostCommandWithReturnCode('cat ' + oss_perf_version_file,
                                                       ignore_failure=True)
  if retcode == 0:
    return out.strip()
  else:
    return "Error determining oss-performance version"


def _CleanupClient(vm):
  """Restore the ssh files to their original state"""
  vm.RemoteHostCommand('mv ~/.ssh/authorized_keys.original ~/.ssh/authorized_keys')
  vm.RemoteHostCommand('sudo mv /etc/hosts.original /etc/hosts')


def _CleanupServer(vm):
  """Restore the /etc/hosts and ssh files to their original state"""

  cmds = ['sudo mv /etc/hosts.original /etc/hosts',
          'sudo mv /etc/ssh/ssh_config.original /etc/ssh/ssh_config']
  vm.RemoteHostCommand(' && '.join(cmds))


def Cleanup(benchmark_spec):
  """Cleans up the client/server nodes"""
  vm_dict = benchmark_spec.vm_groups
  server_vms = vm_dict[SERVER_GROUP]
  client_vms = vm_dict[CLIENT_GROUP]

  _CleanupServer(server_vms[0])
  _CleanupClient(client_vms[0])
