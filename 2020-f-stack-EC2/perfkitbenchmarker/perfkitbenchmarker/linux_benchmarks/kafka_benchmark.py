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

"""Runs Kafka benchmark.
"""

import logging
import re
from six import StringIO
import time
import math
import functools
import itertools
import sys
import copy
import os

from itertools import repeat
from perfkitbenchmarker import configs
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import flag_util
from perfkitbenchmarker import autoscale_util
from absl import flags
from perfkitbenchmarker import sample
from perfkitbenchmarker.linux_packages import kafka
from perfkitbenchmarker.linux_packages import zookeeper
from perfkitbenchmarker.linux_packages import INSTALL_DIR

FLAGS = flags.FLAGS

# producer flags
flags.DEFINE_integer('kafka_producer_vms', 1,
                     'The number of vms for producer.', lower_bound=1)
flags.DEFINE_integer('kafka_producer_records_per_client', 3000000,
                     'The number of records each client will send.', lower_bound=1)
# https://kafka.apache.org/documentation/#producerconfigs
flags.DEFINE_integer('kafka_producer_buffer_memory', None,
                     'The total bytes of memory the producer can use to buffer records.',
                     lower_bound=0)
flags.DEFINE_integer('kafka_producer_tps', 50000,
                     'The desired throughput in records per second for a single producer.',
                     lower_bound=-1)
flags.DEFINE_integer('kafka_producer_batch_size', None,
                     'The batch size in bytes.',
                     lower_bound=0)
flags.DEFINE_integer('kafka_producer_wait_time', None,
                     'The producer wait time in ms.',
                     lower_bound=0)
flags.DEFINE_integer('kafka_producer_acks', None,
                     'The number of acknowledgements required by the producer.',
                     lower_bound=-1, upper_bound=1)
flags.DEFINE_boolean('kafka_producer_compress', False,
                     'Enable compression on full batches of data.')
# consumer flags
flags.DEFINE_integer('kafka_consumer_vms', 1,
                     'The number of vms for consumer.', lower_bound=1)
flags.DEFINE_integer('kafka_consumer_fetch_size', None,
                     'The amount of data to fetch in a single request.')
flags.DEFINE_integer('kafka_consumer_fetch_threads', None,
                     'Number of fetcher threads.')
flags.DEFINE_integer('kafka_consumer_processing_threads', None,
                     'Number of processing threads')
flags.DEFINE_integer('kafka_consumer_records_per_client', 3000000,
                     'The number of messages to consume',
                     lower_bound=0)
# cluster configuration flags
flags.DEFINE_integer('kafka_broker_vms', 1,
                     'The number of Kafka broker vms.', lower_bound=1)
flags.DEFINE_integer('kafka_brokers_per_vm', 1,
                     'The number of brokers to run on each Kafka server vm.', lower_bound=1)
flags.DEFINE_boolean('kafka_enable_encryption', False,
                     'Enable encryption and authentication with SSL.')
# kafka topic flags
flags.DEFINE_integer('kafka_topic_replication_factor', 1,
                     'Topic replication factor.', lower_bound=1)
flags.DEFINE_integer('kafka_topic_num_partitions', 2,
                     'Number of partitions for topic.', lower_bound=1)
flags.DEFINE_integer('kafka_record_size', 1000,
                     'The size of each record.', lower_bound=1)
# autoscaling flags
flags.DEFINE_integer('kafka_num_partitions_min', 1,
                     'The minimum number of partitions.', lower_bound=1)
flags.DEFINE_integer('kafka_p95_latency', 5,
                     'p95 latency target for kafka autoscaling mode.', lower_bound=0)

KAFKA_BENCHMARK_TOPIC = "PKBBENCHMARK"
KAFKA_CONSUMER_GROUP_ID = "PKB_CONSUMER_GROUP"

BENCHMARK_NAME = 'kafka'
BENCHMARK_CONFIG = """
kafka:
  description: Kafka benchmark.
  vm_groups:
    brokers:
      os_type: ubuntu1804
      vm_spec: *default_dual_core
      disk_spec: *default_50_gb
    producers:
      os_type: ubuntu1804
      vm_spec: *default_dual_core
    consumers:
      os_type: ubuntu1804
      vm_spec: *default_dual_core
"""

KEYSTORE_FILENAME = 'kafka.server.keystore.jks'
TRUSTSTORE_FILENAME = 'kafka.server.truststore.jks'
CLIENT_TRUSTSTORE_FILENAME = 'kafka.client.truststore.jks'
CLIENT_PROPERTIES_FILENAME = 'client-ssl.properties'


def GetConfig(user_config):
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
  if FLAGS['kafka_producer_vms'].present:
    config['vm_groups']['producers']['vm_count'] = FLAGS.kafka_producer_vms
  if FLAGS['kafka_consumer_vms'].present:
    config['vm_groups']['consumers']['vm_count'] = FLAGS.kafka_consumer_vms
  if FLAGS['kafka_broker_vms'].present:
    config['vm_groups']['brokers']['vm_count'] = FLAGS.kafka_broker_vms
  return config


def _PrepareClient(vm):
  vm.Install('kafka')
  if FLAGS.kafka_enable_encryption:
    vm.PushDataFile('kafka/' + CLIENT_TRUSTSTORE_FILENAME, kafka.CONF_DIR)
    vm.PushDataFile('kafka/' + CLIENT_PROPERTIES_FILENAME, kafka.CONF_DIR)
    client_config = {'security.protocol': 'SSL',
                     'ssl.truststore.location': '{0}/{1}'.format(kafka.CONF_DIR, CLIENT_TRUSTSTORE_FILENAME),
                     'ssl.truststore.password': 'test1234',
                     'ssl.endpoint.identification.algorithm': ''}
    for key, value in client_config.items():
      vm.RemoteCommand(r"sed -i -e '$a{0}={1}' {2}/{3}".format(key, value, kafka.CONF_DIR, CLIENT_PROPERTIES_FILENAME))


def _PrepareBroker(vm, benchmark_spec, vm_index, server_number):
  vm.Install('kafka')
  zk_index = vm_index % (len(benchmark_spec.vm_groups['brokers']))
  zk_server, zk_port = _GetZookeeperServer(benchmark_spec, zk_index)
  log_dir = (benchmark_spec.vm_groups['brokers'][vm_index].disk_specs[0].mount_point).replace(r"/", r"\/")
  extra_config = {}
  encrypt = False
  if FLAGS.kafka_enable_encryption:
    vm.PushDataFile('kafka/' + KEYSTORE_FILENAME, kafka.CONF_DIR)
    vm.PushDataFile('kafka/' + TRUSTSTORE_FILENAME, kafka.CONF_DIR)
    extra_config = {'ssl.keystore.location': '{0}/{1}'.format(kafka.CONF_DIR, KEYSTORE_FILENAME),
                    'ssl.keystore.password': 'test1234',
                    'ssl.key.password': 'test1234',
                    'ssl.truststore.location': '{0}/{1}'.format(kafka.CONF_DIR, TRUSTSTORE_FILENAME),
                    'ssl.truststore.password': 'test1234',
                    'security.inter.broker.protocol': 'SSL',
                    'ssl.endpoint.identification.algorithm': '',
                    'ssl.truststore.type': 'pkcs12',
                    'ssl.client.auth': 'none'}
    encrypt = True
  config = {'broker.id': '{0}{1}'.format(vm_index + 1, server_number),
            'zookeeper.connect': '{0}:{1}'.format(zk_server, zk_port),
            'log.dirs': r'{0}\/kafka\/{1}'.format(log_dir, server_number)}
  kafka.Configure(vm, server_number, config, kafka.DEFAULT_PORT + (10000 * server_number), autoscale_util.GetInternalIpAddresses(vm), extra_config, encrypt)
  kafka.Start(vm, server_number)


def _PrepareZookeeper(zk_vm, benchmark_spec, vm_index):
  zk_vm.Install('zookeeper')
  config = {}
  for idx, vm in enumerate(benchmark_spec.vm_groups['brokers']):
    key = 'server.{0}'.format(idx)
    value = '{0}:{1}:{2}'.format(vm.internal_ip, zookeeper.LEADER_PORT,
                                 zookeeper.ELECTION_PORT)
    config[key] = value
  zookeeper.Configure(zk_vm, vm_index, config)
  zookeeper.Start(zk_vm)


# Example:
# bin/kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 3
# --partitions 1 --topic my-replicated-topic
def _CreateKafkaTopic(benchmark_spec, topic, num_partitions):
  logging.info('Creating a Kafka topic')
  run_cmd_tokens = ['%s/bin/kafka-topics.sh --create' % kafka.KAFKA_DIR,
                    '--zookeeper %s:%d' % (_GetZookeeperServer(benchmark_spec, 0)),
                    '--topic %s' % topic,
                    '--replication-factor %d' % FLAGS.kafka_topic_replication_factor,
                    '--partitions %d' % num_partitions,
                    ]
  run_cmd = ' '.join(run_cmd_tokens)
  # run this from one of the client VMs
  vm = benchmark_spec.vm_groups['producers'][0]
  stdout, _ = vm.RemoteCommand(run_cmd)
  logging.info('Created topic output:\n{0}'.format(stdout))


def _DeleteKafkaTopic(benchmark_spec, topic):
  logging.info('Deleting Kafka topic')
  run_cmd_tokens = ['%s/bin/kafka-topics.sh --delete' % kafka.KAFKA_DIR,
                    '--zookeeper %s:%d' % (_GetZookeeperServer(benchmark_spec, 0)),
                    '--topic %s' % topic,
                    ]
  run_cmd = ' '.join(run_cmd_tokens)
  vm = benchmark_spec.vm_groups['producers'][0]
  stdout, _ = vm.RemoteCommand(run_cmd)
  logging.info('Deleted topic output:\n{0}'.format(stdout))


def _WaitUntilStarted(benchmark_spec):
  num_tries = 10
  # wait a few seconds after starting Kafka server before topic creation
  time.sleep(5)
  for _ in range(num_tries):
    try:
      _CreateKafkaTopic(benchmark_spec, 'waittopic', FLAGS.kafka_topic_num_partitions)
      return
    except Exception as e:
      logging.info("Failed to create test topic: %s" % e.message)
  raise Exception("Unable to create test topic after"
                  " %d tries while waiting for brokers to start" % num_tries)


def Prepare(benchmark_spec):
  """Prepare the client test VM, installs kafka and dependencies.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  benchmark_spec.always_call_cleanup = True

  # zookeeper
  zookeeper_partials = [functools.partial(_PrepareZookeeper, vm, benchmark_spec, index)
                        for index, vm in enumerate(benchmark_spec.vm_groups['brokers'])]

  # producers and consumers
  merged_clients = benchmark_spec.vm_groups['producers'] + benchmark_spec.vm_groups['consumers']
  client_partials = [functools.partial(_PrepareClient, vm)
                     for vm in merged_clients]

  vm_util.RunThreaded((lambda f: f()), client_partials + zookeeper_partials)

  # kafka brokers
  kafka_partials = [functools.partial(_PrepareBroker, kafka_vm,
                                      benchmark_spec, vm_index, svr_number)
                    for vm_index, kafka_vm in enumerate(benchmark_spec.vm_groups['brokers'])
                    for svr_number in range(FLAGS.kafka_brokers_per_vm)]
  vm_util.RunThreaded((lambda f: f()), kafka_partials)

  # wait for kafka brokers to start, will throw exception on failure
  _WaitUntilStarted(benchmark_spec)


def _GetBootstrapServer(benchmark_spec, producer_idx):
  # Not sure this is what we want when we have more than one broker,
  # but we'll go with it for now.
  vm = benchmark_spec.vm_groups['brokers'][0]
  internal_ips = autoscale_util.GetInternalIpAddresses(vm)
  selected_ip = internal_ips[producer_idx % len(internal_ips)]
  return selected_ip, kafka.DEFAULT_PORT + (producer_idx % len(internal_ips))


def _GetServerList(benchmark_spec, consumer_idx):
  servers = []
  for vm in benchmark_spec.vm_groups['brokers']:
    for i in range(FLAGS.kafka_brokers_per_vm):
      internal_ips = autoscale_util.GetInternalIpAddresses(vm)
      selected_ip = internal_ips[consumer_idx % len(internal_ips)]
      servers.append((selected_ip, kafka.DEFAULT_PORT + (i * 10000) + (consumer_idx % len(internal_ips))))
  return servers


def _GetServerListAsString(benchmark_spec, consumer_idx):
  result = ""
  servers = _GetServerList(benchmark_spec, consumer_idx)
  for server in servers:
    result += '%s:%d ' % (server[0], server[1])
  return result


def _GetZookeeperServer(benchmark_spec, zk_index):
  vm = benchmark_spec.vm_groups['brokers'][zk_index]
  return vm.internal_ip, zookeeper.DEFAULT_PORT


def _CreateMetadataFromFlags():
  """Create meta data with all flags for kafka."""
  metadata = {
      'kafka_producer_records_per_client': FLAGS.kafka_producer_records_per_client,
      'kafka_consumer_records_per_client': FLAGS.kafka_consumer_records_per_client,
  }
  return metadata


def _GetProducerPerfCommand(benchmark_spec, producer_idx):
  # Example Producer:
  # bin/kafka-producer-perf-test.sh
  # --topic test --num-records 5000 --throughput -1
  # --record-size 100 --producer-props bootstrap.servers=localhost:9092
  # buffer.memory=67108864 batch.size=8196
  producer_cmd_tokens = ['%s/bin/kafka-producer-perf-test.sh' % kafka.KAFKA_DIR,
                         '--topic %s' % KAFKA_BENCHMARK_TOPIC,
                         '--num-records %d' % FLAGS.kafka_producer_records_per_client,
                         '--record-size %d' % FLAGS.kafka_record_size,
                         '--throughput %d' % FLAGS.kafka_producer_tps,
                         '--producer-props']
  producer_cmd_tokens.append('bootstrap.servers=%s:%d' % (_GetBootstrapServer(benchmark_spec, producer_idx)))
  if FLAGS.kafka_producer_buffer_memory:
    producer_cmd_tokens.append('buffer.memory=%d' % FLAGS.kafka_producer_buffer_memory)
  if FLAGS.kafka_producer_batch_size:
    producer_cmd_tokens.append('batch.size=%d' % FLAGS.kafka_producer_batch_size)
  if FLAGS.kafka_producer_wait_time:
    producer_cmd_tokens.append('linger.ms=%d' % FLAGS.kafka_producer_wait_time)
  if FLAGS.kafka_producer_acks:
    producer_cmd_tokens.append('acks=%d' % FLAGS.kafka_producer_acks)
  if FLAGS.kafka_producer_compress:
    producer_cmd_tokens.append('compression.type=lz4')
  if FLAGS.kafka_enable_encryption:
    producer_cmd_tokens.append('--producer.config %s/client-ssl.properties' % kafka.CONF_DIR)
  producer_cmd = ' '.join(producer_cmd_tokens)
  return producer_cmd


def _GetConsumerPerfCommand(benchmark_spec, consumer_idx):
  # Example Consumer:
  # bin/kafka-consumer-perf-test.sh
  # --messages 50000000 --topic test --threads 1
  # --broker-list localhost:9092
  consumer_cmd_tokens = ['%s/bin/kafka-consumer-perf-test.sh' % kafka.KAFKA_DIR,
                         '--topic %s' % KAFKA_BENCHMARK_TOPIC,
                         '--messages %d' % FLAGS.kafka_consumer_records_per_client,
                         '--broker-list %s' % (_GetServerListAsString(benchmark_spec, consumer_idx)),
                         '--group %s' % KAFKA_CONSUMER_GROUP_ID]
  if FLAGS.kafka_consumer_processing_threads:
    consumer_cmd_tokens.append('--threads %d' % FLAGS.kafka_consumer_processing_threads)
  if FLAGS.kafka_consumer_fetch_size:
    consumer_cmd_tokens.append('--fetch-size %d' % FLAGS.kafka_consumer_fetch_size)
  if FLAGS.kafka_consumer_fetch_threads:
    consumer_cmd_tokens.append('--num-fetch-threads %d' % FLAGS.kafka_consumer_fetch_threads)
  if FLAGS.kafka_enable_encryption:
    consumer_cmd_tokens.append('--consumer.config %s/client-ssl.properties' % kafka.CONF_DIR)
  consumer_cmd = ' '.join(consumer_cmd_tokens)
  return consumer_cmd


def _RunAndParseResults(vm, cmd, client_results, metadata):
  stdout, stderr = vm.RobustRemoteCommand(cmd)
  # global producer_results
  results = _ParseResults(stdout, stderr, metadata)
  client_results.extend(results)


def _RunProducer(vm, producer_idx, benchmark_spec, metadata, producer_results):
  producer_cmd = _GetProducerPerfCommand(benchmark_spec, producer_idx)
  _RunAndParseResults(vm, producer_cmd, producer_results, metadata)


def _RunConsumer(vm, consumer_idx, benchmark_spec, metadata, consumer_results):
  consumer_cmd = _GetConsumerPerfCommand(benchmark_spec, consumer_idx)
  _RunAndParseResults(vm, consumer_cmd, consumer_results, metadata)


def _ParseResults(stdout, stderr, metadata):
  results = []
  output_io = StringIO(stdout)
  for line in output_io:
    # Example Producer Output:
    # 5000 records sent, 19920.318725 records/sec (1.90 MB/sec), 18.94 ms avg latency,
    # 115.00 ms max latency, 16 ms 50th, 39 ms 95th, 40 ms 99th, 41 ms 99.9th.
    match = re.search(r'^(\d+) records sent, (\d*\.?\d+) records/sec .(\d*.?\d+) MB/sec., (\d*.?\d+) ms avg latency, (\d*.?\d+) ms max latency, (\d*.?\d+) ms 50th, (\d*.?\d+) ms 95th, (\d*.?\d+) ms 99th, (\d*.?\d+) ms 99.9th', line)
    if match:
      try:
        records_sent = float(match.group(1))
        records_per_second = float(match.group(2))
        megabytes_per_second = float(match.group(3))
        average_latency = float(match.group(4))
        max_latency = float(match.group(5))
        fiftieth_latency = float(match.group(6))
        ninetyfifth_latency = float(match.group(7))
        ninetyninth_latency = float(match.group(8))
        ninetyninepointnine_latency = float(match.group(9))
      except ValueError:
        logging.error("Parsing error -- type conversion failed")
        raise
      results.append(sample.Sample("tx records", records_sent, 'records', metadata))
      results.append(sample.Sample("tx records per second", records_per_second, 'rec/s', metadata))
      results.append(sample.Sample("tx megabytes per second", megabytes_per_second, 'MB/s',
                                   metadata))
      results.append(sample.Sample("tx latency average", average_latency, 'ms',
                                   metadata))
      results.append(sample.Sample("tx latency max", max_latency, 'ms', metadata))
      results.append(sample.Sample("tx latency 50th percentile", fiftieth_latency, 'ms', metadata))
      results.append(sample.Sample("tx latency 95th percentile", ninetyfifth_latency, 'ms',
                                   metadata))
      results.append(sample.Sample("tx latency 99th percentile", ninetyninth_latency, 'ms',
                                   metadata))
      results.append(sample.Sample("tx latency 99.9th percentile", ninetyninepointnine_latency, 'ms',
                                   metadata))
      break
    # Example Consumer Output:
    # start.time, end.time, data.consumed.in.MB, MB.sec, data.consumed.in.nMsg, nMsg.sec,
    # rebalance.time.ms, fetch.time.ms, fetch.MB.sec, fetch.nMsg.sec
    # 2018-08-13 22:11:19:613, 2018-08-13 22:11:20:429, 47.6837, 58.4359, 500000,
    # 612745.0980, 36, 780, 61.1330, 641025.6410
    match = re.search(r'(\d+\.\d+), (\d+\.\d+), (\d+), (\d+\.\d+), (\d+), (\d+), (\d+\.\d+), (\d+\.\d+)', line)
    if match:
      try:
        megabytes_received = float(match.group(1))
        megabytes_per_second = float(match.group(2))
        records_received = float(match.group(3))
        records_per_second = float(match.group(4))
      except ValueError:
        logging.error("Parsing error -- type conversion failed")
        raise
      results.append(sample.Sample("rx megabytes", megabytes_received, 'MB', metadata))
      results.append(sample.Sample("rx megabytes per second", megabytes_per_second, 'MB/s',
                                   metadata))
      results.append(sample.Sample("rx records", records_received, 'records', metadata))
      results.append(sample.Sample("rx records per second", records_per_second, 'records/s',
                                   metadata))
      break
  logging.debug("_ParseResults returning {0} samples".format(len(results)))
  return results


def _GetThroughputFromResults(results, metric_string):
  throughput = 0
  for _sample in results:
    if _sample.metric == metric_string:
      throughput += _sample.value
  return throughput


def _GetMaxFromResults(results, metric_string):
  Max = 0
  for _sample in results:
    if _sample.metric == metric_string:
      if Max < _sample.value:
        Max = _sample.value
  return Max


def _GetVirtualVms(client_process_count, client_vms):
  """ Get a list of virtual VMs on wich to execute client processes. When the
      client process count is larger than the number of VMs available,
      physical VMs are duplicated (will appear in resulting list more than
      once).
  """
  duplicate = int(math.ceil(client_process_count / float(len(client_vms))))
  virtual_vms = [
      vm for item in client_vms for vm in repeat(item, duplicate)][:client_process_count]
  return virtual_vms


def _MeetsExitCriteria(samples):
  throughputs = [s.value for s in samples if s.metric == "tx aggregate megabytes per second"]
  return autoscale_util.MeetsExitCriteria(throughputs)


def _GetMaxThroughputSample(samples, metadata):
  max_value = max([s.value for s in samples if s.metric == "tx aggregate megabytes per second"])
  for s in samples:
    if s.metric == "tx aggregate megabytes per second" and s.value == max_value:
      p95 = s.metadata['max p95 tx latency']
      break
  md = copy.deepcopy(metadata)
  md['max p95 tx latency'] = p95
  return sample.Sample("Maximum Throughput", max_value, 'MB/s', md)


def _GetMaxThroughputForLatencySLA(samples, metadata):
  throughputs_under_sla = [s.value for s in samples if s.metric == "tx aggregate megabytes per second" and s.metadata['max p95 tx latency'] < FLAGS.kafka_p95_latency]
  if throughputs_under_sla:
    max_value = max(throughputs_under_sla)
    for s in samples:
      if s.metric == "tx aggregate megabytes per second" and s.value == max_value:
        p95 = s.metadata['max p95 tx latency']
        break
  else:
    p95 = 0
    max_value = 0
  md = metadata.copy()
  md['max p95 tx latency'] = p95
  return sample.Sample("Maximum Throughput for Latency SLA", max_value, 'MB/s', md)


def Run(benchmark_spec):
  """Run the Kafka benchmark and publish results.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.

  Returns:
    Results.
  """
  num_partitions = FLAGS.kafka_num_partitions_min
  iteration_count = 1
  results = []
  while True:
    # At every iteration, start with an empty list to collect results
    consumer_results = []
    producer_results = []
    aggregate_results = []

    # Topic deleted at end of each iteration, here we recreate topic for next iteration
    # retry up to 5 times
    num_tries = 5
    for _ in range(num_tries):
      try:
        logging.info("Attempting to create test topic.")
        _CreateKafkaTopic(benchmark_spec, KAFKA_BENCHMARK_TOPIC, num_partitions)
      except Exception:
        logging.info("Failed to create Kafka topic: retrying")
        time.sleep(5)
        continue
      break

    # producers
    kafka_producer_vms = _GetVirtualVms(num_partitions, benchmark_spec.vm_groups['producers'])
    producer_partials = [functools.partial(_RunProducer, vm, idx, benchmark_spec,
                                           _CreateMetadataFromFlags(), producer_results)
                         for idx, vm in enumerate(kafka_producer_vms)]
    # consumers
    kafka_consumer_vms = _GetVirtualVms(num_partitions, benchmark_spec.vm_groups['consumers'])
    consumer_partials = [functools.partial(_RunConsumer, vm, idx, benchmark_spec,
                                           _CreateMetadataFromFlags(), consumer_results)
                         for idx, vm in enumerate(kafka_consumer_vms)]
    # start producers and consumers
    vm_util.RunThreaded((lambda f: f()), producer_partials + consumer_partials)

    # Aggregate results from clients, then parse tx throughput and p95 latencies
    aggregate_results.extend(producer_results)
    aggregate_results.extend(consumer_results)
    throughput = _GetThroughputFromResults(aggregate_results, "tx megabytes per second")
    p95 = _GetMaxFromResults(aggregate_results, "tx latency 95th percentile")
    logging.info('tx aggregate megabytes per second: {0}  at iteration: {1} \n'
                 .format(throughput, iteration_count))
    logging.info('Max tx latency 95th percentile: {0} at iteration: {1} \n'
                 .format(p95, iteration_count))
    metadata = {
        'num_producers': num_partitions,
        'num_consumers': num_partitions,
        'kafka version': kafka.KAFKA_ROOT,
        'max p95 tx latency': p95
    }
    results.append(sample.Sample("tx aggregate megabytes per second",
                                 throughput, 'MB/s', metadata))
    # At every iteration, delete existing topic and recreate to update partitions
    _DeleteKafkaTopic(benchmark_spec, KAFKA_BENCHMARK_TOPIC)
    # are we done?
    if _MeetsExitCriteria(results):
      logging.info("Exit criteria met.")
      break
    iteration_count += 1
    num_partitions += 1
  metadata = {
      'num_producers': num_partitions,
      'num_consumers': num_partitions,
      'kafka version': kafka.KAFKA_ROOT,
  }
  results.append(_GetMaxThroughputSample(results, metadata))
  results.append(_GetMaxThroughputForLatencySLA(results, metadata))
  return results


def _CleanupServer(vm):
  """Stops and uninstalls Zookeeper and Kafka on the brokers."""
  zookeeper.Stop(vm)
  kafka.Stop(vm)
  vm.Uninstall('zookeeper')
  vm.Uninstall('kafka')


def _CleanupClient(vm):
  """Stops and uninstalls Kafka on the clients."""
  vm.Uninstall('kafka')


def Cleanup(benchmark_spec):
  """Clean up Sysbench CPU benchmark related states.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  server_partials = [functools.partial(_CleanupServer, kafka_vm)
                     for kafka_vm in benchmark_spec.vm_groups['brokers']]
  vm_util.RunThreaded((lambda f: f()), server_partials)

  kafka_partials = [functools.partial(kafka.DeleteLogFile, kafka_vm,
                                      benchmark_spec, vm_index)
                    for vm_index, kafka_vm in enumerate(benchmark_spec.vm_groups['brokers'])]
  vm_util.RunThreaded((lambda f: f()), kafka_partials)

  client_partials = [functools.partial(_CleanupClient, client)
                     for client in benchmark_spec.vm_groups['consumers']]
  vm_util.RunThreaded((lambda f: f()), client_partials)

  client_partials = [functools.partial(_CleanupClient, client)
                     for client in benchmark_spec.vm_groups['producers']]
  vm_util.RunThreaded((lambda f: f()), client_partials)
