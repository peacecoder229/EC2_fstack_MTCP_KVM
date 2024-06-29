# PerfSpect-PKB integration
import logging
import os
import posixpath
import time

from perfkitbenchmarker import events
from absl import flags
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import data
from perfkitbenchmarker import trace_util

FLAGS = flags.FLAGS

flags.DEFINE_boolean('perfspect', False,
                     'Install and run perfspect on the target system.')

PERFSPECT_GIT_LINK = "https://gitlab.devtools.intel.com/cloud/PerfSpect.git"
PREREQ_PKGS = ["linux-tools-common",
               "linux-tools-generic",
               "linux-tools-`uname -r`"]



class PerfspectCollector(object):
  """Manages running telemetry during a test, and fetching the results folder."""

  telemetry_dir = "/opt/perf_telemetry"

  def __init__(self):
    self.pid = None
    self.perf_dir = None

  def _FetchResults(self, vm):
    """Fetches telemetry results."""
    logging.info('Fetching telemetry results')
    perfspect_dir = '~/' + vm.name + '-perfspect'
    vm.RemoteCommand(('mkdir {0} ').format(perfspect_dir))
    vm.RemoteCommand(' '.join(map(str, ["sudo", "cp", "-r", os.path.join(self.telemetry_dir, 'perfspect', 'results', '*'),
                     perfspect_dir])))
    vm.RemoteCopy(vm_util.GetTempDir(), perfspect_dir, False)
    logging.info('PerfSpect results copied')

  def _InstallTelemetry(self, vm):
    """Installs Telemetry on the VM."""

    logging.info('Installing perfspect on VM')
    vm.RemoteCommand(' '.join(map(str, ["sudo", "rm", "-rf", self.telemetry_dir])))
    vm.RemoteCommand(' '.join(map(str, ["sudo", "mkdir", "-p", self.telemetry_dir])))
    vm.PushFile(self.perf_dir)
    vm.RemoteCommand(' '.join(map(str, ["sudo", "cp", "-r", "./perfspect", self.telemetry_dir + "/"])))
    vm.InstallPackages(' '.join(PREREQ_PKGS))

  def _StartTelemetry(self, vm):
    """Starts Telemetry on the VM"""
    collect_cmd = ['sudo', 'python3', os.path.join(self.telemetry_dir, 'perfspect', 'perf-collect.py'),
                   '>', '/dev/null', '2>&1', '&', 'echo $!']
    stdout, _ = vm.RemoteCommand(' '.join(collect_cmd))
    self.pid = stdout.strip()
    logging.debug("pid of perfspect collector process: {0}".format(self.pid))

  def _StopTelemetry(self, vm):
    """Stops Telemetry on the VM."""
    logging.info('Stopping telemetry')
    vm.RemoteCommand('sudo pkill perf')
    logging.debug('waiting until the process is killed')
    wait_cmd = ['tail', '--pid=' + self.pid, '-f', '/dev/null']
    vm.RemoteCommand(' '.join(wait_cmd))
    logging.info('Post processing perfspect raw metrics')
    postprocess_cmd = ['cd', os.path.join(self.telemetry_dir, 'perfspect'), '&&', 'sudo', './perf-postprocess-html',
                       '-r', 'results/perfstat.csv', '--html']
    vm.RemoteCommand(' '.join(postprocess_cmd))


  def Install(self, unused_sender, benchmark_spec):
    """Install Telemetry.

    Args:
      benchmark_spec: benchmark_spec.BenchmarkSpec. The benchmark currently
          running.
    """
    logging.info('Installing telemetry')
    self.perf_dir = os.path.join(vm_util.GetTempDir(), 'perfspect')
    vm_util.IssueCommand("git clone {0} {1}".format(PERFSPECT_GIT_LINK, self.perf_dir).split())
    rm_cmd = "rm -rf " + os.path.join(str(self.perf_dir), '.git')
    vm_util.IssueCommand(rm_cmd.split())
    logging.debug(trace_util.GetVMsToTrace(benchmark_spec, FLAGS.trace_vm_groups))
    vm_util.RunThreaded(self._InstallTelemetry, trace_util.GetVMsToTrace(benchmark_spec, FLAGS.trace_vm_groups))

  def Start(self, unused_sender, benchmark_spec):
    """Start Telemetry

    Args:
      benchmark_spec: benchmark_spec.BenchmarkSpec. The benchmark currently
          running.
    """
    logging.info('Starting telemetry')
    vm_util.RunThreaded(self._StartTelemetry, trace_util.GetVMsToTrace(benchmark_spec, FLAGS.trace_vm_groups))

  def After(self, unused_sender, benchmark_spec):
    """Stop telemetry, fetch results from VM(s).

    Args:
      benchmark_spec: benchmark_spec.BenchmarkSpec. The benchmark that stopped
          running.
    """
    vm_util.RunThreaded(self._StopTelemetry, trace_util.GetVMsToTrace(benchmark_spec, FLAGS.trace_vm_groups))
    vm_util.RunThreaded(self._FetchResults, trace_util.GetVMsToTrace(benchmark_spec, FLAGS.trace_vm_groups))


def Register(parsed_flags):
  """Register the collector if FLAGS.perfspect is set."""
  if not parsed_flags.perfspect:
    return
  logging.info('Registering telemetry collector')
  telemetry_collector = PerfspectCollector()
  events.before_phase.connect(telemetry_collector.Install, events.RUN_PHASE, weak=False)
  events.start_trace.connect(telemetry_collector.Start, events.RUN_PHASE, weak=False)
  events.stop_trace.connect(telemetry_collector.After, events.RUN_PHASE, weak=False)


def IsEnabled():
  return FLAGS.perfspect
