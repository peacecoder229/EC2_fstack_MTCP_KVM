import os
import sys
import pickle
import json
import logging
import tarfile
import time
import uuid
import fcntl
import copy
import subprocess
import csv
if __name__ == '__main__':
  sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import publisher
from perfkitbenchmarker import events
from absl import flags
from perfkitbenchmarker import version
from perfkitbenchmarker import errors

FLAGS = flags.FLAGS

INTEL_PUBLISHER_DIR = 'intel_kafka_publisher'
DEFAULT_RESULTS_JSON_FILENAME = 'results.json'
DEFAULT_PLATFORMS_JSON_FILENAME = 'platforms.json'
KAFKA_HTTP_REQUEST_SIZE = 10485760  # 10MB
COLLECTD_MAX_RECORDS_PER_SEND = 100000
DEFAULT_RESULTS_TOPIC = 'pkb.publisher'
DEFAULT_PLATFORMS_TOPIC = 'pkb.platforms'

flags.DEFINE_string('intel_publisher_run_dir', None,
                    'Path to a perfkitbenchmarker run directory. '
                    'Contents will be published if used with --kafka_publish.')
flags.DEFINE_string('kafka_proxy_uri', None,
                    'Name of Kafka REST proxy address where you want to publish e.g https://localhost:8082')
flags.DEFINE_string('kafka_brokers', '10.114.164.85:9092,10.114.164.87:9092,10.114.164.89:9092',
                    'A comma-separated list of kafka brokers in hostname:port format.')
flags.DEFINE_boolean('kafka_publish', False,
                     'Enable publishing of results/telemetry to Kafka HTTPS or broker endpoints')
flags.DEFINE_boolean('kafka_proxy_publish', False,
                     'Enable publishing of results/telemetry to Confluent Kafka HTTPS Proxy endpoints')
flags.DEFINE_string('kafka_ssl_key_path', None,
                    'Path for SSL certificates if SSL is used with Kafka brokers. '
                    'Expects a directory containing ca.crt, kafka.crt, and kafka.key')
flags.DEFINE_string('intel_kafka_publisher_s3_archive_bucket_url',
                    'https://d15e4ftowigvkb.cloudfront.net',
                    'URL of bucket to save run directory archive. This bucket must '
                    'allow anonymous upload from the PKB host.')


class PkbRunDirParseErrorException(Exception):
  pass


def Register():
  logging.info("Registering Intel Publisher.")
  intel_publisher = IntelPublisher()
  events.before_phase.connect(intel_publisher.CacheVmInfo, events.RUN_PHASE, weak=False)
  events.samples_created.connect(intel_publisher.AddSamples, events.RUN_PHASE, weak=False)
  events.benchmark_end.connect(intel_publisher.PrepareAndPublish, weak=False)


class IntelPublisher:

  def __init__(self):
    self.collected_samples = []
    self.s3_archive_filename = None
    self.svrinfo = None
    self.collectd = None
    self.samples = []
    self.temp_dir = None

  def AddSamples(self, unused_sender, benchmark_spec, samples):
      self.collected_samples.extend(samples)

  def PrepareAndPublish(self, sender_event, benchmark_spec):
    if not self.collected_samples:
      logging.info("No samples were collected, skipping publishing.")
      return
    self.temp_dir = vm_util.GetTempDir()
    if FLAGS.intel_kafka_publisher_s3_archive_bucket_url and FLAGS.kafka_publish:
      self.s3_archive_filename = _GetTimestampedFileName(benchmark_spec.name, benchmark_spec.uuid)
    try:
      if FLAGS.svrinfo:
        self.svrinfo = SvrInfo(benchmark_spec, self.temp_dir)
    except Exception as err:
      logging.error("Encountered exception '{}' while attempting parse svr_info.".format(err))
    if FLAGS.collectd:
      self.collectd = Collectd(benchmark_spec, FLAGS.collectd_output or self.temp_dir)
    self.samples = self._CreatePerfkitSamples(benchmark_spec)
    logging.info("Writing new line delimited JSON.")
    self._WriteNewlineDelimitedJson(self.samples)
    self.KafkaPublish()

  def KafkaPublish(self):

    def Send():
      SendKafka(DEFAULT_RESULTS_TOPIC, self.samples)
      if self.svrinfo:
        logging.info("Publishing Svrinfo.")
        self.svrinfo.KafkaPublish()
      if self.collectd:
        logging.info("Publishing Collectd.")
        self.collectd.KafkaPublish()

    if self.s3_archive_filename:
      logging.info("Publish Archive to S3: {}".format(self.s3_archive_filename))
      if self._ArchiveToS3(self.temp_dir, self.s3_archive_filename):
        for sample in self.samples:
          sample['metadata'].update({'s3_archive_url': os.path.join(FLAGS.intel_kafka_publisher_s3_archive_bucket_url,
                                                                    self.s3_archive_filename)})
        Send()
      else:
        logging.error("Pushing to S3 failed! Data was not sent to Kafka.")
    elif FLAGS.kafka_publish:
      Send()

  def _CreatePerfkitSamples(self, benchmark_spec):
    perfkit_samples = []
    platforms = self._CreatePlatformSamples(benchmark_spec)
    for s in copy.deepcopy(self.collected_samples):
      sample = dict(s.asdict())
      sample['test'] = benchmark_spec.name
      sample['owner'] = FLAGS.owner
      sample['perfkitbenchmarker_version'] = version.VERSION
      sample['run_uri'] = benchmark_spec.uuid
      sample['sample_uri'] = str(uuid.uuid4())
      sample['platforms'] = platforms
      if FLAGS.publish_config:
        sample['metadata'].update({'user_cmdline': " ".join(sys.argv[:])})
      sample['metadata'].update(benchmark_spec.software_config_metadata)
      sample['metadata'].update(benchmark_spec.tunable_parameters_metadata)
      perfkit_samples.append(sample)
    return perfkit_samples

  @staticmethod
  def _WriteNewlineDelimitedJson(samples):
    results_dir = os.path.join(vm_util.GetTempDir(), INTEL_PUBLISHER_DIR)
    vm_util.IssueCommand(['mkdir', '-p', results_dir])
    results_file = os.path.join(results_dir, DEFAULT_RESULTS_JSON_FILENAME)
    logging.info('Writing data samples to file: {}'.format(results_file))
    with open(results_file, 'a+') as fp:
      fcntl.flock(fp, fcntl.LOCK_EX)
      for sample in samples:
        sample = sample.copy()
        fp.write(json.dumps(sample) + '\n')

  @staticmethod
  def _ArchiveToS3(run_dir, filename):
    """Compresses run_dir into a tar.gz format and uploads to S3 bucket via curl.
    Args:
      run_dir: Full path to perfkitbenchmarker run directory.
      filename: Name for tarball.
    """
    tarball_name = filename
    temp_tar = os.path.join('/tmp', tarball_name)
    with tarfile.open(temp_tar, mode='w:gz') as tar:
      tar.add(run_dir, arcname=os.path.basename(run_dir))
    upload_cmd = ['curl', '-X', 'PUT', '-H', 'x-amz-acl: bucket-owner-full-control',
                  '-T', temp_tar, FLAGS.intel_kafka_publisher_s3_archive_bucket_url]
    logging.info("Uploading results to {}".format(os.path.join(FLAGS.intel_kafka_publisher_s3_archive_bucket_url,
                                                               tarball_name)))
    retry = 3
    success = False
    while retry > 0:
      p = subprocess.Popen(upload_cmd, stdout=subprocess.PIPE)
      status = p.wait()
      if status:
        retry -= 1
      else:
        success = True
        break
    os.unlink(temp_tar)
    return success

  def _CreatePlatformSamples(self, benchmark_spec):
    platforms = []
    for vm in benchmark_spec.vms:
      platform = {
          'vm_name': vm.name,
          'machine_type': vm.machine_type,
          'zone': vm.zone,
          'cloud': vm.CLOUD,
          'vm_group': benchmark_spec.GetVmGroupForVm(vm),
          'numa_node_count': vm.numa_node_count,
          'image': vm.image,
          'kernel_release': vm.kernel_release,
          'os_type': vm.OS_TYPE,
          'os_info': vm.os_info,
          'uid': benchmark_spec.uid,
          'run_uri': benchmark_spec.uuid,
          'test': benchmark_spec.name,
          'owner': FLAGS.owner
      }
      try:
        # These VM variables trigger remote commands if they are not cached.
        # We do not want them to cause the publisher to fail if they are not cached.
        lscpu = vm.CheckLsCpu().data
        platform['cpu_model'] = lscpu.get('Model name', None)
        platform['sockets'] = lscpu.get('Socket(s)', None)
        platform['num_cpus'] = vm.num_cpus
        platform['mem_info'] = "{:.2f} GB".format(vm.total_memory_kb / 1024 ** 2),
      except errors.VirtualMachine.RemoteCommandError:
        logging.warning("CPU/Mem info was not cached and cannot be retrieved. Skipping.")
      if self.svrinfo:
        vm_svrinfo = self.svrinfo.vm_json.get(platform['vm_name'], None)
        if vm_svrinfo:
          platform.update(self.svrinfo.FormatForPlatform(vm_svrinfo))
      platforms.append(platform)
    return platforms

  @staticmethod
  def CacheVmInfo(unused_sender, benchmark_spec):
    """Executes vm.CheckLsCpu(), total_memory_kb to ensure that vm cache is warmed."""
    for vm in benchmark_spec.vms:
      vm.CheckLsCpu()
      vm.total_memory_kb


class Collectd:

  def __init__(self, benchmark_spec, output_dir):
    self.benchmark_spec = benchmark_spec
    self.output_dir = output_dir

  def KafkaPublish(self):
    logging.info('Searching for collectd samples to publish.')
    topic = 'collectd'
    for vm in self.benchmark_spec.vms:
      local_dir = os.path.join(self.output_dir, vm.name + '-collectd')
      vm_group = self.benchmark_spec.GetVmGroupForVm(vm)
      for docs in self._CsvToKafkaDoc(local_dir, self.benchmark_spec.uuid, self.benchmark_spec.name, vm.name, vm_group):
        SendKafka(topic, docs)

  def _CsvToKafkaDoc(self, path, run_uri, benchmark_name, vm_name, vm_group):
    logging.info("Parsing CSV files for uploading to Kafka")
    parse_error_count = 0
    docs = []
    for (root, dirs, files) in os.walk(path):
      if dirs:
        continue
      plugin_attrs = os.path.basename(root).split('-', 1)
      plugin = plugin_attrs[0]
      plugin_instance = ''
      if len(plugin_attrs) > 1:
        plugin_instance = plugin_attrs[1]

      for file in files:
        try:
          # strip date from file name
          attrs = file.split('-')[:-3]
          type = attrs[0]
          type_instance = ''
          if len(attrs) > 1:
            type_instance = attrs[1]

          with open(root + os.sep + file, "r") as csvfile:
            csvreader = csv.reader(csvfile)
            header_row = next(csvreader)
            header_row.pop(0)
            for row in csvreader:
              epoch = row.pop(0)
              doc = {
                  'run_uri': run_uri,
                  'benchmark': benchmark_name,
                  'vmname': vm_name,
                  'vm_group': vm_group,
                  'plugin': plugin,
                  'plugin_instance': plugin_instance,
                  'type': type,
                  'type_instance': type_instance,
                  'time': epoch,
                  'dsnames': header_row,
                  'dstypes': ['NA' for i in header_row],
                  'values': row,
                  'interval': 10,
              }
              docs.append(doc)
              if len(docs) >= COLLECTD_MAX_RECORDS_PER_SEND:
                yield docs
                docs = []
        except IndexError:
          parse_error_count += 1
    if parse_error_count:
      logging.info("Encountered {} errors parsing Collectd CSV".format(parse_error_count))
    yield docs


class SvrInfo:

  SYSD_KEYS = ['BIOS Version', 'Binutils Version', 'GCC Version', 'Manufacturer', 'Microcode', 'Product Name']

  def __init__(self, benchmark_spec, output_dir):
    self.benchmark_spec = benchmark_spec
    self.output_dir = output_dir
    self.vm_json = {}
    self.vm_elastic_formatted_json = {}
    self._ParseJson()

  def _ParseJson(self):
    for vm in self.benchmark_spec.vms:
      local_results_dir = os.path.join(self.output_dir, vm.name + '-svrinfo')
      json_path = os.path.join(local_results_dir, vm.ip_address + '.json')
      with open(json_path, 'r') as f:
        data = json.load(f)
        self.vm_json[vm.name] = data
        self.vm_elastic_formatted_json[vm.name] = self._FormatDataForPublish(data, self.benchmark_spec, vm)

  def KafkaPublish(self):
    topic = 'svrinfo'
    for vm_name, json_data in self.vm_json.items():
      reformatted = self.vm_elastic_formatted_json.get(vm_name, [])
      SendKafka(topic, [reformatted])

  def _FormatDataForPublish(self, data, benchmark_spec, vm):
    # "Flatten" keys to eliminate non-deterministic keys
    flattened_data = {}
    for key in data:
      flattened_data[key] = json.dumps(data[key])
    data = flattened_data
    vm_group = benchmark_spec.GetVmGroupForVm(vm)
    data['run_uri'] = benchmark_spec.uuid
    data['vm_name'] = vm.name
    data['vm_group'] = vm_group
    data['sample_uri'] = str(uuid.uuid4())
    data['test'] = benchmark_spec.name
    return data

  @classmethod
  def FormatForPlatform(cls, vm_svrinfo):
    platform = {}
    platform['frequencies_measured'] = json.dumps(vm_svrinfo.get('frequencies_measured', None))
    platform['cpu'] = json.dumps(vm_svrinfo.get('cpu', None))
    platform['security_vulnerabilities'] = json.dumps(vm_svrinfo.get('security_vuln', {}))

    net = vm_svrinfo.get('net', {})
    platform['net'] = []
    for idx, dev in net.items():
      platform['net'].append(json.dumps(dev))

    blkdev = vm_svrinfo.get('block_devices', {})
    platform['blk'] = []
    for idx, blk in blkdev.items():
        platform['blk'].append(json.dumps(blk))

    sysd = vm_svrinfo.get('sysd', {})
    for key in cls.SYSD_KEYS:
      platform_key = key.replace(' ', '_').lower()
      platform[platform_key] = sysd.get(key, None)
    return platform


def _GetTimestampedFileName(benchmark_name, run_uri):
  timestamp = time.strftime('%Y_%m_%d_%H_%M')
  run_uri = run_uri[:8]
  return '_'.join([benchmark_name, timestamp, run_uri]) + '.tar.gz'


def SendKafka(topic, records):
  """Send data to Kafka brokers under supplied topic name.
  Args:
    topic: Kafka topic where records will be sent
    records: a list of objects that will be published.
  """
  now = time.time()
  records_with_timestamp = []
  for record in records:
    record_copy = copy.deepcopy(record)
    if 'timestamp' not in record_copy:
      record_copy['timestamp'] = publisher.FormatTimestampForElasticsearch(now)
    else:
      record_copy['timestamp'] = publisher.FormatTimestampForElasticsearch(record_copy['timestamp'])
    record_copy = publisher.DeDotKeys(record_copy)
    records_with_timestamp.append(record_copy)

  broker_list = FLAGS.kafka_brokers.split(',')
  try:
    import kafka
    from kafka.errors import KafkaError
  except ImportError:
    raise ImportError('The "kafka-python" package is required to use '
                      'the Kafka publisher. Please make sure it '
                      'is installed.')
  try:
    logger = logging.getLogger('kafka')
    logger.setLevel(logging.ERROR)
    if FLAGS.kafka_ssl_key_path:
      key_path = FLAGS.kafka_ssl_key_path
      producer = kafka.KafkaProducer(bootstrap_servers=broker_list,
                                     ssl_cafile=os.path.join(key_path, 'ca.crt'),
                                     ssl_certfile=os.path.join(key_path, 'kafka.crt'),
                                     ssl_keyfile=os.path.join(key_path, 'kafka.key'),
                                     security_protocol='SSL', ssl_check_hostname=False,
                                     retries=2)
    else:
      producer = kafka.KafkaProducer(bootstrap_servers=broker_list, retries=2)
    for d in records_with_timestamp:
      producer.send(topic, json.dumps(d).encode('utf-8'))
    logging.info("Sent {} documents to Kafka topic {}".format(len(records_with_timestamp), topic))
    producer.flush(timeout=30)
    producer.close(timeout=30)
  except KafkaError as err:
    logging.error("Unable to send data to Kafka brokers: {}".format(err))


def _GetSamplesFromFile(json_file):
  samples = []
  try:
    with open(json_file, 'r') as file:
      for sample in [json.loads(s) for s in file if s]:
        samples.append(sample)
  except IOError as e:
    logging.warning("Encountered error {} trying to open {}. Exiting.".format(e, json_file))
    raise PkbRunDirParseErrorException
  return samples


def PublishFromPerfkitResultsDir(pkb_dir):
  """ Reads in completed data from a Perfkitbenchmarker run directory and publishes data
    to Kafka and to S3 Archive. Data published to Kafka includes results, platforms, collectd (if available).
  Args:
    pkb_dir: Full path to pkb run directory, example: /tmp/perfkitbenchmarker/runs/abc12345.
  Returns:
    No return value.
  """

  intel_results_dir = os.path.join(pkb_dir, INTEL_PUBLISHER_DIR)
  results_json_path = os.path.join(intel_results_dir, DEFAULT_RESULTS_JSON_FILENAME)
  default_json_path = os.path.join(pkb_dir, publisher.DEFAULT_JSON_OUTPUT_NAME)
  platforms_json_path = os.path.join(intel_results_dir, DEFAULT_PLATFORMS_JSON_FILENAME)

  # If platform JSON exists, publish it (backwards compatibility)
  if os.path.exists(platforms_json_path):
    samples = _GetSamplesFromFile(results_json_path)
    SendKafka(DEFAULT_PLATFORMS_TOPIC, samples)

  if os.path.exists(results_json_path):
    samples = _GetSamplesFromFile(results_json_path)
  elif os.path.exists(publisher.DEFAULT_JSON_OUTPUT_NAME):
    samples = _GetSamplesFromFile(default_json_path)
  else:
    logging.warning("Could not find any usable files for publishing.")
    raise PkbRunDirParseErrorException

  # Search for run UIDs in results file.
  unique_benchmarks = {}

  for sample in samples:
    if 'metadata' in sample and 'owner' in sample:
      if 'uid' in sample['metadata']:
        uid = sample['metadata']['uid']
        run_uri = sample['run_uri']
        test = sample['test']
        if uid not in unique_benchmarks:
          unique_benchmarks[uid] = (run_uri, test, [])
        unique_benchmarks[uid][2].append(sample)

  if not unique_benchmarks:
    logging.warning("Could not find any benchmark uid in parsed samples. Publishing "
                    "samples as they are without s3 archive. Any svr_info, collectd will be skipped.")
    SendKafka(DEFAULT_RESULTS_TOPIC, samples)
    return

  # We expect pickled files that match the name of the uid found in metadata.
  for uid, (run_uri, test, benchmark_samples) in unique_benchmarks.items():
    benchmark_spec_path = os.path.join(pkb_dir, uid)
    intel_publisher = IntelPublisher()
    intel_publisher.temp_dir = pkb_dir
    intel_publisher.samples = benchmark_samples
    intel_publisher.s3_archive_filename = _GetTimestampedFileName(test, run_uri)
    try:
      with open(benchmark_spec_path, 'rb') as file:
        benchmark_spec = pickle.load(file)
        try:
          intel_publisher.svrinfo = SvrInfo(benchmark_spec, pkb_dir)
        except Exception as e:
          logging.info('Could not publish svrinfo: {}'.format(e))
        try:
          intel_publisher.collectd = Collectd(benchmark_spec, pkb_dir)
        except Exception as e:
          logging.info('Could not publish collectd: {}'.format(e))
    except IOError:
      logging.warning('Benchmark doesn\'t have any benchmark_spec'
                      ' at {}, trying to publish without it'.format(benchmark_spec_path))
    intel_publisher.KafkaPublish()


if __name__ == '__main__':
  import log_util
  log_util.ConfigureBasicLogging()
  try:
    argv = FLAGS(sys.argv)
  except flags.Error as e:
    logging.error(e)
    print(FLAGS.module_help(__file__))
    sys.exit(1)

  # Set kafka_publish to True for the sample publisher.
  logging.info("Setting flag --kafka_publish for Intel Kafka publishing.")
  FLAGS.kafka_publish = True

  if FLAGS.intel_publisher_run_dir:
    PublishFromPerfkitResultsDir(FLAGS.intel_publisher_run_dir)
