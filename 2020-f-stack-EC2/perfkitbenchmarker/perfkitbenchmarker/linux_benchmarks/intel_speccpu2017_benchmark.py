# Copyright 2018 PerfKitBenchmarker Authors. All rights reserved.
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

"""Runs SPEC CPU2017.

From the SPEC CPU2017 documentation:
The SPEC CPU 2017 benchmark package contains SPEC's next-generation,
industry-standardized, CPU intensive suites for measuring and comparing
compute intensive performance, stressing a system's processor,
memory subsystem and compiler.

SPEC CPU2017 homepage: http://www.spec.org/cpu2017/
"""
import logging
import re
import os
import posixpath
from perfkitbenchmarker import configs
from perfkitbenchmarker import errors
from absl import flags
from perfkitbenchmarker import data
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import sample
from perfkitbenchmarker.linux_packages import intel_speccpu as speccpu

# Available packages
ICC19 = ('FOR-INTEL-cpu2017-1.1.5-ic2021.1-lin-binaries-20201113_revA.tar.xz,'
         'e272aa71d38d8629cbe6fd11830fd26acccf27a0f2bf43e10be4493dc79f3808,'
         'ic2021.1-lin-core-avx512-rate-20201113_revA.cfg,'
         '--nobuild --define default-platform-flags --define smt-on --define '
         'invoke_with_interleave --define drop_caches')
GCC91 = ('FOR-INTEL-cpu2017-1.1.0-aarch64-gcc9.1.0-binaries-20181218.tar.xz,'
         'b72cc571e99186010a58230d499e1428a4377ef1fbd018f63ae1c96d80079215,'
         'gcc9.1_cross-a76-baseline-rate-20191218.cfg,'
         '--nobuild --define drop_caches')
AOCC20 = ('FOR-Intel-Internal_only-cpu2017-aocc2.0-lin-baserateonly-binaries-20191115.tar.xz,'
          'ad9d211de94d5393a19d3e66785b3924b8268fce6482c2539b88ef10fd2e21ab,'
          'aocc2.0-rome-rate-20191115.cfg,'
          '--noreportable')
GCC82 = ('FOR-INTEL-cpu2017-1.0.5-gcc8.2.0-lin-O2-binaries-20181022.tar.xz,'
         '37f9ef0691f426e4389c531f4e609d7183e916447be491d501bbda9232b626c4,'
         'gcc8.2.0-lin-O2-rate-20181022.cfg,'
         '--define default-platform-flags --define smt-on --define drop_caches')
TP = '0,base,3,'
SC = '1,base,3,'
# Runmode values - SIR=intrate, SFP=fprate, TP=throughput, SC=single copy.
# [0]workload, [1]copies, [2]tuning, [3]iterations, [4]tarball, [5]tarball sha26, [6]config file, [7]custom options
INTEL_SPECCPU2017_RUNMODES = {
    'SIR_TP_ICC19': 'intrate,' + TP + ICC19,
    'SIR_SC_ICC19': 'intrate,' + SC + ICC19,
    'SFP_TP_ICC19': 'fprate,' + TP + ICC19,
    'SFP_SC_ICC19': 'fprate,' + SC + ICC19,
    'SIR_TP_GCC91': 'intrate,' + TP + GCC91,
    'SIR_SC_GCC91': 'intrate,' + SC + GCC91,
    'SFP_TP_GCC91': 'fprate,' + TP + GCC91,
    'SFP_SC_GCC91': 'fprate,' + TP + GCC91,
    'SIR_TP_AOCC20': 'intrate,' + TP + AOCC20,
    'SIR_SC_AOCC20': 'intrate,' + SC + AOCC20,
    'SFP_TP_AOCC20': 'fprate,' + TP + AOCC20,
    'SFP_SC_AOCC20': 'fprate,' + SC + AOCC20,
    'SIR_TP_GCC82': 'intrate,' + TP + GCC82,
    'SIR_SC_GCC82': 'intrate,' + SC + GCC82,
    'SFP_TP_GCC82': 'fprate,' + TP + GCC82,
    'SFP_SC_GCC82': 'fprate,' + SC + GCC82,
    'DEFAULT': 'intrate,1,base,1,' + ICC19,
    'CUSTOM': ''
}
RUNMODES = INTEL_SPECCPU2017_RUNMODES.keys()
FLAGS = flags.FLAGS
flags.DEFINE_enum(
    'intel_spec17_runmode', 'DEFAULT',
    RUNMODES,
    'Run mode to use. SIR=intrate, SFP=fprate, TP=throughput, SC=single copy.'
    'Run intrate single copy using icc 1.9 will be SIR_SC_ICC19 Defaults to '
    'None. ')
flags.DEFINE_string(
    'intel_spec17_iso', 'cpu2017-1.1.0.iso',
    'The speccpu2017 iso file.')
flags.DEFINE_string(
    'intel_spec17_iso_sha256', None,
    'sha256 hash for iso file')
flags.DEFINE_string(
    'intel_spec17_tar', None,
    'Pre-built tar file containing binaries that will be extracted over the top'
    'of a directory of files created by running the spec17 install.sh script   '
    'from the mounted iso.')
flags.DEFINE_string(
    'intel_spec17_tar_sha256', None,
    'sha256 for tar file')
flags.DEFINE_string(
    'intel_spec17_run_script', None,
    'The run script -- either already included in the tar or local. If local, it'
    'will be copied to the target.')
flags.DEFINE_string(
    'intel_spec17_config_file', None,
    'Used by the PKB intel_speccpu2017 benchmark. Name of the cfg file to use as'
    'the SPEC CPU config file provided to the runspec binary via its --config '
    'flag. By default this flag is null to allow usage '
    'of tarball included scripts')
flags.DEFINE_integer(
    'intel_spec17_copies', None,
    'Number of copies to run for rate tests. If not set default to number of cpu cores'
    'using lscpu.')
flags.DEFINE_integer(
    'intel_spec17_threads', None,
    'Number of threads to run for speed tests. If not set '
    'default to number of cpu threads using lscpu.')
flags.DEFINE_string(
    'intel_spec17_benchmark', None,
    'This will pass the workload to be ran, it can be one of the intrate, intspeed,'
    'fprate, fpspeed or all (e.g. --intel_spec17_benchmark="intrate fprate etc.") or'
    'just a single benchmark from the suites for which --noreportable option will '
    'be added to the runcpu command')
flags.DEFINE_enum(
    'intel_spec17_tuning', None,
    ['base', 'peak', 'base,peak'],
    'Selects tuning to use: base, peak, or all. For a reportable run, must be'
    'either base or all. Reportable runs do base first, then (optionally) peak.'
    'Defaults to base. ')
flags.DEFINE_integer(
    'intel_spec17_iterations', None,
    'Used by the PKB speccpu benchmarks. The number of benchmark iterations '
    'to execute, provided to the runspec binary via its --iterations flag.')
flags.DEFINE_string(
    'intel_spec17_runcpu_options', None,
    'This will allow passing command options which are not already defined as'
    'a flag. Check a full list: https://www.spec.org/cpu2017/Docs/runcpu.html'
    ' (e.g. -o all to output reports in all formats or --noreportable')
flags.DEFINE_string(
    'intel_spec17_define', None,
    'Used by the PKB speccpu benchmarks. Optional comma-separated list of '
    'SYMBOL[=VALUE] preprocessor macros provided to the runspec binary via '
    'repeated --define option (e.g. numa,smt,sse=SSE4.2)')
flags.DEFINE_enum(
    'intel_spec17_size', 'ref',
    ['test', 'train', 'ref'],
    'Selects size of input data to run: test, train, or ref. The reference '
    'workload ("ref") is the only size whose time appears in reports.')
flags.DEFINE_string(
    'intel_spec17_action', 'validate',
    'Used by the PKB speccpu benchmarks. If set, will append --action validate'
    'to runcpu command. Check this page for a full list of available options:'
    'https://www.spec.org/cpu2017/Docs/runcpu.html#action')

BENCHMARK_NAME = 'intel_speccpu2017'

BENCHMARK_CONFIG = """
intel_speccpu2017:
  description: Runs SPEC CPU2017
  vm_groups:
    default:
      os_type: ubuntu1804
      vm_spec: *default_single_core
      disk_spec: *default_500_gb
      vm_count: 1
  flags:
    enable_transparent_hugepages: false
"""

BENCHMARK_DATA = {}

KB_TO_GB_MULTIPLIER = 1000000

LOG_FILENAME = [
    'CPU2017.*.fprate.txt',
    'CPU2017.*.fprate.refrate.txt',
    'CPU2017.*.fpspeed.txt',
    'CPU2017.*.fpspeed.refspeed.txt',
    'CPU2017.*.intrate.txt',
    'CPU2017.*.intrate.refrate.txt',
    'CPU2017.*.intspeed.txt',
    'CPU2017.*.intspeed.refspeed.txt',
]


def GetConfig(user_config):
  return configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)


def GenerateMetadataFromFlags(benchmark_spec):
  metadata = {}
  metadata['Spec_cpu_2017_ISO'] = FLAGS.intel_spec17_iso
  metadata['Spec_cpu_2017_ISO_sha256'] = FLAGS.intel_spec17_iso_sha256 or 'n/a'
  metadata['Spec_cpu_2017_binaries_tarball'] = FLAGS.intel_spec17_tar or 'n/a'
  metadata['Spec_cpu_2017_binaries_tarball_sha256'] = FLAGS.intel_spec17_tar_sha256 or 'n/a'
  metadata['Spec_cpu_2017_run_script'] = FLAGS.intel_spec17_run_script or 'n/a'
  metadata['Spec_cpu_2017_config_file'] = FLAGS.intel_spec17_config_file or 'n/a'
  metadata['Spec_cpu_2017_benchmark'] = FLAGS.intel_spec17_benchmark or 'n/a'
  metadata['Spec_cpu_2017_copies'] = FLAGS.intel_spec17_copies or 'n/a'
  metadata['Spec_cpu_2017_threads'] = FLAGS.intel_spec17_threads or 'n/a'
  metadata['Spec_cpu_2017_tuning'] = FLAGS.intel_spec17_tuning or 'n/a'
  metadata['Spec_cpu_2017_iterations'] = FLAGS.intel_spec17_iterations or 'n/a'
  metadata['Spec_cpu_2017_size'] = FLAGS.intel_spec17_size or 'n/a'
  metadata['Spec_cpu_2017_action'] = FLAGS.intel_spec17_action or 'n/a'
  metadata['Spec_cpu_2017_defines'] = FLAGS.intel_spec17_define or 'n/a'
  metadata['Spec_cpu_2017_options'] = FLAGS.intel_spec17_runcpu_options or 'n/a'
  metadata['Spec_cpu_2017_runmode'] = FLAGS.intel_spec17_runmode or 'n/a'
  if FLAGS.intel_spec17_runmode and metadata['Spec_cpu_2017_runmode'] != 'CUSTOM':
      metadata['Spec_cpu_2017_binaries_tarball'] = FLAGS.intel_spec17_tar or INTEL_SPECCPU2017_RUNMODES.get(
          '{}'.format(FLAGS.intel_spec17_runmode)).split(',')[4]
      metadata['Spec_cpu_2017_binaries_tarball_sha256'] = FLAGS.intel_spec17_tar_sha256 or INTEL_SPECCPU2017_RUNMODES.get(
          '{}'.format(FLAGS.intel_spec17_runmode)).split(',')[5]
      metadata['Spec_cpu_2017_config_file'] = FLAGS.intel_spec17_config_file or INTEL_SPECCPU2017_RUNMODES.get(
          '{}'.format(FLAGS.intel_spec17_runmode)).split(',')[6]
      metadata['Spec_cpu_2017_benchmark'] = FLAGS.intel_spec17_benchmark or INTEL_SPECCPU2017_RUNMODES.get(
          '{}'.format(FLAGS.intel_spec17_runmode)).split(',')[0]
      metadata['Spec_cpu_2017_copies'] = FLAGS.intel_spec17_copies or INTEL_SPECCPU2017_RUNMODES.get(
          '{}'.format(FLAGS.intel_spec17_runmode)).split(',')[1]
      metadata['Spec_cpu_2017_tuning'] = FLAGS.intel_spec17_tuning or INTEL_SPECCPU2017_RUNMODES.get(
          '{}'.format(FLAGS.intel_spec17_runmode)).split(',')[2]
      metadata['Spec_cpu_2017_iterations'] = FLAGS.intel_spec17_iterations or INTEL_SPECCPU2017_RUNMODES.get(
          '{}'.format(FLAGS.intel_spec17_runmode)).split(',')[3]
      metadata['Spec_cpu_2017_options'] = FLAGS.intel_spec17_runcpu_options or '{0}'.format(INTEL_SPECCPU2017_RUNMODES.get(
          '{}'.format(FLAGS.intel_spec17_runmode)).split(',')[7])
  if FLAGS.intel_spec17_run_script:
      options = 'Check arguments inside {0} script'.format(FLAGS.intel_spec17_run_script)
      metadata['Spec_cpu_2017_config_file'] = options
      metadata['Spec_cpu_2017_benchmark'] = options
      metadata['Spec_cpu_2017_copies'] = options
      metadata['Spec_cpu_2017_threads'] = options
      metadata['Spec_cpu_2017_tuning'] = options
      metadata['Spec_cpu_2017_iterations'] = options
      metadata['Spec_cpu_2017_size'] = options
      metadata['Spec_cpu_2017_action'] = options
      metadata['Spec_cpu_2017_defines'] = options
      metadata['Spec_cpu_2017_options'] = options
  return metadata


def Prepare(benchmark_spec):
  """Installs SPEC CPU2017 on the target vm.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  vm = benchmark_spec.vms[0]
  metadata = GenerateMetadataFromFlags(benchmark_spec)
  install_config = speccpu.SpecInstallConfigurations()
  install_config.benchmark_name = BENCHMARK_NAME
  install_config.base_spec_dir = 'cpu2017'
  install_config.base_iso_file_path = metadata['Spec_cpu_2017_ISO']
  install_config.base_mount_dir = 'mnt'
  install_config.base_tar_file_path = metadata['Spec_cpu_2017_binaries_tarball']
  BENCHMARK_DATA[FLAGS.intel_spec17_iso] = metadata['Spec_cpu_2017_ISO_sha256']
  BENCHMARK_DATA[FLAGS.intel_spec17_tar] = metadata['Spec_cpu_2017_binaries_tarball_sha256']
  speccpu.Install(vm, install_config)
  # If the run_script is local, upload it to the target. If it fails,
  # assume the script is already on the target.
  try:
    vm.PushFile(data.ResourcePath(FLAGS.intel_spec17_run_script),
                vm.speccpu_vm_state.spec_dir)
  except:
    try:
      vm.PushFile(data.ResourcePath(posixpath.join('intel_speccpu2017', FLAGS.intel_spec17_run_script)),
                  vm.speccpu_vm_state.spec_dir)
    except:
      logging.info("{0} not found locally. Will assume script is already on target."
                   .format(FLAGS.intel_spec17_run_script))


def _DownloadResults(benchmark_spec):
  """ archive and download the result directory """
  vm = benchmark_spec.vms[0]
  spec_dir = vm.speccpu_vm_state.spec_dir
  filename = 'speccpu2017_results.tar.gz'
  archive = '{dir}/{filename}'.format(dir=spec_dir, filename=filename)
  vm.RemoteCommand('cd {dir} && tar -cvzf {archive} result/'
                   .format(dir=spec_dir, archive=archive))
  vm.PullFile(vm_util.GetTempDir(), archive)


def _ExtractScores(log_txt, metadata):
  benchmark_re = re.compile(r'^(\d*\.\w*)\s*(\d*)\s*(\d*)\s*(\d*\.?\d*)\s{,3}\S{,3}\s*(\d*)\s*(\d*)\s*(\d*\.?\d*)\s{1,3}')
  score_re = re.compile(r'^(.*SPEC.*2017_.*)\s{2}(\S*)')
  benchmark_results = {}
  scores = {}
  results = []

  for line in log_txt.splitlines():
    match = re.search(benchmark_re, line)
    if match:
      benchmark_results[str(match.group(1))] = (match.group(2), match.group(3), match.group(4), match.group(5), match.group(6), match.group(7))
      continue
    match = re.search(score_re, line)
    if match:
      scores[str(match.group(1))] = match.group(2)
  # individual benchmark results
  for key, value in benchmark_results.items():
    results.append(sample.Sample(key + '_base_copies', value[0], 'copies', metadata))
    results.append(sample.Sample(key + '_base_run_time', value[1], 'seconds', metadata))
    results.append(sample.Sample(key + '_base_rate', value[2], 'ratio', metadata))
    results.append(sample.Sample(key + '_peak_copies', value[3], 'copies', metadata))
    results.append(sample.Sample(key + '_peak_run_time', value[4], 'seconds', metadata))
    results.append(sample.Sample(key + '_peak_rate', value[5], 'ratio', metadata))
  # scores
  for key, value in scores.items():
    if value == "Not":
      value = '0'
    results.append(sample.Sample(key.strip(), value, 'score', metadata))
  return results


def _ParseResults(vm, log_file_names, metadata):
  results = []
  for log in log_file_names:
    try:
      stdout, _ = vm.RemoteCommand('cat {0}/result/{1}'
                                   .format(vm.speccpu_vm_state.spec_dir, log),
                                   should_log=True)
    except errors.VirtualMachine.RemoteCommandError:
      continue
    results.extend(_ExtractScores(stdout, metadata))
  return results


def Run(benchmark_spec):
  """Runs SPEC CPU2017 on the target vm.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.

  Returns:
    A list of sample.Sample objects.
  """
  vm = benchmark_spec.vms[0]
  metadata = GenerateMetadataFromFlags(benchmark_spec)
  samples = []
  # Specific to P2CA scripts
  workspace = vm.speccpu_vm_state.spec_dir
  topo_txt = posixpath.join(workspace, 'topo.txt')
  numa_detection_script = posixpath.join(workspace, 'numa-detection.sh')
  nhmtopology = posixpath.join(workspace, 'nhmtopology.pl')
  numa_node_count = vm.CheckLsCpu().numa_node_count
  cores = vm.CheckLsCpu().data["Core(s) per socket"]

  if FLAGS.intel_spec17_run_script:
    vm.RobustRemoteCommand('cd {dir} && chmod +x {script} && sudo ./{script}'
                           .format(dir=vm.speccpu_vm_state.spec_dir, script=FLAGS.intel_spec17_run_script))
  else:
    cmd = ('. ./shrc && '
           'ulimit -s unlimited && ')
    options = ''

    if os.path.isfile(topo_txt):
      vm.RemoteCommand('rm {0}'.format(topo_txt))

    if os.path.isfile(numa_detection_script):
      cmd += '. ./numa-detection.sh && '

    if os.path.isfile(nhmtopology):
      vm.RemoteCommand('specperl {0}'.format(nhmtopology))
      stdout, _ = vm.RemoteCommand('cat {0}'.format(topo_txt))
      topology = '{0}'.format(stdout)

    cmd += ('sync ; echo 3 | sudo tee /proc/sys/vm/drop_caches && ')

    if numa_node_count > 0:
      cmd += 'numactl --interleave=all '

    cmd += 'runcpu '

    if FLAGS.intel_spec17_runmode and metadata['Spec_cpu_2017_runmode'] != 'CUSTOM':
      runcpu_options = [
          ('config', metadata['Spec_cpu_2017_config_file']),
          ('tune', metadata['Spec_cpu_2017_tuning']),
          ('size', metadata['Spec_cpu_2017_size']),
          ('iterations', metadata['Spec_cpu_2017_iterations']),
          ('action', metadata['Spec_cpu_2017_action']),
          ('output_format', 'all')
      ]
      if metadata['Spec_cpu_2017_copies'] != '0':
        runcpu_options.append(('copies', metadata['Spec_cpu_2017_copies']))
      else:
        runcpu_options.append(('copies', vm.NumCpusForBenchmark()))

      if os.path.isfile(nhmtopology):
        options += '--define {} '.format(topology)

      if FLAGS.intel_spec17_runmode in [
          'SIR_TP_ICC19', 'SIR_SC_ICC19', 'SFP_TP_ICC19', 'SFP_SC_ICC19',
          'SIR_TC_GCC82', 'SIR_SC_GCC82', 'SFP_TC_GCC82', 'SFP_SC_GCC82'
      ]:
        if numa_node_count == 0:
          options += '--define no_numa '
        options += '--define cores={} '.format(cores)

      if FLAGS.intel_spec17_runmode in [
          'SIR_TP_ICC19', 'SIR_SC_ICC19', 'SFP_TP_ICC19', 'SFP_SC_ICC19'
      ]:
        options += '--define numcopies={} '.format(vm.NumCpusForBenchmark())

      options += ''.join('--{0}={1} '.format(k, v) for k, v in runcpu_options)
      options += '{0} '.format(metadata['Spec_cpu_2017_options'])

      runcpu_cmd = '{cmd} {options} {workload}'.format(
          cmd=cmd,
          options=options,
          workload=metadata['Spec_cpu_2017_benchmark'])
    else:
      runcpu_options = [
          ('config', FLAGS.intel_spec17_config_file),
          ('tune', FLAGS.intel_spec17_tuning or 'base'),
          ('size', FLAGS.intel_spec17_size),
          ('iterations', FLAGS.intel_spec17_iterations or 1),
          ('action', FLAGS.intel_spec17_action),
          ('output_format', 'all')
      ]

      if FLAGS.intel_spec17_copies:
        runcpu_options.append(('copies', FLAGS.intel_spec17_copies))
      else:
        runcpu_options.append(('copies', vm.NumCpusForBenchmark()))

      if FLAGS.intel_spec17_define:
        for runspec_define in FLAGS.intel_spec17_define.split(','):
          runcpu_options.append(('define', runspec_define))

      if os.path.isfile(nhmtopology):
        runcpu_options.append(('define', topology))

      options = ''.join('--{0}={1} '.format(k, v) for k, v in runcpu_options)
      options += '--noreportable '

      if FLAGS.intel_spec17_benchmark in ['intrate', 'intspeed', 'fprate', 'fpspeed']:
        options = options.replace('--noreportable', '')

      if FLAGS.intel_spec17_runcpu_options:
        options += '{0} '.format(FLAGS.intel_spec17_runcpu_options)

      runcpu_cmd = '{cmd} {options} {workload}'.format(
          cmd=cmd, options=options, workload=FLAGS.intel_spec17_benchmark)
      metadata['Spec_cpu_2017_tuning'] = runcpu_options[1][1]
      metadata['Spec_cpu_2017_iterations'] = runcpu_options[3][1]
      metadata['Spec_cpu_2017_copies'] = runcpu_options[6][1]

    cmd = 'cd {0} && sudo bash -c \'{runcpu_cmd}\''.format(vm.speccpu_vm_state.spec_dir, runcpu_cmd=runcpu_cmd)
    vm.RobustRemoteCommand(cmd)

  try:
    _DownloadResults(benchmark_spec)
  except:
    logging.warning('failed to download results')

  try:
    samples = _ParseResults(vm, LOG_FILENAME, metadata)
  except:
    # don't crash if we can't parse the results text file
    logging.warning('failed to parse results text file')
    samples = [sample.Sample('Parsing failed', 0, '')]
  return samples


def Cleanup(benchmark_spec):
  """Cleans up SPEC CPU2017 from the target vm.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  vm = benchmark_spec.vms[0]
  speccpu.Uninstall(vm)
