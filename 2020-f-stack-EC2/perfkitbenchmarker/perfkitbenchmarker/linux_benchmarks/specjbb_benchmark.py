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

import logging
import re
import posixpath
import datetime
import time
import multiprocessing

from perfkitbenchmarker import configs
from perfkitbenchmarker import data
from absl import flags
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import trace_util
from perfkitbenchmarker import sample
from perfkitbenchmarker import events

SPECJBB_DEFAULT_T1_MULT = 7
SPECJBB_DEFAULT_T2_MULT = 0.25
SPECJBB_DEFAULT_T3_MULT = 1.20

SPECJBB_RUNTYPES = ['HBIR_RT', 'HBIR_RT_LOADLEVELS', 'PRESET']
FLAGS = flags.FLAGS
flags.DEFINE_enum('specjbb_runtype', 'HBIR_RT', SPECJBB_RUNTYPES,
                  'specjbb run-type like HBIR_RT, LOADLEVEL, PRESET')
flags.DEFINE_string('specjbb_kitversion', 'jbb103', 'SPECjbb kit version. This must be available in '
                                                    'SPECjbb repo in order to be used.')
flags.DEFINE_integer('specjbb_groups', None, 'Number of SPECjbb groups to create. Defaults to number of NUMA nodes '
                                             'if not specified.')
flags.DEFINE_integer('specjbb_gc_threads', None, 'SPECjbb garbage collector threads per group. Defaults to (total '
                                                 'vCPUs / number of groups) if not specified.')
flags.DEFINE_integer('specjbb_tier_1_threads', None, 'Number of tier 1 threads per group. Defaults to '
                                                     '({} * # cores / specjbb_groups) if not '
                                                     'specified.'.format(SPECJBB_DEFAULT_T1_MULT))
flags.DEFINE_integer('specjbb_tier_2_threads', None, 'Number of tier 2 threads per group. Defaults to '
                                                     '({} * # cores / specjbb_groups) if not '
                                                     'specified.'.format(SPECJBB_DEFAULT_T2_MULT))
flags.DEFINE_integer('specjbb_tier_3_threads', None, 'Number of tier 3 threads per group. Defaults to '
                                                     '({} * # cores / specjbb_groups) if not '
                                                     'specified.'.format(SPECJBB_DEFAULT_T3_MULT))
flags.DEFINE_string('specjbb_xmx', None, 'Max Heap size per backend JVM. Defaults to '
                                         '(1 * (cores / specjbb_groups))g for max-jop tuning if not specified. '
                                         'Defaults to (total memory - (7 + 2 * specjbb_groups)) / specjbb_groups '
                                         'for critical-jop tuning. Note that the memory unit is required.')
flags.DEFINE_string('specjbb_xms', None, 'Min Heap size per backend JVM. Defaults to '
                                         '(1 * (cores / specjbb_groups))g for max-jop tuning if not specified. '
                                         'Defaults to (total memory - (7 + 2 * specjbb_groups)) / specjbb_groups '
                                         'for critical-jop tuning. Note that the memory unit is required.')
flags.DEFINE_string('specjbb_xmn', None, 'Nursery size per backend JVM. Defaults to '
                                         '(1 * (cores / specjbb_groups) - 2)g for max-jop tuning if not specified. '
                                         'Defaults to ((total memory - (7 + 2 * specjbb_groups)) / specjbb_groups) - 3 '
                                         'for critical-jop tuning. Note that the memory unit is required.')
flags.DEFINE_float('specjbb_loadlevel_start', 0.95, 'Controls the % of max RT when the load level stage should start. '
                                                    'This is particularly helpful with telemetry analysis as different '
                                                    'values have to be used to capture critical jOPS / max jOPS '
                                                    'thresholds. Use 0.5-0.55 for critical and 0.95 for max.',
                   lower_bound=0.0, upper_bound=1.0)
flags.DEFINE_integer('specjbb_loadlevel_step', 1, 'Controls the % step of load level stage.')
flags.DEFINE_integer('specjbb_rtstart', 0, 'rt start point percentage')
flags.DEFINE_integer('specjbb_preset_ir', 1000, 'specjbb preset Injection Rate when specjbb_runtype=PRESET.')
flags.DEFINE_integer('specjbb_duration', 600, 'specjbb duration for PRESET and LOADLEVEL')
flags.DEFINE_string('specjbb_url', 'https://gitlab.devtools.intel.com/mljones2/SPECjbb2015/-/archive/master/SPECjbb2015-master.tar.gz',
                    'The url where the specjbb workload exists')
flags.DEFINE_string('specjbb_java_parameters', '', 'string of any extra Java parameters that '
                                                   'need to be passed to Backend JVM')
flags.DEFINE_integer('specjbb_mapreducer_pool_size', None, 'Map reducer pool size. Defaults to (total '
                                                           'vCPUs / number of groups) if not specified.')
flags.DEFINE_integer('specjbb_selector_runner_count', None, 'Selector runner count. Defaults to number of groups '
                                                            'if not specifiec')
flags.DEFINE_integer('specjbb_client_pool_size', 210, 'Client pool size.')
flags.DEFINE_integer('specjbb_customer_driver_threads', 64, 'Customer Driver Threads.')
flags.DEFINE_integer('specjbb_customer_driver_threads_probe', 64, 'Customer Driver Threads Probe.')
flags.DEFINE_integer('specjbb_customer_driver_threads_saturate', 64, 'CUstomer Driver Threads Saturate.')
flags.DEFINE_integer('specjbb_worker_pool_min', 1, 'Worker pool min.')
flags.DEFINE_integer('specjbb_worker_pool_max', 90, 'Worker pool max.')
flags.DEFINE_boolean('specjbb_use_avx', True, 'If enabled, uses latest available AVX version.')
flags.DEFINE_boolean('specjbb_use_large_pages', True, 'If enabled, large pages are used.')
flags.DEFINE_integer('specjbb_large_page_size_mb', 2, 'Large page size in megabytes, when used.')


BENCHMARK_NAME = 'specjbb'
BENCHMARK_VERSION = "1.0.1-2015"
BENCHMARK_CONFIG = """
specjbb:
  description: >
      Run specjbb for benchmark
  vm_groups:
    target:
      os_type: ubuntu1604
      vm_spec: *default_dual_core
"""
VM_GROUP = 'target'

# Per recipe, this is a constant: 1
SPECJBB_MEMORY_PER_CORE = 1

# Per recipe, this is a constant, but may need to be flexible
TI_JVM_COUNT = 1

WORK_DIR = '/opt/pkb'
SPECJBB_WORK_DIR = posixpath.join(WORK_DIR, 'SPECjbb2015')
SPECJBB_LOG_DIR = posixpath.join(SPECJBB_WORK_DIR, 'specjbb_logs')
JVM_OPTS_TI_TEMPLATE = "-server -Xms2g -Xmx2g -Xmn1536m {gc_version} -XX:ParallelGCThreads=2"
JVM_OPTS_CT_TEMPLATE = "-server -Xms2g -Xmx2g -Xmn1536m {gc_version} -XX:ParallelGCThreads=2"
JVM_OPTS_BE_TEMPLATE = "-Xms{xms} -Xmx{xmx} -Xmn{xmn} {gc_version} -XX:ParallelGCThreads={gc_threads} " \
                       "-showversion -XX:+AlwaysPreTouch -XX:-UseAdaptiveSizePolicy " \
                       "-XX:SurvivorRatio=28 -XX:MaxTenuringThreshold=15 -XX:InlineSmallCode=10k -verbose:gc " \
                       "-XX:-UseCountedLoopSafepoints -XX:LoopUnrollLimit=20 -XX:MaxGCPauseMillis=500 " \
                       "-XX:AdaptiveSizeMajorGCDecayTimeScale=12 -XX:AdaptiveSizeDecrementScaleFactor=2 " \
                       "-server -XX:TargetSurvivorRatio=95 -XX:AllocatePrefetchLines=3 " \
                       "-XX:AllocateInstancePrefetchLines=2 -XX:AllocatePrefetchStepSize=128 " \
                       "-XX:AllocatePrefetchDistance=384 -XX:-PrintGCDetails {java_args}"


def GetConfig(user_config):
  return configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)


def Prepare(benchmark_spec):
  """Prepare the virtual machines to run.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  benchmark_spec.always_call_cleanup = True
  benchmark_spec.control_traces = True
  benchmark_spec.workload_name = "SPECjbb 2015"
  benchmark_spec.sut_vm_group = 'target'

  vm = benchmark_spec.vm_groups[VM_GROUP][0]
  vm.InstallPackages('numactl curl fontconfig')
  if FLAGS['openjdk_version'].present:
    if FLAGS.openjdk_version <= 8:
      raise Exception("Openjdk package version {} is too low for SPECjbb. "
                      "Expecting version > 8.".format(FLAGS.openjdk_version))
  else:
    logging.info("Overriding default Openjdk version to 11. Use --openjdk_version to set version.")
    FLAGS.openjdk_version = 11
  vm.Install('openjdk')
  logging.info("configuring the environment for specjbb")
  logging.info("get specjbb repo locally")
  specjbb_path = vm_util.PrependTempDir('specjbb.tar.gz')
  url = FLAGS.specjbb_url
  cmd_download = ['curl', '-SL', '--noproxy', 'gitlab.devtools.intel.com', url, '-o', specjbb_path]
  vm_util.IssueCommand(cmd_download)
  logging.info("copying tarball to VM")
  vm.RemoteCopy(specjbb_path, WORK_DIR)
  vm_util.IssueCommand(['rm', specjbb_path])
  logging.info("extracting tar")
  vm.RemoteHostCommand('cd {} && tar -xvzf specjbb.tar.gz'.format(WORK_DIR))
  vm.RemoteHostCommand('cd {} && mv -f SPECjbb2015-master SPECjbb2015'.format(WORK_DIR))
  vm.RemoteHostCommand('chmod +x {}/SPECjbb*/*.sh'.format(WORK_DIR))
  vm.RemoteHostCommand('chmod +x {}/SPECjbb*/*/*.sh'.format(WORK_DIR))
  vm.RemoteHostCommand('mkdir -p {}'.format(SPECJBB_LOG_DIR))
  vm.RemoteHostCommand('sudo sh -c \"echo always > /sys/kernel/mm/transparent_hugepage/enabled \"')
  vm.RemoteHostCommand(r'sudo sh -c "echo \* soft nofile 65536 >> /etc/security/limits.conf "')
  vm.RemoteHostCommand(r'sudo sh -c "echo \* hard nofile 65536 >> /etc/security/limits.conf "')


def Run(benchmark_spec):
  """
  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  Returns:
    A list of sample.Sample objects.
  """
  vm = benchmark_spec.vm_groups[VM_GROUP][0]
  _GenerateMetadataFromFlags(benchmark_spec)
  tuning_params = benchmark_spec.tunable_parameters_metadata
  sw_params = benchmark_spec.software_config_metadata

  jdk_version, _ = vm.RemoteHostCommand('java -version 2>&1  | sed -E -n \'s/.* version "([^.-]*).*"/\\1/p\' '
                                        '| cut -d\' \' -f1')
  if int(jdk_version) >= 14:
    gc_arg = '-XX:+UseParallelGC'
  else:
    gc_arg = '-XX:+UseParallelOldGC'

  benchmark_spec.software_config_metadata['gc'] = gc_arg

  jvm_ops_be = JVM_OPTS_BE_TEMPLATE.format(gc_version=gc_arg,
                                           gc_threads=tuning_params['specjbb_gc_threads'],
                                           xms=tuning_params['specjbb_xms'],
                                           xmx=tuning_params['specjbb_xmx'],
                                           xmn=tuning_params['specjbb_xmn'],
                                           java_args=sw_params['specjbb_java_parameters'])
  jvm_ops_ctl = JVM_OPTS_CT_TEMPLATE.format(gc_version=gc_arg)
  jvm_ops_ti = JVM_OPTS_TI_TEMPLATE.format(gc_version=gc_arg)

  if not FLAGS.specjbb_use_avx:
      avx_suffix = " -XX:UseAVX=0"
      jvm_ops_be = jvm_ops_be + avx_suffix
      jvm_ops_ctl = jvm_ops_ctl + avx_suffix
      jvm_ops_ti = jvm_ops_ti + avx_suffix

  if FLAGS.specjbb_use_large_pages:
      large_page_suffix = " -XX:+UseLargePages -XX:LargePageSizeInBytes={}m".format(FLAGS.specjbb_large_page_size_mb)
      jvm_ops_be = jvm_ops_be + large_page_suffix
      jvm_ops_ctl = jvm_ops_ctl + large_page_suffix
      jvm_ops_ti = jvm_ops_ti + large_page_suffix

  sw_params['specjbb_backend_cmd'] = jvm_ops_be
  sw_params['specjbb_controller_cmd'] = jvm_ops_ctl
  sw_params['specjbb_injector_cmd'] = jvm_ops_ti


  _ConfigureFiles(vm, tuning_params, sw_params)

  for group in range(tuning_params['specjbb_groups']):
    group_id = 'Group{}'.format(group)
    ulimit = 'ulimit -n 65536'
    numactl = 'numactl --cpunodebind={} --localalloc'.format(group % vm.CheckLsCpu().numa_node_count)
    cmd_template = 'bash -c \'cd {jbb_dir}; {ulimit}; nohup {numactl} java {jvm_opts} ' \
                   '-Xlog:gc*:file={log_dir}/{jvm_name}.GC.log -jar specjbb2015.jar ' \
                   '-m {jvm_type} -G={group_id} -J={jvm_id} > {log_dir}/{log} 2>&1 &\''
    # Start Injector JVMs
    for jvm_num in range(TI_JVM_COUNT):
      jvm_id = 'JVM{}'.format(jvm_num)
      jvm_name = '{}.TxInjector.{}'.format(group_id, jvm_num)
      log = '{}.log'.format(jvm_name)
      jvm_type = 'TXINJECTOR'
      ti_cmd = cmd_template.format(jbb_dir=posixpath.join(SPECJBB_WORK_DIR, sw_params['specjbb_kitversion']),
                                   ulimit=ulimit, numactl=numactl, jvm_opts=jvm_ops_ti, jvm_name=jvm_name,
                                   jvm_type=jvm_type, group_id=group_id, jvm_id=jvm_id, log=log, log_dir=SPECJBB_LOG_DIR)
      vm.RemoteHostCommand(ti_cmd)
    # Start backend JVM
    # If recipe calls for multiple backends per group, we may need to change this logic
    # Backend index starts at TI_JVM_COUNT since we start 0
    jvm_id = 'JVM{}'.format(TI_JVM_COUNT)
    jvm_name = '{}.Backend.{}'.format(group_id, TI_JVM_COUNT)
    log = '{}.log'.format(jvm_name)
    jvm_type = 'BACKEND'
    be_cmd = cmd_template.format(jbb_dir=posixpath.join(SPECJBB_WORK_DIR, sw_params['specjbb_kitversion']),
                                 ulimit=ulimit, numactl=numactl, jvm_opts=jvm_ops_be, jvm_name=jvm_name,
                                 jvm_type=jvm_type, group_id=group_id, jvm_id=jvm_id, log=log, log_dir=SPECJBB_LOG_DIR)
    vm.RemoteHostCommand(be_cmd)
  logging.info("Allowing 20 seconds for JVMs to start.")
  time.sleep(20)
  _CheckJvmProcesses(vm, {'BACKEND': tuning_params['specjbb_groups'],
                     'TXINJECTOR': tuning_params['specjbb_groups'] * TI_JVM_COUNT})
  _StartController(vm, sw_params, benchmark_spec)
  samples = _GetResults(vm)
  return samples


def Cleanup(benchmark_spec):
  """Cleanup.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  vm = benchmark_spec.vm_groups['target'][0]
  vm.RemoteHostCommand('sudo rm -rf {}'.format(WORK_DIR), ignore_failure=True)


def _GenerateMetadataFromFlags(benchmark_spec):
  sw_params = benchmark_spec.software_config_metadata
  tuning_params = benchmark_spec.tunable_parameters_metadata
  vm = benchmark_spec.vm_groups[VM_GROUP][0]
  sw_params["benchmark_version"] = BENCHMARK_VERSION
  sw_params["specjbb_url"] = FLAGS.specjbb_url
  if FLAGS.openjdk_url:
    sw_params["specjbb_openjdk_url"] = FLAGS.openjdk_url
  else:
    sw_params["specjbb_openjdk_version"] = FLAGS.openjdk_version
  sw_params["specjbb_java_parameters"] = FLAGS.specjbb_java_parameters
  sw_params["specjbb_kitversion"] = FLAGS.specjbb_kitversion
  sw_params["specjbb_runtype"] = FLAGS.specjbb_runtype
  tuning_params["specjbb_groups"] = FLAGS.specjbb_groups or vm.CheckLsCpu().numa_node_count
  cpus_per_group = int(vm.num_cpus / tuning_params["specjbb_groups"])
  tuning_params["specjbb_gc_threads"] = FLAGS.specjbb_gc_threads or cpus_per_group
  tuning_params['specjbb_tier_1_threads'] = FLAGS.specjbb_tier_1_threads or int(SPECJBB_DEFAULT_T1_MULT * cpus_per_group)
  tuning_params['specjbb_tier_2_threads'] = FLAGS.specjbb_tier_2_threads or int(SPECJBB_DEFAULT_T2_MULT * cpus_per_group)
  tuning_params["specjbb_tier_3_threads"] = FLAGS.specjbb_tier_3_threads or int(SPECJBB_DEFAULT_T3_MULT * cpus_per_group)
  tuning_params["specjbb_rtstart"] = FLAGS.specjbb_rtstart
  tuning_params["specjbb_preset_ir"] = FLAGS.specjbb_preset_ir
  tuning_params["specjbb_loadlevel_start"] = FLAGS.specjbb_loadlevel_start
  tuning_params["specjbb_loadlevel_step"] = FLAGS.specjbb_loadlevel_step
  tuning_params["specjbb_duration"] = FLAGS.specjbb_duration
  tuning_params["specjbb_customer_driver_threads"] = FLAGS.specjbb_customer_driver_threads
  tuning_params['specjbb_customer_driver_threads_probe'] = FLAGS.specjbb_customer_driver_threads_probe
  tuning_params["specjbb_customer_driver_threads_saturate"] = FLAGS.specjbb_customer_driver_threads_saturate
  tuning_params["specjbb_worker_pool_min"] = FLAGS.specjbb_worker_pool_min
  tuning_params["specjbb_worker_pool_max"] = FLAGS.specjbb_worker_pool_max
  tuning_params["specjbb_mapreducer_pool_size"] = FLAGS.specjbb_mapreducer_pool_size or cpus_per_group
  tuning_params["specjbb_selector_runner_count"] = FLAGS.specjbb_selector_runner_count or tuning_params["specjbb_groups"]
  tuning_params["specjbb_client_pool_size"] = FLAGS.specjbb_client_pool_size
  _TuneMax(cpus_per_group, tuning_params)


def _ConfigureFiles(vm, tuning_params, sw_params):
  """
  Replaces variables in configuration file templates with corresponding values.

  Args:
    vm: VM object for SUT.
    metadata: Metadata dictionary containing dynamically updated configuration.
  """

  # If the SPEC information feature is to be relied upon, this will need several more updates.
  info_template = data.ResourcePath(posixpath.join("specjbb/template-M.raw.j2"))
  info_context = {
      'jvm': 'jvm',
      'group_count': tuning_params['specjbb_groups'],
      'tx_cmdline': sw_params['specjbb_injector_cmd'],
      'backend_cmdline': sw_params['specjbb_backend_cmd'],
      'controller_cmdline': sw_params['specjbb_controller_cmd'],
      'date': str(datetime.datetime.now()),
      'kernel': vm.kernel_release,
      'os': vm.os_info,
      'cpu': vm.CheckLsCpu().data['Model name'] if 'Model name' in vm.CheckLsCpu().data else '',
      'chips': vm.CheckLsCpu().socket_count,
      'cores': '',
      'threads': vm.num_cpus,
      'memory': vm.total_memory_kb / 1024 ** 2,
  }
  info_outfile = posixpath.join(SPECJBB_WORK_DIR, sw_params['specjbb_kitversion'], 'config', 'template-M.raw')
  vm.RenderTemplate(info_template, info_outfile, context=info_context)

  properties_template = data.ResourcePath(posixpath.join('specjbb', 'specjbb2015.props.j2'))
  properties_context = {
      'specjbb_run_type': sw_params['specjbb_runtype'],
      'specjbb_rt_curve_start': float(tuning_params['specjbb_rtstart'] / 100),
      'specjbb_tier_1_threads': tuning_params['specjbb_tier_1_threads'],
      'specjbb_tier_2_threads': tuning_params['specjbb_tier_2_threads'],
      'specjbb_tier_3_threads': tuning_params['specjbb_tier_3_threads'],
      'specjbb_group_count': tuning_params['specjbb_groups'],
      'specjbb_client_pool_size': tuning_params['specjbb_client_pool_size'],
      'specjbb_selector_runner_count': tuning_params['specjbb_selector_runner_count'],
      'specjbb_mapreducer_pool_size': tuning_params['specjbb_mapreducer_pool_size'],
      'specjbb_customer_driver_threads': tuning_params['specjbb_customer_driver_threads'],
      'specjbb_customer_driver_threads_probe': tuning_params['specjbb_customer_driver_threads_probe'],
      'specjbb_customer_driver_threads_saturate': tuning_params['specjbb_customer_driver_threads_saturate'],
      'specjbb_worker_pool_min': tuning_params['specjbb_worker_pool_min'],
      'specjbb_worker_pool_max': tuning_params['specjbb_worker_pool_max'],
      'specjbb_duration': tuning_params['specjbb_duration'] * 1000,
      'specjbb_preset_ir': tuning_params['specjbb_preset_ir'],
      'specjbb_loadlevel_start': tuning_params['specjbb_loadlevel_start'],
      'specjbb_loadlevel_step': tuning_params['specjbb_loadlevel_step']
  }
  properties_outfile = posixpath.join(SPECJBB_WORK_DIR, sw_params['specjbb_kitversion'], 'config', 'specjbb2015.props')
  vm.RenderTemplate(properties_template, properties_outfile, context=properties_context)


def _TuneMax(cpus_per_group, metadata):
  baseline_memory = _GetMemoryCorrectionForCompressedOops(cpus_per_group * SPECJBB_MEMORY_PER_CORE)
  metadata["specjbb_xmx"] = FLAGS.specjbb_xmx or '{}g'.format(baseline_memory)
  metadata["specjbb_xms"] = FLAGS.specjbb_xms or '{}g'.format(baseline_memory)
  calculated_xmn = baseline_memory - 2
  metadata["specjbb_xmn"] = FLAGS.specjbb_xmn or '{}g'.format(calculated_xmn if calculated_xmn >= 1 else 1)


def _TuneCritical(benchmark_spec, metadata):
  vm = benchmark_spec.vm_groups[VM_GROUP][0]
  total_memory = int(vm.total_memory_kb / 1024 / 1024)
  max_heap_per_group = int(_GetMemoryCorrectionForCompressedOops(
      (total_memory - (7 + (2 * metadata["specjbb_groups"]))) / metadata["specjbb_groups"]))
  if max_heap_per_group < 2:
    max_heap_per_group = 2
  if FLAGS.specjbb_xmx:
    metadata["specjbb_xmx"] = FLAGS.specjbb_xmx
  else:
    metadata["specjbb_xmx"] = '{}g'.format(max_heap_per_group) if max_heap_per_group >= 2 else '2g'
  if FLAGS.specjbb_xmn:
    metadata["specjbb_xmn"] = FLAGS.specjbb_xmn
  else:
    nursery_per_group = max_heap_per_group - 3
    metadata["specjbb_xmn"] = '{}g'.format(nursery_per_group) if nursery_per_group >= 1 else '1g'
  metadata["specjbb_xms"] = FLAGS.specjbb_xms or metadata["specjbb_xmx"]


def _GetMemoryCorrectionForCompressedOops(memory_gb):
  """
  Adjusts memory sizes between 32GB and 48GB as these are problematic due to Java Compressed OOPS.
  Args:
   memory_gb: Memory as calculated
  Return:
     Adjusted memory
  """
  if 32 <= memory_gb < 48:
    return 31
  else:
    return memory_gb


def _StartController(vm, metadata, benchmark_spec):
  log = 'controller.log'
  out = 'controller.out'
  stdout = ''
  start_phrase = None
  trace_controller = None
  duration = FLAGS.specjbb_duration
  if metadata['specjbb_runtype'] == 'PRESET':
    start_phrase = 'Ramping up completed'
  elif metadata['specjbb_runtype'] == 'HBIR_RT_LOADLEVELS':
    start_phrase = 'Performing load levels'
  try:
    if start_phrase and FLAGS.trace_allow_benchmark_control:
      trace_controller = multiprocessing.Process(target=trace_util.ControlTracesByLogfileProcess,
                                                 args=(vm, benchmark_spec,
                                                       posixpath.join(SPECJBB_LOG_DIR, out),
                                                       start_phrase),
                                                 kwargs={'duration': duration})
      trace_controller.start()
    cmd = 'cd {jbb_dir}; java {jvm_ctlr_args} -Xlog:gc*:file={logdir}/Ctrlr.GC.log ' \
          '-jar specjbb2015.jar -m MULTICONTROLLER 2> {logdir}/{err_log} > ' \
          '{logdir}/{out}'.format(jbb_dir=posixpath.join(SPECJBB_WORK_DIR, metadata['specjbb_kitversion']),
                                  jvm_ctlr_args=metadata['specjbb_controller_cmd'], err_log=log, out=out, logdir=SPECJBB_LOG_DIR)
    stdout, _ = vm.RobustRemoteCommand(cmd)
  except Exception:
     pass
  finally:
    if start_phrase and trace_controller:
      # Ensure trace_controller has exited and if not, terminate it and stop traces

      if trace_controller.is_alive():
        logging.info("Waiting up to {} seconds for trace controller to exit.".format(duration))
        trace_controller.join(timeout=duration)
        if trace_controller.is_alive():
          trace_controller.terminate()
          logging.info("Sending stop trace event as trace controller was still "
                       "running after waiting {} seconds".format(duration))
          events.stop_trace.send(events.RUN_PHASE, benchmark_spec=benchmark_spec)
  return stdout


def _CheckJvmProcesses(vm, jvm_types):
  pids = []
  missing_jvms = 0
  for jvm_type, count in jvm_types.items():
    stdout, _ = vm.RemoteHostCommand("ps -e -o pid,cmd | grep [j]ava |"
                                     " grep {0} | awk '{{print $1}}'".format(jvm_type))
    pids_found = []
    if stdout.strip():
      pids_found = stdout.strip().split('\n')
      pids.extend(pids_found)
    if len(pids_found) != count:
      logging.error("Expected {0} JVM(s) of type {1}, found {2} running.".format(count, jvm_type, len(pids_found)))
      missing_jvms = 1
  if missing_jvms:
    logging.info("Removing remaining processes and copying logs.")
    if pids:
      vm.RemoteHostCommand('kill -9 {}'.format(' '.join(pids)))
    vm.RemoteCopy(vm_util.GetTempDir(), SPECJBB_LOG_DIR, False)
    raise Exception("Unable to start all JVMS. Check corresponding JVM logs for failures.")


def _GetResults(vm):
  samples = []
  logging.info("Copying logs.")
  vm.RemoteCopy(vm_util.GetTempDir(), SPECJBB_LOG_DIR, False)
  logging.info("Copying SPEC results dir.")
  vm.RemoteCopy(vm_util.GetTempDir(),
                posixpath.join(SPECJBB_WORK_DIR, FLAGS.specjbb_kitversion, 'result'), False)
  controller_out = posixpath.join(vm_util.GetTempDir(), 'specjbb_logs', 'controller.out')
  logging.info("Parsing results from {}.".format(controller_out))
  with open(controller_out) as f:
    # Example:
    # RUN RESULT: hbIR (max attempted) = 24482, hbIR (settled) = 23715, max-jOPS = 21299, critical-jOPS = 4659
    regex = R'^RUN RESULT:.*max-jOPS = (.+),.*critical-jOPS = (.+)$'
    results_found = False
    line = f.readline()
    while line:
      match = re.search(regex, line)
      if match:
        results_found = True
        max_jops = match.group(1)
        critical_jops = match.group(2)
        try:
          samples.append(sample.Sample("max-jOPS", float(max_jops), "operations/sec", {'primary_sample': True}))
          samples.append(sample.Sample("critical-jOPS", float(critical_jops), "operations/sec", {}))
        except ValueError as e:
          logging.warning("Metric could not be reported: {}".format(e))
        break
      line = f.readline()
    if not results_found:
      raise Exception("Unable to find Results in output. Check controller logs for failures.")
  return samples
