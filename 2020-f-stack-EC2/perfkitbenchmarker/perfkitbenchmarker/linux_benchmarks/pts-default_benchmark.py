import logging
import xml.etree.ElementTree as ET

from perfkitbenchmarker import configs
from perfkitbenchmarker.linux_packages import phoronix_test_suite
from absl import flags
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import sample

FLAGS = flags.FLAGS
flags.DEFINE_string('pts_benchmark', 'pts/aio-stress', 'Phoronix Test Suite benchmark to execute')
flags.DEFINE_string('pts_user_config', 'perfkitbenchmarker/data/phoronix/user-config.xml', 'Phoronix Test Suite user config file')

BENCHMARK_NAME = 'pts-default'

BENCHMARK_CONFIG = """
pts-default:
  description: >
    Executes a Phoronix Test Suite benchmark with default parameters
  vm_groups:
    default:
      vm_spec: *default_dual_core
      disk_spec: *default_50_gb
  flags:
    aws_boot_disk_size: 25
"""
PHORONIX_USER_DIR = '.phoronix-test-suite'
PHORONIX_RESULTS_DIR = 'test-results'


def GetConfig(user_config):
  return configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)


def _GetResults(vm, results_xml):
  # get all the result files back to our local host
  return vm.PullFile(vm_util.GetTempDir(), results_xml)


def _ParseResults():
  samples = []
  metadata = {'benchmark': FLAGS.pts_benchmark}
  local_results = "{0}/composite.xml".format(vm_util.GetTempDir())
  tree = ET.parse(local_results)
  root = tree.getroot()
  for result in root.findall('Result'):
    scale = result.find('Scale')
    data = result.find('Data')
    for entry in data.findall('Entry'):
      for item in entry:
        metadata[item.tag] = item.text
        if item.tag == 'Value':
          value = item.text
    samples.append(sample.Sample('metric', value, scale.text, metadata))
  return samples


def _SetProxy(user_config, proxy_host, proxy_port):
  # We have to modify the XML to use a proxy in PTS
  try:
    tree = ET.parse(user_config)
    root = tree.getroot()
    proxy_host_tag = root.find('Options/Networking/ProxyAddress')
    proxy_host_tag.text = proxy_host
    proxy_port_tag = root.find('Options/Networking/ProxyPort')
    proxy_port_tag.text = proxy_port
    tree.write(user_config)
  except Exception as e:
    # This may happen if your file is corrupted
    logging.error('Exception setting proxy: %s' % e)
    exit(1)


def Prepare(benchmark_spec):
  vm = benchmark_spec.vms[0]
  if FLAGS.http_proxy:
    host = FLAGS.http_proxy.split(':')[1].strip('/')
    port = FLAGS.http_proxy.split(':')[2].rstrip('/ ')
    _SetProxy(FLAGS.pts_user_config, host, port)
  vm.Install('phoronix_test_suite')
  vm.RemoteCommand('mkdir -p .phoronix-test-suite')
  vm.PushFile(FLAGS.pts_user_config, PHORONIX_USER_DIR)
  vm.RemoteCommand('/usr/bin/phoronix-test-suite enterprise-setup')
  # On CentOS and Clear they prompt for a password even though it's not needed. Below is the workaround
  vm.RemoteCommand('echo | sudo /usr/bin/phoronix-test-suite install {0}'.format(FLAGS.pts_benchmark))


def Run(benchmark_spec):
  benchmark_results_dir = 'pkb-' + FLAGS.pts_benchmark.split('/')[1].split('-')[0]
  RESULTS_XML = "/".join([PHORONIX_USER_DIR, PHORONIX_RESULTS_DIR, benchmark_results_dir, 'composite.xml'])
  cmd = [
      "TEST_RESULTS_NAME={0}".format(benchmark_results_dir),
      "/usr/bin/phoronix-test-suite default-benchmark {0}".format(FLAGS.pts_benchmark)
  ]
  benchmark_spec.vms[0].RemoteCommand(" ".join(cmd), login_shell=True)
  _GetResults(benchmark_spec.vms[0], RESULTS_XML)
  return _ParseResults()


def Cleanup(benchmark_spec):
  # Note: the phoronix_test_suite PKB package cleans up after itself on the SUT
  # Unset the proxy
  _SetProxy(FLAGS.pts_user_config, '', '')
