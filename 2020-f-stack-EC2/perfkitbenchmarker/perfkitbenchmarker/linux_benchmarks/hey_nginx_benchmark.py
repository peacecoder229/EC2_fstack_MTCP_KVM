"""
hey_nginx HTTP server benchmark
"""
import functools
import os

from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import data

from perfkitbenchmarker import configs
from absl import flags
from perfkitbenchmarker.linux_packages import hey
from perfkitbenchmarker.linux_packages import openresty
from perfkitbenchmarker.linux_packages import intel_nginx
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import sample

flags.DEFINE_integer('hey_nginx_client_vms', 1,
                     'Number of client vms.',
                     lower_bound=1)
flags.DEFINE_integer('hey_nginx_requests_per_client', 100000,
                     'Number of HTTP requests each client will make.',
                     lower_bound=1)
flags.DEFINE_integer('hey_nginx_threads_per_client', 0,
                     'Number of concurrent threads each client will '
                     'use to send requests. Zero will match thread count '
                     'to the number of logical CPUs on the client system.',
                     lower_bound=0)
flags.DEFINE_enum('hey_nginx_nginx', "openresty", ['openresty', 'intel_nginx'],
                  'The nginx module to use during testing.')
FLAGS = flags.FLAGS

BENCHMARK_NAME = 'hey_nginx'
BENCHMARK_CONFIG = """
hey_nginx:
  description: nginx HTTP server benchmark.
  vm_groups:
    workers:
      vm_spec: *default_dual_core
      os_type: ubuntu1804
      vm_count: 1
    clients:
      vm_spec: *default_dual_core
      os_type: ubuntu1804
  flags:
"""

CSR_FILENAME = 'csr.pem'
CERTIFICATE_FILENAME = 'certificate.pem'
HTML_FILENAME = '1.html'
PRIVATE_KEY_FILENAME = 'privatekey.key'


def GetConfig(user_config):
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
  if FLAGS['hey_nginx_client_vms'].present:
    config['vm_groups']['clients']['vm_count'] = FLAGS.hey_nginx_client_vms
  return config


def _GetNginxModule():
  nginx = None
  if FLAGS.hey_nginx_nginx == 'openresty':
    nginx = openresty
  elif FLAGS.hey_nginx_nginx == 'intel_nginx':
    nginx = intel_nginx
  return nginx


def _SudoPushDataFile(vm, src, dest):
  vm.PushDataFile('hey_nginx/' + src, INSTALL_DIR)
  vm.RemoteCommand('sudo mv {} {}'.format(os.path.join(INSTALL_DIR, os.path.basename(src)), dest))


def _PrepareServer(vm):
  nginx = _GetNginxModule()
  vm.Install(FLAGS.hey_nginx_nginx)
  _SudoPushDataFile(vm, nginx.NGINX_CONF_FILENAME, nginx.NGINX_CONF_DIR)
  _SudoPushDataFile(vm, CERTIFICATE_FILENAME, nginx.NGINX_CONF_DIR)
  _SudoPushDataFile(vm, CSR_FILENAME, nginx.NGINX_CONF_DIR)
  _SudoPushDataFile(vm, PRIVATE_KEY_FILENAME, nginx.NGINX_CONF_DIR)
  _SudoPushDataFile(vm, HTML_FILENAME, nginx.NGINX_HTML_DIR)
  conf_file = os.path.join(nginx.NGINX_CONF_DIR, nginx.NGINX_CONF_FILENAME)
  vm.RemoteCommand("sudo sed -i 's/REPLACE_ME_WITH_SERVER_IP/{}/g' {}".format(vm.internal_ip, conf_file))
  vm.RemoteCommand("sudo sed -i 's/REPLACE_ME_WITH_NUM_LOGICAL_CPUS/{}/g' {}".format(vm.num_cpus, conf_file))
  nginx.TestConfig(vm)
  nginx.Start(vm)


def _PrepareClient(vm):
  vm.Install('hey')


def Prepare(benchmark_spec):
  server = benchmark_spec.vm_groups['workers'][0]
  server_partials = [functools.partial(_PrepareServer, server)]
  client_partials = [functools.partial(_PrepareClient, client)
                     for client in benchmark_spec.vm_groups['clients']]
  vm_util.RunThreaded((lambda f: f()), server_partials + client_partials)


def Run(benchmark_spec):
  samples = []
  results = []
  server = benchmark_spec.vm_groups['workers'][0]
  if FLAGS.hey_nginx_threads_per_client:
    num_threads = FLAGS.hey_nginx_threads_per_client
  else:
    num_threads = benchmark_spec.vm_groups['clients'][0].num_cpus
  url = 'https://{}:{}{}'.format(server.internal_ip, 4433, '/content/1')
  options = ['-n', str(FLAGS.hey_nginx_requests_per_client),
             '-c', str(num_threads),
             '-cpus', str(benchmark_spec.vm_groups['clients'][0].num_cpus)
             ]

  def _Run(vm):
    output = hey.Run(vm, ' '.join(options), url)
    results.append(hey.ParseSummaryOutput(output))
  vm_util.RunThreaded(_Run, benchmark_spec.vm_groups['clients'])
  # aggregate results from clients, create samples
  aggregated_result = {}
  for result in results:
    for k, v in result.items():
      if k not in aggregated_result:
        aggregated_result[k] = [0.0, v[1], v[2]]  # value, units, do average
      aggregated_result[k][0] += v[0]
  metadata = {}
  for k, v in aggregated_result.items():
    if v[2]:
      num_clients = len(benchmark_spec.vm_groups['clients'])
      aggregated_result[k][0] = aggregated_result[k][0] / num_clients
    samples.append(sample.Sample(k, v[0], v[1], metadata))
  return samples


def Cleanup(benchmark_spec):
  server = benchmark_spec.vm_groups['workers'][0]
  nginx = _GetNginxModule()
  nginx.Stop(server)
