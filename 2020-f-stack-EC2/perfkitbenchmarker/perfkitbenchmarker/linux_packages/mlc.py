"""Intel Memory Latency Checker (mlc).
"""
import posixpath
import os
import logging
import re

from perfkitbenchmarker.linux_packages import INSTALL_DIR
from absl import flags
from perfkitbenchmarker import data
from perfkitbenchmarker import sample
from perfkitbenchmarker import vm_util

MLC_INSTALL_DIR = posixpath.join(INSTALL_DIR, 'mlc')
MLC_BIN = posixpath.join(MLC_INSTALL_DIR, 'Linux', 'mlc_internal')
MLC_MODES = ['loaded_latency', 'idle_latency', 'peak_injection_bandwidth', 'latency_matrix']
HUGEPAGES_PROC_ENTRY = "/proc/sys/vm/nr_hugepages"
ARCHIVE_LINK = ("https://gitlab.devtools.intel.com/cumulus/external_dependencies/mlc/raw/master/"
                "mlc_v3.9-internal.zip")

flags.DEFINE_list('mlc_modes', MLC_MODES,
                  'List of mlc analysis modes. Supported modes are: '
                  '%s' % ', '.join(MLC_MODES)
                  )
flags.register_validator('mlc_modes',
                         lambda modes: modes and set(modes).issubset(MLC_MODES),
                         'Invalid modes list. mlc_modes must be a subset of: '
                         + ', '.join(MLC_MODES) + '.')
flags.DEFINE_string('mlc_options', '-Z',
                    'mlc options.')
flags.DEFINE_integer('mlc_numhugepages', 4000, 'Number of huge pages that will be use')

FLAGS = flags.FLAGS


def _ParseMetaData(output):
  """
  Retrieves mlc version and command line parameters in a dictionary that
  can be used as metadata for Sample objects
  args:
    output: string containing stdout from running mlc with no parameters
  return:
    dictionary of metadata
  """
  metadata = {}
  match = re.search(r'Intel\(R\) Memory Latency Checker.*(v\d.\d.*)', output)
  if match:
    metadata['MLC version'] = match.group(1)
  match = re.search(r'Command line parameters: (.*)', output)
  if match:
    metadata['Parameters'] = match.group(1)
  return metadata


def _CheckPlatform(vm):
  supportsAvx512, _ = vm.RemoteCommand("lscpu | grep avx512", ignore_failure=True)
  mlc_options = ''
  if supportsAvx512:
    mlc_options = FLAGS.mlc_options
  return mlc_options


def _ParseIdleLatency(output):
  """
  Creates Sample objects from mlc output
  args:
    output: string containing stdout from running mlc with no parameters
  return:
    an array of Sample objects
  """
  """ Example output for 'mlc --idle_latency':
  Intel(R) Memory Latency Checker - v3.6
  Command line parameters: --idle_latency

  Using buffer size of 200.000MiB
  Each iteration took 176.8 core clocks ( 57.2    ns)
  """
  samples = []
  metadata = _ParseMetaData(output)
  for line in output.splitlines():
    match = re.search(r'Each iteration took\s+(\d+\.\d+) core clocks \(\s+(\d+\.\d+)\s+ns\)', line)
    if match:
      clocks = match.group(1)
      ns = match.group(2)
      samples.append(sample.Sample('clocks per iteration', clocks, 'clocks', metadata))
      samples.append(sample.Sample('time per iteration', ns, 'ns', metadata))
  return samples


def _ParseIdleLatencyMatrix(output):
  """
  Creates Sample objects from mlc output
  args:
    output: string containing stdout from running mlc with no parameters
  return:
    an array of Sample objects
  """
  """ Example output for 'mlc --latency_matrix':
  Intel(R) Memory Latency Checker (for Internal Use Only) - v3.6-internal
  Command line parameters: -r --latency_matrix

  Using buffer size of 2000.000MiB
  Measuring idle latencies (in ns)...
                  Numa node
  Numa node            0
         0          93.8
  """
  samples = []
  metadata = _ParseMetaData(output)
  unit = 'ns'
  for line in output.splitlines():
    match = re.search(r'\s+([0-9]*)\s+([0-9]*\.[0-9]*)', line)
    if match:
      samples.append(sample.Sample("Numa node " + match.group(1), match.group(2), unit, metadata))
  return samples


def _ParseLoadedLatency(output):
  """
  Creates Sample objects from mlc output
  args:
    output: string containing stdout from running mlc with no parameters
  return:
    an array of Sample objects
  """
  """ Example output for 'mlc --loaded_latency':
  Intel(R) Memory Latency Checker (for Internal Use Only) - v3.6-internal
  Command line parameters: --loaded_latency

  Using buffer size of 100.000MiB/thread for reads and an additional 100.000MiB/thread for writes

  Measuring Loaded Latencies for the system
  Using all the threads from each core if Hyper-threading is enabled
  Using Read-only traffic type
  Inject  Latency Bandwidth
  Delay   (ns)    MB/sec
  ==========================
  00000   97.12    15194.9
  00002   97.32    15204.5
  00008   96.63    15147.5
  00015   95.63    15013.4
  00050   72.39    12056.7
  00100   62.89     8465.2
  00200   59.17     5133.9
  00300   57.84     3872.9
  00400   56.94     3224.4
  00500   56.43     2827.6
  00700   56.52     2350.9
  01000   56.25     1995.1
  01300   56.23     1799.9
  01700   56.23     1645.5
  02500   56.07     1487.1
  03500   56.06     1388.9
  05000   56.07     1314.6
  09000   56.01     1239.0
  20000   55.99     1186.5
  """
  samples = []
  metadata = _ParseMetaData(output)
  for line in output.splitlines():
    match = re.search(r'\s+(\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)', line)
    if match:
      inject_delay = match.group(1)
      latency = match.group(2)
      bandwidth = match.group(3)
      # two metrics per row of data
      metric = '%s_Latency' % inject_delay
      unit = 'ns'
      samples.append(sample.Sample(metric, latency, unit, metadata))
      metric = '%s_Bandwidth' % inject_delay
      unit = 'MB/sec'
      samples.append(sample.Sample(metric, bandwidth, unit, metadata))
  return samples


def _ParsePeakInjectionBW(output):
  """
  Creates Sample objects from mlc output
  args:
    output: string containing stdout from running mlc with no parameters
  return:
    an array of Sample objects
  """
  """ Example output for 'mlc --peak_injection_bandwidth'
  Intel(R) Memory Latency Checker (for Internal Use Only) - v3.6-internal
  Command line parameters: --peak_injection_bandwidth

  Using buffer size of 183.105MiB/thread for reads and an additional 183.105MiB/thread for writes

  Measuring Peak Injection Memory Bandwidths for the system
  Bandwidths are in MB/sec (1 MB/sec = 1,000,000 Bytes/sec)
  Using all the threads from each core if Hyper-threading is enabled
  Using traffic with the following read-write ratios
  ALL Reads        :      87110.7
  4:1 Reads-Writes :      90523.6
  3:1 Reads-Writes :      90609.0
  2:1 Reads-Writes :      90891.9
  1:1 Reads-Writes :      92297.7
  Stream-triad like:      81389.0
  All NT writes    :      47772.8
  1:1 Read-NT write:      76965.5
  """
  samples = []
  metadata = _ParseMetaData(output)
  unit = 'MB/sec'
  resultStrings = ['ALL Reads', '4:1 Reads-Writes', '3:1 Reads-Writes', '2:1 Reads-Writes',
                   '1:1 Reads-Writes', 'Stream-triad like', 'All NT writes', '1:1 Read-NT write']
  for line in output.splitlines():
    for val in resultStrings:
      match = re.search(r'({0})\s*\:\s+([0-9]*\.[0-9]*)'.format(val), line)
      if match:
        samples.append(sample.Sample(match.group(1), match.group(2), unit, metadata))
  return samples


def _GetAbsPath(path):
  absPath = os.path.abspath(os.path.expanduser(path))
  if not os.path.isfile(absPath):
    raise RuntimeError('File (%s) does not exist.' % path)
  return absPath


def _ParseOutput(mode, output):
  """
  Parse mlc output
  args:
    mode: the mlc analysis mode
    output: the mlc execution output
  return:
    list of Sample objects
  """
  if mode == 'loaded_latency':
    return _ParseLoadedLatency(output)
  if mode == 'idle_latency':
    return _ParseIdleLatency(output)
  if mode == 'peak_injection_bandwidth':
    return _ParsePeakInjectionBW(output)
  if mode == 'latency_matrix':
    return _ParseIdleLatencyMatrix(output)


def Run(vm):
  """
  Runs mlc
  args:
    vm
  return:
    list of Samples
  """
  samples = []
  mlc_options = FLAGS.mlc_options
  if not FLAGS['mlc_options'].present:
    mlc_options = _CheckPlatform(vm)
  for mode in FLAGS.mlc_modes:
    if mode == 'peak_injection_bandwidth':
      output, _ = vm.RobustRemoteCommand('sudo %s --%s' % (MLC_BIN, mode))
    else:
      output, _ = vm.RobustRemoteCommand('sudo {0} {1} --{2}'
                                         .format(MLC_BIN, mlc_options, mode))
    samples.extend(_ParseOutput(mode, output))
  return samples


def EnableHugePages(vm):
  # Save the original hugepages count
  HUGEPAGES_ORIGINAL_COUNT_FILE = vm_util.PrependTempDir("system_original_hugepages_count.txt")
  out, _ = vm.RemoteCommand("cat {0}".format(HUGEPAGES_PROC_ENTRY))
  with open(HUGEPAGES_ORIGINAL_COUNT_FILE, "w") as f:
    f.write(out.strip())

  # Set the desired number of hugepages
  cmd = "echo {0} | sudo tee {1} ".format(FLAGS.mlc_numhugepages, HUGEPAGES_PROC_ENTRY)
  vm.RemoteCommand(cmd)


def DisableHugePages(vm):
  # Load the original hugepages count and restore it
  HUGEPAGES_ORIGINAL_COUNT_FILE = vm_util.PrependTempDir("system_original_hugepages_count.txt")
  if os.path.exists(HUGEPAGES_ORIGINAL_COUNT_FILE):
    with open(HUGEPAGES_ORIGINAL_COUNT_FILE, "r") as f:
      original_hugepages_count = f.read().strip()
    cmd = "echo {0} | sudo tee {1} ".format(original_hugepages_count, HUGEPAGES_PROC_ENTRY)
    vm.RemoteCommand(cmd)
  else:
    logging.info("Backup file with original count of hugepages not found: {0}".format(
        HUGEPAGES_ORIGINAL_COUNT_FILE))


def Install(vm):
  tmp_dir = vm_util.GetTempDir()
  vm_util.IssueCommand("wget -P {0} {1}".format(tmp_dir, ARCHIVE_LINK).split())
  mlc_path = os.path.join(tmp_dir, ARCHIVE_LINK[ARCHIVE_LINK.rindex("/") + 1:])
  vm.InstallPackages('unzip')
  vm.RemoteCommand('mkdir -p %s' % (MLC_INSTALL_DIR))
  vm.PushFile(mlc_path, MLC_INSTALL_DIR)
  vm.RemoteCommand('cd %s && unzip -o %s && chmod +x %s' % (
      MLC_INSTALL_DIR,
      'mlc*.zip',
      MLC_BIN))
  vm.RemoteCommand('sudo modprobe msr')


def Uninstall(vm):
  pass
