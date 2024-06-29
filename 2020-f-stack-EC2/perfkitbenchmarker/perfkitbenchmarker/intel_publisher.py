import logging
import os
import shutil
import subprocess
import pymongo
import sys
import json
import fcntl
import copy
if __name__ == '__main__':
  sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from absl import flags
from perfkitbenchmarker import publisher
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import intel_publisher_models as m
from perfkitbenchmarker import version

FLAGS = flags.FLAGS
flags.DEFINE_string('run_dir', None,
                    'Path to a perfkitbenchmarker run directory to publish.')
flags.DEFINE_boolean('intel_publish', False, 'Enable Intel publishing including MongoDB, S3 archiving, and log file.')
flags.DEFINE_string('intel_publisher_mongodb_connection_string', 'xyz', 'MongoDB connection string for Intel Publisher.')
flags.DEFINE_string('intel_publisher_mongodb_name', 'cumulus', 'MongoDB database name for Intel Publisher.')
flags.DEFINE_string('intel_publisher_s3_archive_bucket_url',
                    'https://d15e4ftowigvkb.cloudfront.net',
                    'URL of bucket to save run directory archive. This bucket must '
                    'allow anonymous upload from the PKB host.')

INTEL_PUBLISHER_DIR = 'intel_publisher'
METRICS_WITHOUT_METADATA = set('End to End Runtime')


class IntelSampleCollector:
  """A decorator class for the SampleCollector Class which provides data transformation capabilities
  on top of samples prior to publishing.
  """

  def __init__(self, metadata_providers=None, publishers=None,
               publishers_from_flags=True, add_default_publishers=True, enable_base_collector=True):
    self.base_collector = None
    self.samples = []
    if enable_base_collector:
      self.base_collector = publisher.SampleCollector(metadata_providers, publishers,
                                                      publishers_from_flags, add_default_publishers)
      self.samples = self.base_collector.samples
    self.run = None
    self.sample_types = m.InitializeCollections()
    self.platforms = {}
    self.intel_publishers = []
    if add_default_publishers:
      self.intel_publishers.extend(self._DefaultPublishers())
    if publishers_from_flags:
      if FLAGS.intel_publish:
        self.intel_publishers.append(MongoDbPublisher(
            connection_string=FLAGS.intel_publisher_mongodb_connection_string,
            db=FLAGS.intel_publisher_mongodb_name))
      if FLAGS.intel_publisher_s3_archive_bucket_url and FLAGS.svrinfo:
        self.intel_publishers.append(SvrinfoS3Publisher(vm_util.GetTempDir()))
    logging.info("Initialized Intel Sample Collector")

  @classmethod
  def _DefaultPublishers(cls):
    intel_publishers = [JsonFilePublisher(vm_util.GetTempDir())]
    return intel_publishers

  def AddSamples(self, samples, benchmark, benchmark_spec):
    """Adds data samples to the publisher.

    Args:
      samples: A list of Sample objects.
      benchmark: string. The name of the benchmark.
      benchmark_spec: BenchmarkSpec. Benchmark specification.
    """
    if self.base_collector:
      base_samples = copy.deepcopy(samples)
      for sample in base_samples:
        for key in benchmark_spec.software_config_metadata.keys():
          if key not in sample.metadata:
            sample.metadata[key] = benchmark_spec.software_config_metadata[key]
        for key in benchmark_spec.tunable_parameters_metadata.keys():
          if key not in sample.metadata:
            sample.metadata[key] = benchmark_spec.tunable_parameters_metadata[key]
        sample.metadata.update(benchmark_spec.tunable_parameters_metadata)
      self.base_collector.AddSamples(base_samples, benchmark, benchmark_spec)
    benchmark_spec.s3_archive_url = os.path.join(FLAGS.intel_publisher_s3_archive_bucket_url,
                                                 FLAGS.run_uri + '.zip')
    # Create Run Document
    if not self.run:
      self.run = m.PerfkitRun(benchmark_spec, FLAGS.owner)
      self.run.perfkitbenchmarker_version = version.VERSION
      self.run.cmd_line = " ".join(sys.argv[:])
      self.sample_types[m.PERFKITRUN_COLLECTION].append(self.run)
    self._CreateSamplePoints(benchmark_spec, samples)
    self._CreatePlatforms(benchmark_spec)
    self._CreateMetadata(benchmark_spec)

  def _CreateSamplePoints(self, benchmark_spec, samples):
    """Create results SamplePoints."""
    for s in samples:
      if not self.run.timestamp or s.timestamp < self.run.timestamp:
        self.run.timestamp = s.timestamp
      sample_point = m.SamplePoint(benchmark_spec.workload_name, self.run.uri, s)
      if 'primary_sample' in sample_point.sample_metadata and sample_point.sample_metadata['primary_sample'] is True:
        self.run.SetPrimarySamplePoint(sample_point.ToShortForm())
        self.run.timestamp = sample_point.timestamp
      self.sample_types[m.SAMPLEPOINT_COLLECTION].append(sample_point)
    global_metadata = self._StripConstantSampleMetadata(self.sample_types[m.SAMPLEPOINT_COLLECTION])
    benchmark_spec.software_config_metadata.update(global_metadata)

  def _CreatePlatforms(self, benchmark_spec):
    """Create Platforms and SUT platform."""
    for vm_group, vms in benchmark_spec.vm_groups.items():
      for vm in vms:
        if vm.name not in self.platforms:
          platform = m.Platform(self.run.uri, vm, vm_group)
          if FLAGS.svrinfo and vm.ip_address:
            platform.AddSvrinfo(vm_util.GetTempDir(), vm.ip_address, FLAGS.intel_publisher_s3_archive_bucket_url)
          self.platforms[vm.name] = platform
          self.sample_types[m.PLATFORM_COLLECTION].append(platform)
        if vm_group == benchmark_spec.sut_vm_group and not self.run.sut_platform:
          self.run.SetSutPlatform(self.platforms[vm.name].ToShortForm())

  def _CreateMetadata(self, benchmark_spec):
    """Create Software Configuration Metadata and Create Tunable Parameters Metadata."""
    if not self.run.softw_config_uri:
      software_config_metadata = m.Metadata(benchmark_spec.software_config_metadata, m.METADATA_SW_CONFIG_TYPE)
      self.sample_types[m.METADATA_COLLECTION].append(software_config_metadata)
      self.run.softw_config_uri = software_config_metadata.uri
    if not self.run.tune_param_uri:
      tunable_parameters_metadata = m.Metadata(benchmark_spec.tunable_parameters_metadata, m.METADATA_PARAMS_TYPE)
      self.sample_types[m.METADATA_COLLECTION].append(tunable_parameters_metadata)
      self.run.tune_param_uri = tunable_parameters_metadata.uri

  def IntelPublishSamples(self):
    """Publish samples via all registered publishers."""
    samples_todict = {sample_type: [publisher.DeDotKeys(s.todict()) for s in samples]
                      for sample_type, samples in self.sample_types.items()}
    if self.run:
      for p in self.intel_publishers:
        p.PublishSamples(samples_todict)

  def PublishSamples(self):
    """Pass-through to base_collector."""
    self.base_collector.PublishSamples()

  @staticmethod
  def _StripConstantSampleMetadata(sample_points):
    """Finds and deletes sample metadata which exists for all samples.

    Args:
      sample_points: A list of SamplePoint objects.

    Returns:
      Dictionary of key-value pairs that are constant across all samples.
    """
    def KeyValSerializer(key, value):
      return "{}={}".format(key, value)

    global_metadata_pairs = {}
    if len(sample_points) < 2:
      return global_metadata_pairs
    key_val_counter = {}
    # Drop end-to-end runtime: it always has no metadata.
    non_endtoend_samples = [i for i in sample_points
                            if i.metric != 'End to End Runtime']
    # Iterate once to count times that each key-value pair occurs
    for sample in non_endtoend_samples:
      for key, value in sample.sample_metadata.items():
        serialized_metadata_pair = KeyValSerializer(key, value)
        if serialized_metadata_pair in key_val_counter:
          key_val_counter[serialized_metadata_pair] += 1
        else:
          key_val_counter[serialized_metadata_pair] = 1
    # Iterate again to check if metadata occurred in all samples
    for sample in non_endtoend_samples:
      for key, value in copy.deepcopy(sample.sample_metadata).items():
        serialized_metadata_pair = KeyValSerializer(key, value)
        if key_val_counter[serialized_metadata_pair] == len(sample_points):
          # key = val exists in all samples
          del sample.sample_metadata[key]
          global_metadata_pairs[key] = value
    return global_metadata_pairs


class MongoDbPublisher(publisher.SamplePublisher):
  """Writes Intel samples to a MongoDB.
  """

  def __init__(self, connection_string, db):
    super().__init__()
    self.connection_string = connection_string
    self.db = db

  def PublishSamples(self, sample_types):
    logging.info("Attemping to publish to {}".format(self.connection_string))
    client = pymongo.MongoClient(self.connection_string)
    db = client[self.db]
    for collection, sample_list in sample_types.items():
      try:
        r = db[collection].insert_many(sample_list)
        logging.info("Inserted into collection {}: {}".format(collection, r.acknowledged))
      except Exception as e:
        logging.error("Inserting into collection {} failed: {}".format(collection, e))


class JsonFilePublisher(publisher.SamplePublisher):
  """Writes Intel samples to JSON files.
  """
  def __init__(self, run_dir):
    super().__init__()
    self.results_dir = os.path.join(run_dir, INTEL_PUBLISHER_DIR)

  def PublishSamples(self, sample_types):
    vm_util.IssueCommand(['mkdir', '-p', self.results_dir])
    sample_types = self._PreventDuplicates(sample_types)
    for sample_type, samples in sample_types.items():
      results_file = os.path.join(self.results_dir, sample_type + '.json')
      logging.info('Writing data samples to file: {}'.format(results_file))
      with open(results_file, 'a+') as fp:
        fcntl.flock(fp, fcntl.LOCK_EX)
        for sample in samples:
          fp.write(json.dumps(copy.deepcopy(sample)) + '\n')

  def _PreventDuplicates(self, sample_types):
    new_samples = {}
    existing_run_uris = [s['uri'] for s in self._ReadSamples(m.PERFKITRUN_COLLECTION)]
    run_uri_fields = {m.PERFKITRUN_COLLECTION: 'uri', m.PLATFORM_COLLECTION: 'run_uri'}
    # Ensure run_uri is not already recorded in JSON
    for collection, field in run_uri_fields.items():
      for sample in sample_types.get(collection, []):
        if sample.get(field) not in existing_run_uris:
          new_samples.setdefault(collection, []).append(sample)
    # For these collections, there should not be duplicates, or they do not matter.
    for collection in [m.SAMPLEPOINT_COLLECTION, m.METADATA_COLLECTION]:
      for sample in sample_types.get(collection, []):
        new_samples.setdefault(collection, []).append(sample)
    return new_samples

  def _ReadSamples(self, sample_type):
    samples = []
    json_file = os.path.join(self.results_dir, sample_type + '.json')
    try:
      with open(json_file, 'r') as file:
        return [json.loads(s) for s in file if s]
    except FileNotFoundError:
      return samples


class SvrinfoS3Publisher(publisher.SamplePublisher):
  """Writes Svrinfo from Intel platform samples to S3.
  """
  def __init__(self, run_dir):
    self.run_dir = run_dir
    super().__init__()

  def PublishSamples(self, sample_types):
    for platform in sample_types.get(m.PLATFORM_COLLECTION, []):
      if platform['server_info_html_url']:
        html_filename = m.Platform.GetLocalSvrinfoFilename(self.run_dir,
                                                           platform['pkb_name'],
                                                           platform['ip_address'],
                                                           '.html')
        UploadFileToS3(platform['server_info_html_url'], html_filename, headers=['Content-Type: text/html'])


def ArchiveToS3(run_dir, filename):
  """Compresses run_dir into a .zip format and uploads.
  Intended to be used outside of publisher after run has completed.

  Args:
    run_dir: Full path to perfkitbenchmarker run directory.
    filename: Name for Zip file, defaults to name of run directory if not provided.
  """
  temp_zip = os.path.join('/tmp', filename)
  shutil.make_archive(temp_zip.strip('.zip'), 'zip', run_dir)
  s3_path = os.path.join(FLAGS.intel_publisher_s3_archive_bucket_url, filename)
  UploadFileToS3(s3_path, temp_zip)
  os.unlink(temp_zip)


def UploadFileToS3(s3_bucket_url, filename, headers=None):
  """Uploads file to S3 bucket via curl."""
  upload_cmd = ['curl', '-X', 'PUT', '-H', 'x-amz-acl: bucket-owner-full-control',
                '-T', filename, s3_bucket_url]
  if headers:
    for header in headers:
      upload_cmd.extend(['-H', header])
  logging.info("Uploading results to {}".format(s3_bucket_url))
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
  return success


def RepublishJSONSamples(run_dir):
  """Read samples from JSON files and re-export them.

  Args:
    run_dir: the path to the Perfkitbenchmarker run directory.
  """
  results_dir = os.path.join(run_dir, INTEL_PUBLISHER_DIR)
  sample_types = m.InitializeCollections()
  run_uri = None
  try:
    for sample_type in sample_types.keys():
      json_file = os.path.join(results_dir, sample_type + '.json')
      with open(json_file, 'r') as file:
        samples = [json.loads(s) for s in file if s]
        sample_types[sample_type] = samples
        # Try to fetch run_uri while reading samples for later use.
        if sample_type == m.PERFKITRUN_COLLECTION and samples:
          run_uri = samples[0].get('uri', None)
    publishers = [MongoDbPublisher(connection_string=FLAGS.intel_publisher_mongodb_connection_string,
                                   db=FLAGS.intel_publisher_mongodb_name)]
    if FLAGS.intel_publisher_s3_archive_bucket_url:
      publishers.append(SvrinfoS3Publisher(run_dir))

    for p in publishers:
      p.PublishSamples(sample_types)
  except FileNotFoundError as e:
    logging.info("Error: {}".format(e))
  return run_uri


if __name__ == '__main__':
  import log_util
  log_util.ConfigureBasicLogging()
  try:
    argv = FLAGS(sys.argv)
  except flags.Error as e:
    logging.error(e)
    print(FLAGS.module_help(__file__))
    sys.exit(1)

  logging.info("Setting flag --intel_publish for Intel MongoDB and S3 publishing.")
  FLAGS.intel_publish = True
  if FLAGS.run_dir:
    run_uri = RepublishJSONSamples(FLAGS.run_dir)
    if run_uri:
      ArchiveToS3(FLAGS.run_dir, run_uri + '.zip')
  else:
    logging.warning("Please specify --run_dir=<perfkit directory> to publish results.")
