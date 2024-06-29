# Copyright 2019 PerfKitBenchmarker Authors. All rights reserved.
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

"""Runs plain netperf in a few modes.

docs:
https://hewlettpackard.github.io/netperf/doc/netperf.html
manpage: http://manpages.ubuntu.com/manpages/maverick/man1/netperf.1.html

Runs TCP_RR, TCP_CRR, and TCP_STREAM benchmarks from netperf across two
machines.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import collections
import csv
import json
import logging
import os
import re
from perfkitbenchmarker import configs
from perfkitbenchmarker import data
from perfkitbenchmarker import errors
from perfkitbenchmarker import flag_util
from absl import flags
from perfkitbenchmarker import sample
from perfkitbenchmarker import vm_util
from perfkitbenchmarker.linux_packages import netperf
import six
from six.moves import zip
from six.moves import range


flag_util.DEFINE_integerlist('intel_netperf_client_vms', flag_util.IntegerList([1]),
                             'Number of virtual machines to provision and '
                             'use as clients. Netperf will run once for each value '
                             'in the list.', module_name=__name__)
flags.DEFINE_integer('intel_netperf_max_iter', None,
                     'Maximum number of iterations to run during '
                     'confidence interval estimation. If unset, '
                     'a single iteration will be run.',
                     lower_bound=3, upper_bound=30)
flags.DEFINE_integer('intel_netperf_test_length', 60,
                     'netperf test length, in seconds',
                     lower_bound=1)
flags.DEFINE_integer('intel_netperf_request_bytes', 1,
                     'The request size in bytes for'
                     'request/response benchmarks.',
                     lower_bound=1)
flags.DEFINE_integer('intel_netperf_response_bytes', 1,
                     'The response size in bytes for'
                     'request/response benchmarks.',
                     lower_bound=1)
flags.DEFINE_bool('intel_netperf_enable_histograms', True,
                  'Determines whether latency histograms are '
                  'collected/reported. Only for *RR benchmarks')
flag_util.DEFINE_integerlist('intel_netperf_num_streams', flag_util.IntegerList([1]),
                             'Number of netperf processes to run. Netperf '
                             'will run once for each value in the list.',
                             module_name=__name__)
flags.DEFINE_integer('intel_netperf_thinktime', 0,
                     'Time in nanoseconds to do work for each request.')
flags.DEFINE_integer('intel_netperf_thinktime_array_size', 0,
                     'The size of the array to traverse for thinktime.')
flags.DEFINE_integer('intel_netperf_thinktime_run_length', 0,
                     'The number of contiguous numbers to sum at a time in the '
                     'thinktime array.')

ALL_BENCHMARKS = ['TCP_RR', 'TCP_CRR', 'TCP_STREAM', 'UDP_RR']
flags.DEFINE_list('intel_netperf_benchmarks', ALL_BENCHMARKS,
                  'The netperf benchmark(s) to run.')
flags.register_validator(
    'intel_netperf_benchmarks',
    lambda benchmarks: benchmarks and set(benchmarks).issubset(ALL_BENCHMARKS))

FLAGS = flags.FLAGS

BENCHMARK_NAME = 'intel_netperf'
BENCHMARK_CONFIG = """
intel_netperf:
  description: Run TCP_RR, TCP_CRR, UDP_RR and TCP_STREAM
  vm_groups:
    workers:
      vm_spec: *default_single_core
      os_type: ubuntu1804
      vm_count: 1
    clients:
      vm_spec: *default_single_core
      os_type: ubuntu1804
  flags:
    gce_boot_disk_size: 200
    aws_boot_disk_size: 200
    publish_after_run: true
    ssh_reuse_connections: false  # we adjust the max open files, so need new ssh session
"""

MBPS = 'Mbits/sec'
TRANSACTIONS_PER_SECOND = 'transactions_per_second'
# Specifies the keys and to include in the results for OMNI tests.
# Any user of ParseNetperfOutput() (e.g. container_netperf_benchmark), must
# specify these selectors to ensure the parsing doesn't break.
OUTPUT_SELECTOR = (
    'THROUGHPUT,THROUGHPUT_UNITS,P50_LATENCY,P90_LATENCY,'
    'P99_LATENCY,STDDEV_LATENCY,MIN_LATENCY,MAX_LATENCY,'
    'CONFIDENCE_ITERATION,THROUGHPUT_CONFID,'
    'LOCAL_TRANSPORT_RETRANS,REMOTE_TRANSPORT_RETRANS')

# Command ports are even (id*2), data ports are odd (id*2 + 1)
PORT_START = 20000

REMOTE_SCRIPTS_DIR = 'netperf_test_scripts'
REMOTE_SCRIPT = 'netperf_test.py'

PERCENTILES = [50, 90, 99]

# By default, Container-Optimized OS (COS) host firewall allows only
# outgoing connections and incoming SSH connections. To allow incoming
# connections from VMs running netperf, we need to add iptables rules
# on the VM running netserver.
_COS_RE = re.compile(r'\b(cos|gci)-')


def GetConfig(user_config):
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
  if FLAGS['intel_netperf_client_vms'].present:
    config['vm_groups']['clients']['vm_count'] = max(FLAGS.intel_netperf_client_vms)
  return config


def PrepareNetperf(vm):
  """Installs netperf on a single vm."""
  vm.Install('netperf')

  # Set keepalive to a low value to ensure that the control connection
  # is not closed by the cloud networking infrastructure.
  # This causes keepalive packets to be sent every minute on all ipv4
  # tcp connections.
  #
  # TODO(user): Keepalive is not enabled on the netperf control socket.
  # While (for unknown reasons) this hack fixes the issue with the socket
  # being closed anyway, a more correct approach would be to patch netperf
  # and enable keepalive on the control socket in addition to changing the
  # system defaults below.
  #
  if vm.IS_REBOOTABLE:
    vm.ApplySysctlPersistent({
        'net.ipv4.tcp_keepalive_time': 60,
        'net.ipv4.tcp_keepalive_intvl': 60,
    })


def PrepareNetperfClients(vm):
  """Client specific configuration changes."""
  # increase the maximum number of open files, needs to be at least 4x the number of streams/# client vms
  before = int(vm.RemoteCommand('ulimit -n')[0])
  logging.info("ulimit -n (before): %s" % before)
  nofile = (max(FLAGS.intel_netperf_num_streams) * 4) / min(FLAGS.intel_netperf_client_vms)
  if before < nofile:
    vm.RemoteCommand('echo "* soft nofile %d" | sudo tee -a /etc/security/limits.conf' % nofile)
    vm.RemoteCommand('echo "* hard nofile %d" | sudo tee -a /etc/security/limits.conf' % nofile)
    vm.RemoteCommand('echo "session required pam_limits.so" | sudo tee -a /etc/pam.d/common-session')
    vm.RemoteCommand('echo "session required pam_limits.so" | sudo tee -a /etc/pam.d/common-session-noninteractive')
  logging.info("ulimit -n (after): %s" % vm.RemoteCommand('ulimit -n')[0])


def Prepare(benchmark_spec):
  """Install netperf on the target vm.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """

  vm_util.RunThreaded(PrepareNetperf, benchmark_spec.vms)

  server_vm = benchmark_spec.vm_groups['workers'][0]
  client_vms = benchmark_spec.vm_groups['clients']

  vm_util.RunThreaded(PrepareNetperfClients, client_vms)

  num_netserver_processes = max(FLAGS.intel_netperf_num_streams)

  # See comments where _COS_RE is defined.
  if server_vm.image and re.search(_COS_RE, server_vm.image):
    _SetupHostFirewall(benchmark_spec)

  # Start the netserver processes
  if vm_util.ShouldRunOnExternalIpAddress():
    # Open all of the command and data ports
    server_vm.AllowPort(PORT_START, PORT_START + num_netserver_processes * 2 - 1)
  netserver_cmd = ('for i in $(seq {port_start} 2 {port_end}); do '
                   '{netserver_path} -p $i & done').format(
                       port_start=PORT_START,
                       port_end=PORT_START + num_netserver_processes * 2 - 1,
                       netserver_path=netperf.NETSERVER_PATH)
  server_vm.RemoteCommand(netserver_cmd)

  # Copy remote test script to clients
  path = data.ResourcePath(os.path.join(REMOTE_SCRIPTS_DIR, REMOTE_SCRIPT))
  for vm in client_vms:
    logging.info('Uploading %s to %s', path, vm)
    vm.PushFile(path, REMOTE_SCRIPT)
    vm.RemoteCommand('sudo chmod 777 %s' % REMOTE_SCRIPT)


def _SetupHostFirewall(benchmark_spec):
  """Set up host firewall to allow incoming traffic.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """

  server_vm = benchmark_spec.vm_groups['workers'][0]
  client_vms = benchmark_spec.vm_groups['clients']

  ip_addrs = []
  for vm in client_vms:
    ip_addrs.append(vm.internal_ip)
    if vm_util.ShouldRunOnExternalIpAddress():
      ip_addrs.append(vm.ip_address)

  logging.info('setting up host firewall on %s running %s for client(s) at %s',
               server_vm.name, server_vm.image, ip_addrs)
  cmd = 'sudo iptables -A INPUT -p %s -s %s -j ACCEPT'
  for protocol in 'tcp', 'udp':
    for ip_addr in ip_addrs:
      server_vm.RemoteHostCommand(cmd % (protocol, ip_addr))


def _HistogramStatsCalculator(histogram, percentiles=PERCENTILES):
  """Computes values at percentiles in a distribution as well as stddev.

  Args:
    histogram: A dict mapping values to the number of samples with that value.
    percentiles: An array of percentiles to calculate.

  Returns:
    A dict mapping stat names to their values.
  """
  stats = {}

  # Histogram data in list form sorted by key
  by_value = sorted([(value, count) for value, count in histogram.items()],
                    key=lambda x: x[0])
  total_count = sum(histogram.values())

  cur_value_index = 0  # Current index in by_value
  cur_index = 0  # Number of values we've passed so far
  for p in percentiles:
    index = int(float(total_count) * float(p) / 100.0)
    index = min(index, total_count - 1)  # Handle 100th percentile
    for value, count in by_value[cur_value_index:]:
      if cur_index + count > index:
        stats['p%s' % str(p)] = by_value[cur_value_index][0]
        break
      else:
        cur_index += count
        cur_value_index += 1

  # Compute stddev
  value_sum = float(sum([value * count for value, count in histogram.items()]))
  average = value_sum / float(total_count)
  if total_count > 1:
    total_of_squares = sum([(value - average) ** 2 * count
                            for value, count in histogram.items()])
    stats['stddev'] = (total_of_squares / (total_count - 1)) ** 0.5
  else:
    stats['stddev'] = 0
  return stats


def ParseNetperfOutput(stdout, metadata, benchmark_name,
                       enable_latency_histograms):
  """Parses the stdout of a single netperf process.

  Args:
    stdout: the stdout of the netperf process
    metadata: metadata for any sample.Sample objects we create
    benchmark_name: the name of the netperf benchmark
    enable_latency_histograms: bool indicating if latency histograms are
        included in stdout

  Returns:
    A tuple containing (throughput_sample, latency_samples, latency_histogram)
  """
  # Don't modify the metadata dict that was passed in
  metadata = metadata.copy()

  # Extract stats from stdout
  # Sample output:
  #
  # "MIGRATED TCP REQUEST/RESPONSE TEST from 0.0.0.0 (0.0.0.0) port 20001
  # AF_INET to 104.154.50.86 () port 20001 AF_INET : +/-2.500% @ 99% conf.
  # : first burst 0",\n
  # Throughput,Throughput Units,Throughput Confidence Width (%),
  # Confidence Iterations Run,Stddev Latency Microseconds,
  # 50th Percentile Latency Microseconds,90th Percentile Latency Microseconds,
  # 99th Percentile Latency Microseconds,Minimum Latency Microseconds,
  # Maximum Latency Microseconds\n
  # 1405.50,Trans/s,2.522,4,783.80,683,735,841,600,900\n
  try:
    fp = six.StringIO(stdout)
    # "-o" flag above specifies CSV output, but there is one extra header line:
    banner = next(fp)
    if not banner.startswith('MIGRATED'):
      logging.warn("STDOUT did not start with the correct banner/header.")
      raise Exception()
    r = csv.DictReader(fp)
    results = next(r)
    logging.info('Netperf Results: %s', results)
    assert 'Throughput' in results
  except (StopIteration, AssertionError):
    # The output returned by netperf was unparseable - usually due to a broken
    # connection or other error.  Raise KnownIntermittentError to signal the
    # benchmark can be retried.  Do not automatically retry as an immediate
    # retry on these VMs may be adveresly affected (e.g. burstable credits
    # partially used)
    message = 'Netperf ERROR: Failed to parse stdout. STDOUT: %s' % stdout
    logging.error(message)
    raise errors.Benchmarks.KnownIntermittentError(message)

  # Update the metadata with some additional infos
  meta_keys = [('Confidence Iterations Run', 'confidence_iter'),
               ('Throughput Confidence Width (%)', 'confidence_width_percent')]
  if 'TCP' in benchmark_name:
    meta_keys.extend([
        ('Local Transport Retransmissions', 'netperf_retransmissions'),
        ('Remote Transport Retransmissions', 'netserver_retransmissions'),
    ])

  metadata.update({meta_key: results[netperf_key]
                   for netperf_key, meta_key in meta_keys})

  # Create the throughput sample
  throughput = float(results['Throughput'])
  throughput_units = results['Throughput Units']
  if throughput_units == '10^6bits/s':
    # TCP_STREAM benchmark
    unit = MBPS
    metric = '%s_Throughput' % benchmark_name
  elif throughput_units == 'Trans/s':
    # *RR benchmarks
    unit = TRANSACTIONS_PER_SECOND
    metric = '%s_Transaction_Rate' % benchmark_name
  else:
    raise ValueError('Netperf output specifies unrecognized throughput units %s'
                     % throughput_units)
  throughput_sample = sample.Sample(metric, throughput, unit, metadata)

  latency_hist = None
  latency_samples = []
  if enable_latency_histograms:
    # Parse the latency histogram. {latency: count} where "latency" is the
    # latency in microseconds with only 2 significant figures and "count" is the
    # number of response times that fell in that latency range.
    latency_hist = netperf.ParseHistogram(stdout)
    hist_metadata = {'histogram': json.dumps(latency_hist)}
    hist_metadata.update(metadata)
    latency_samples.append(sample.Sample(
        '%s_Latency_Histogram' % benchmark_name, 0, 'us', hist_metadata))
  if unit != MBPS:
    for metric_key, metric_name in [
        ('50th Percentile Latency Microseconds', 'p50'),
        ('90th Percentile Latency Microseconds', 'p90'),
        ('99th Percentile Latency Microseconds', 'p99'),
        ('Minimum Latency Microseconds', 'min'),
        ('Maximum Latency Microseconds', 'max'),
        ('Stddev Latency Microseconds', 'stddev')]:
      if metric_key in results:
        latency_samples.append(
            sample.Sample('%s_Latency_%s' % (benchmark_name, metric_name),
                          float(results[metric_key]), 'us', metadata))

  return (throughput_sample, latency_samples, latency_hist)


def EnableLatencyHistogram(num_streams, benchmark_name):
  enable_latency_histograms = FLAGS.intel_netperf_enable_histograms or num_streams > 1
  # Throughput benchmarks don't have latency histograms
  enable_latency_histograms = enable_latency_histograms and \
      benchmark_name != 'TCP_STREAM'
  return enable_latency_histograms


def RunNetperf(vm, benchmark_name, server_ip, num_streams, port_start):
  """Spawns netperf on a remote VM, parses results.

  Args:
    vm: The VM that the netperf TCP_RR benchmark will be run upon.
    benchmark_name: The netperf benchmark to run, see the documentation.
    server_ip: A machine that is running netserver.
    num_streams: The number of netperf client threads to run.

  Returns:
    A sample.Sample object with the result.
  """
  enable_latency_histograms = EnableLatencyHistogram(num_streams, benchmark_name)
  # Flags:
  # -o specifies keys to include in CSV output.
  # -j keeps additional latency numbers
  # -v sets the verbosity level so that netperf will print out histograms
  # -I specifies the confidence % and width - here 99% confidence that the true
  #    value is within +/- 2.5% of the reported value
  # -i specifies the maximum and minimum number of iterations.
  # -r set the request and/or response sizes based on sizespec.
  confidence = ('-I 99,5 -i {0},3'.format(FLAGS.intel_netperf_max_iter)
                if FLAGS.intel_netperf_max_iter else '')
  verbosity = '-v2 ' if enable_latency_histograms else ''
  netperf_cmd = ('{netperf_path} -p {{command_port}} -j {verbosity} '
                 '-t {benchmark_name} -H {server_ip} -l {length} {confidence}'
                 ' -- '
                 '-P ,{{data_port}} '
                 '-o {output_selector}').format(
                     netperf_path=netperf.NETPERF_PATH,
                     benchmark_name=benchmark_name,
                     server_ip=server_ip,
                     length=FLAGS.intel_netperf_test_length,
                     output_selector=OUTPUT_SELECTOR,
                     confidence=confidence, verbosity=verbosity)
  if benchmark_name != 'TCP_STREAM':
    netperf_cmd += ' -r {request_size},{response_size}'.format(request_size=FLAGS.intel_netperf_request_bytes,
                                                               response_size=FLAGS.intel_netperf_response_bytes)
  if FLAGS.intel_netperf_thinktime != 0:
    netperf_cmd += (' -X {thinktime},{thinktime_array_size},'
                    '{thinktime_run_length} ').format(
                        thinktime=FLAGS.intel_netperf_thinktime,
                        thinktime_array_size=FLAGS.intel_netperf_thinktime_array_size,
                        thinktime_run_length=FLAGS.intel_netperf_thinktime_run_length)

  # Run all of the netperf processes and collect their stdout
  # TODO(dlott): Analyze process start delta of netperf processes on the remote
  #              machine

  # Give the remote script the max possible test length plus 5 minutes to
  # complete
  remote_cmd_timeout = \
      FLAGS.intel_netperf_test_length * (FLAGS.intel_netperf_max_iter or 1) + 300
  remote_cmd = ('./%s --netperf_cmd="%s" --num_streams=%s --port_start=%s' %
                (REMOTE_SCRIPT, netperf_cmd, num_streams, port_start))
  try:
    remote_stdout, _ = vm.RemoteCommand(remote_cmd,
                                        timeout=remote_cmd_timeout)
  except errors.VirtualMachine.RemoteCommandError as e:
    logging.error("Caught remote command error, but will continue: " + str(e))
    return []

  # Decode stdouts, stderrs, and return codes from remote command's stdout
  json_out = json.loads(remote_stdout)
  stdouts = json_out[0]
  return stdouts


def ParseAllClientStdouts(stdouts, num_clients, num_streams, benchmark_name):
  enable_latency_histograms = EnableLatencyHistogram(num_streams, benchmark_name)
  # Metadata to attach to samples
  metadata = {'netperf_test_length': FLAGS.intel_netperf_test_length,
              'max_iter': FLAGS.intel_netperf_max_iter or 1,
              'sending_thread_count': num_streams,
              'num_client_vms': num_clients}
  if benchmark_name != 'TCP_STREAM':
    metadata.update({
        'request_size': FLAGS.intel_netperf_request_bytes,
        'response_size': FLAGS.intel_netperf_response_bytes
    })

  parsed_output = []
  for stdout in stdouts:
    out = ParseNetperfOutput(stdout, metadata, benchmark_name,
                             enable_latency_histograms)
    if out:
      parsed_output.append(out)

  if len(parsed_output) == 1:
    # Only 1 netperf thread
    throughput_sample, latency_samples, histogram = parsed_output[0]
    return [throughput_sample] + latency_samples
  else:
    # Multiple netperf threads

    samples = []

    # Unzip parsed output
    # Note that latency_samples are invalid with multiple threads because stats
    # are computed per-thread by netperf, so we don't use them here.
    throughput_samples, _, latency_histograms = [list(t)
                                                 for t in zip(*parsed_output)]
    # They should all have the same units
    throughput_unit = throughput_samples[0].unit
    # Extract the throughput values from the samples
    throughputs = [s.value for s in throughput_samples]
    # Compute some stats on the throughput values
    throughput_stats = sample.PercentileCalculator(throughputs, [50, 90, 99])
    throughput_stats['min'] = min(throughputs)
    throughput_stats['max'] = max(throughputs)
    # Calculate aggregate throughput
    throughput_stats['total'] = throughput_stats['average'] * len(throughputs)
    # Create samples for throughput stats
    for stat, value in throughput_stats.items():
      samples.append(
          sample.Sample('%s_Throughput_%s' % (benchmark_name, stat),
                        float(value),
                        throughput_unit, metadata))
    if enable_latency_histograms:
      # Combine all of the latency histogram dictionaries
      latency_histogram = collections.Counter()
      for histogram in latency_histograms:
        latency_histogram.update(histogram)
      # Create a sample for the aggregate latency histogram
      hist_metadata = {'histogram': json.dumps(latency_histogram)}
      hist_metadata.update(metadata)
      samples.append(sample.Sample(
          '%s_Latency_Histogram' % benchmark_name, 0, 'us', hist_metadata))
      # Calculate stats on aggregate latency histogram
      latency_stats = _HistogramStatsCalculator(latency_histogram, [50, 90, 99])
      # Create samples for the latency stats
      for stat, value in latency_stats.items():
        samples.append(
            sample.Sample('%s_Latency_%s' % (benchmark_name, stat),
                          float(value),
                          'us', metadata))
    return samples


def Run(benchmark_spec):
  """Run netperf TCP_RR on the target vm.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.

  Returns:
    A list of sample.Sample objects.
  """
  server_vm = benchmark_spec.vm_groups['workers'][0]
  client_vms = benchmark_spec.vm_groups['clients']

  results = []
  metadata = {
      'sending_zone': client_vms[0].zone,
      'sending_machine_type': client_vms[0].machine_type,
      'receiving_zone': server_vm.zone,
      'receiving_machine_type': server_vm.machine_type
  }

  def _Run(ip_address, benchmark_name, num_client_vms, streams_per_client):
    stdouts = []
    args = [((client_vms[i], benchmark_name, ip_address,
            streams_per_client, PORT_START + (i * 2 * streams_per_client)), {})
            for i in range(0, num_client_vms)]
    clients_stdouts = vm_util.RunThreaded(RunNetperf, args)
    # combine results from client vms
    for client_stdouts in clients_stdouts:
      stdouts.extend(client_stdouts)
    parsed_results = ParseAllClientStdouts(stdouts, num_client_vms, num_streams, benchmark_name)
    for result in parsed_results:
      result.metadata['ip_type'] = 'external' if ip_address == server_vm.ip_address else 'internal'
      result.metadata.update(metadata)
    return parsed_results

  for num_client_vms in FLAGS.intel_netperf_client_vms:
    assert(num_client_vms >= 1)
    for num_streams in FLAGS.intel_netperf_num_streams:
      assert(num_streams >= 1)
      num_streams_per_client = num_streams / num_client_vms
      if num_streams % num_client_vms != 0:
        logging.warn('netperf_num_streams not evenly divisible by netperf_client_vms. '
                     '%d streams will not be assigned. Each client vm will be allocated '
                     '%d streams.' % (num_streams % num_client_vms, num_streams_per_client))
      for netperf_benchmark in FLAGS.intel_netperf_benchmarks:
        if vm_util.ShouldRunOnExternalIpAddress():
          results.extend(_Run(server_vm.ip_address, netperf_benchmark, num_client_vms, num_streams_per_client))
        if vm_util.ShouldRunOnInternalIpAddress(client_vms[0], server_vm):
          results.extend(_Run(server_vm.internal_ip, netperf_benchmark, num_client_vms, num_streams_per_client))
  return results


def Cleanup(benchmark_spec):
  """Cleanup netperf on the target vm (by uninstalling).

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  server_vm = benchmark_spec.vm_groups['workers'][0]
  client_vms = benchmark_spec.vm_groups['clients']
  server_vm.RemoteCommand('sudo killall netserver')
  for vm in client_vms:
    vm.RemoteCommand('sudo rm -rf %s' % REMOTE_SCRIPT)
