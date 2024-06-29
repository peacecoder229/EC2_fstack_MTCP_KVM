"""Records system information using svrinfo.
"""

import os
import logging

from six.moves.urllib.parse import urlparse


from perfkitbenchmarker import events
from perfkitbenchmarker import trace_util
from absl import flags
from perfkitbenchmarker import vm_util

SVRINFO_ARCHIVE_NAME = 'svr_info.tgz'
SVRINFO_ARCHIVE_URL = "https://gitlab.devtools.intel.com/cumulus/external_dependencies/svr_info/raw/master/svr_info_internal.tgz"

flags.DEFINE_boolean('svrinfo', True,
                     'Run svrinfo on VMs.')
flags.DEFINE_string('svrinfo_flags', '--format all',
                    'Command line flags that get passed to svr_info.')
flags.DEFINE_string('svrinfo_tarball', None,
                    'Local path to svr_info tarball.')
flags.DEFINE_string('svrinfo_url', None,
                    'URL for downloading svr_info tarball.')
FLAGS = flags.FLAGS


class _SvrinfoCollector(object):
  """Manages running svrinfo"""
  def __init__(self):
    pass


  def InstallAndRun(self, unused_sender, benchmark_spec):
    """Install, Run, Retrieve/Publish on all VMs."""
    vms = trace_util.GetVMsToTrace(benchmark_spec, FLAGS.trace_vm_groups)
    if vms:
      svr_info_archive = _GetLocalArchive()
      vm_util.IssueCommand(["tar", "-C", vm_util.GetTempDir(), "-xf", svr_info_archive])
      vm_util.RunThreaded(lambda vm: _Run(vm, benchmark_spec), vms)
      vm_util.IssueCommand(["rm", svr_info_archive])
      vm_util.IssueCommand(["rm", "-rf", os.path.join(vm_util.GetTempDir(), 'svr_info')])


def _GetLocalArchive():
  """ get or make sure we already have the svr_info archive """
  if FLAGS.svrinfo_tarball:
    logging.info("svrinfo_tarball specified: {}".format(FLAGS.svrinfo_tarball))
    local_archive_path = FLAGS.svrinfo_tarball
  else:
    url = FLAGS.svrinfo_url or SVRINFO_ARCHIVE_URL
    logging.info("downloading svrinfo from: {}".format(url))
    filename = os.path.basename(urlparse(url).path)
    local_archive_path = os.path.join(vm_util.GetTempDir(), filename)
    vm_util.IssueCommand(["wget", "-O", local_archive_path, url])
  return local_archive_path


def _Run(vm, benchmark_spec):
  output_dir = os.path.join(vm_util.GetTempDir(), vm.name + '-svrinfo')
  vm_util.IssueCommand(["mkdir", "-p", output_dir])
  command = [
      os.path.join(".", "svr_info")
  ]
  command.extend(FLAGS.svrinfo_flags.split())
  command.extend([
      "--output",
      output_dir,
      "--ip",
      vm.ip_address,
      "--port",
      str(vm.ssh_port),
      "--user",
      vm.user_name])
  key = vm.ssh_private_key if vm.is_static else vm_util.GetPrivateKeyPath()
  if key is not None:
      command.extend(["--key", key])
  vm_util.IssueCommand(command, cwd=os.path.join(vm_util.GetTempDir(), "svr_info"), timeout=None)


def Register(parsed_flags):
  """Register the collector if FLAGS.svrinfo is set."""
  if not parsed_flags.svrinfo:
    return
  logging.info('Registering svr_info collector to run after PREPARE phase.')
  collector = _SvrinfoCollector()
  events.after_phase.connect(collector.InstallAndRun, events.PREPARE_PHASE, weak=False)


def IsEnabled():
  return FLAGS.svrinfo
