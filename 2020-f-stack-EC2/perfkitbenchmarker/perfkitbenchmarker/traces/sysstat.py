""" Sysstat collector """
import os.path
import logging

from perfkitbenchmarker import events
from absl import flags
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import trace_util
from perfkitbenchmarker.linux_packages import sysstat
from perfkitbenchmarker.linux_packages import INSTALL_DIR

FLAGS = flags.FLAGS

flags.DEFINE_boolean('sysstat', False,
                     'Install and run sysstat.')
flags.DEFINE_integer('sysstat_vmstat_interval', 1,
                     'vmstat collection interval. zero to disable',
                     lower_bound=0)
flags.DEFINE_integer('sysstat_mpstat_interval', 1,
                     'mpstat collection interval. zero to disable',
                     lower_bound=0)
flags.DEFINE_integer('sysstat_iostat_interval', 10,
                     'iostat collection interval. zero to disable',
                     lower_bound=0)
flags.DEFINE_integer('sysstat_sar_interval', 1,
                     'sar collection interval. zero to disable',
                     lower_bound=0)

VMSTAT_OUTPUT_FILENAME = 'vm.dat'
VMSTAT_OUTPUT_FILE = os.path.join(INSTALL_DIR, VMSTAT_OUTPUT_FILENAME)

MPSTAT_OUTPUT_FILENAME = 'mp.dat'
MPSTAT_OUTPUT_FILE = os.path.join(INSTALL_DIR, MPSTAT_OUTPUT_FILENAME)

IOSTAT_OUTPUT_FILENAME = 'io.dat'
IOSTAT_OUTPUT_FILE = os.path.join(INSTALL_DIR, IOSTAT_OUTPUT_FILENAME)

SARNET_OUTPUT_FILENAME = 'sarNet.dat'
SARNET_OUTPUT_FILE = os.path.join(INSTALL_DIR, SARNET_OUTPUT_FILENAME)

SARALL_OUTPUT_FILENAME = 'sarBinary.dat'
SARALL_OUTPUT_FILE = os.path.join(INSTALL_DIR, SARALL_OUTPUT_FILENAME)

SARALL_CSV_FILENAME = 'sadfConvert_d.csv'
SARALL_CSV_FILE = os.path.join(INSTALL_DIR, SARALL_CSV_FILENAME)


class _Collector(object):

  def __init__(self):
    pass

  def _InstallSysstat(self, vm):
    vm.Install('sysstat')

  def Install(self, sender, benchmark_spec):
    """Install sysstat on all VMs."""

    vms = trace_util.GetVMsToTrace(benchmark_spec, FLAGS.trace_vm_groups)
    vm_util.RunThreaded(self._InstallSysstat, vms)

  def _StartSysstat(self, vm):

    # Tuple of (binary, enabled if flag is present, arguments)
    vmstat = (sysstat.VMSTAT_TOOL,
              FLAGS.sysstat_vmstat_interval,
              '-nt {:d} > {} 2>&1'.format(FLAGS.sysstat_vmstat_interval, VMSTAT_OUTPUT_FILE))
    mpstat = (sysstat.MPSTAT_TOOL,
              FLAGS.sysstat_mpstat_interval,
              '-P ALL {:d} > {} 2>&1'.format(FLAGS.sysstat_mpstat_interval, MPSTAT_OUTPUT_FILE))
    iostat = (sysstat.IOSTAT_TOOL,
              FLAGS.sysstat_iostat_interval,
              '-kxt {:d} > {} 2>&1'.format(FLAGS.sysstat_iostat_interval, IOSTAT_OUTPUT_FILE))
    sar_network = (sysstat.SAR_TOOL,
                   FLAGS.sysstat_sar_interval,
                   '-n DEV -o {} {:d} > /dev/null 2>&1'.format(SARNET_OUTPUT_FILE, FLAGS.sysstat_sar_interval))
    sar_all = (sysstat.SAR_TOOL,
               FLAGS.sysstat_sar_interval,
               '-A -o {} {:d} > /dev/null 2>&1'.format(SARALL_OUTPUT_FILE, FLAGS.sysstat_sar_interval))

    for tool, enabled, tool_args in [vmstat, mpstat, iostat, sar_network, sar_all]:
      if enabled:
        sysstat.StartSysStat(vm, tool, tool_args)

  def Start(self, unused_sender, benchmark_spec):
    """Start sysstat

    Args:
      benchmark_spec: benchmark_spec.BenchmarkSpec. The benchmark currently
          running.
    """
    vms = trace_util.GetVMsToTrace(benchmark_spec, FLAGS.trace_vm_groups)
    vm_util.RunThreaded(self._StartSysstat, vms)

  def After(self, sender, benchmark_spec):
    """Stop sysstat on all VMs and fetch results."""
    def _Run(vm):
      for tool, enabled in [
          (sysstat.VMSTAT_TOOL, FLAGS.sysstat_vmstat_interval),
          (sysstat.MPSTAT_TOOL, FLAGS.sysstat_mpstat_interval),
          (sysstat.IOSTAT_TOOL, FLAGS.sysstat_iostat_interval),
          (sysstat.SAR_TOOL, FLAGS.sysstat_sar_interval)
      ]:
        if enabled:
          sysstat.StopSysStat(vm, tool)
      if FLAGS.sysstat_sar_interval:
        sysstat.PostProcessSar(vm, SARALL_OUTPUT_FILE, SARALL_CSV_FILE)
      _FetchResults(vm)
    vms = trace_util.GetVMsToTrace(benchmark_spec, FLAGS.trace_vm_groups)
    vm_util.RunThreaded(_Run, vms)


def _FetchResults(vm):
  local_results_dir = os.path.join(vm_util.GetTempDir(), vm.name + '-sysstat')
  vm_util.IssueCommand(['mkdir', '-p', local_results_dir])
  for filename, filepath, enabled in [
      (VMSTAT_OUTPUT_FILENAME, VMSTAT_OUTPUT_FILE, FLAGS.sysstat_vmstat_interval),
      (MPSTAT_OUTPUT_FILENAME, MPSTAT_OUTPUT_FILE, FLAGS.sysstat_mpstat_interval),
      (IOSTAT_OUTPUT_FILENAME, IOSTAT_OUTPUT_FILE, FLAGS.sysstat_iostat_interval),
      (SARALL_CSV_FILENAME, SARALL_CSV_FILE, FLAGS.sysstat_sar_interval),
      (SARNET_OUTPUT_FILENAME, SARNET_OUTPUT_FILE, FLAGS.sysstat_sar_interval),
      (SARALL_OUTPUT_FILENAME, SARALL_OUTPUT_FILE, FLAGS.sysstat_sar_interval)
  ]:
    if enabled:
      vm.PullFile(os.path.join(local_results_dir, filename), filepath)


def Register(parsed_flags):
  """Register the collector."""
  if not parsed_flags.sysstat:
    return
  logging.info('Registering sysstat collector')
  collector = _Collector()
  events.before_phase.connect(collector.Install, events.RUN_PHASE, weak=False)
  events.start_trace.connect(collector.Start, events.RUN_PHASE, weak=False)
  events.stop_trace.connect(collector.After, events.RUN_PHASE, weak=False)


def IsEnabled():
  return FLAGS.sysstat
