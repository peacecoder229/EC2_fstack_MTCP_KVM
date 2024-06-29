import unittest
from unittest.mock import patch, MagicMock
import tempfile
from perfkitbenchmarker import intel_publisher
from perfkitbenchmarker import intel_publisher_models as m
from perfkitbenchmarker import sample
from absl import flags
from perfkitbenchmarker import pkb  # pylint: disable=unused-import
FLAGS = flags.FLAGS
FLAGS.mark_as_parsed()


def CreateBenchmark():
  with patch.object(intel_publisher, 'FLAGS', return_value=MagicMock()):
    intel_publisher.FLAGS.owner = 'test'
    vm = MagicMock()
    vm.machine_type = 'test_machine_type'
    vm.name = 'pkb-test1234-0'
    vm.ip_address = '123.123.123.123'
    vm.CLOUD = 'static'
    vm.zone = 'abc'
    vm.os_type = 'ubuntu2004'
    spec = MagicMock()
    spec.uuid = 'test1234-abc-213-231215'
    spec.vms = [vm]
    spec.vm_groups = {'target': [vm]}
    spec.workload_name = "Test Workload V1.23"
    spec.software_config_metadata = {"main_software": "12.03", "compiler": "9.0"}
    spec.tunable_parameters_metadata = {"flag_value_switch": True, "some_num_threads": 192}
    spec.sut_vm_group = 'target'
    spec.s3_archive_url = 'xyz.abc'
    return spec


def CreateCollector(benchmark_spec):
  FLAGS.run_uri = 'test1234'
  FLAGS.svrinfo = False
  FLAGS.intel_publisher_s3_archive_bucket_url = 'abc.123.abc'
  with patch.object(intel_publisher, 'FLAGS', return_value=MagicMock()):
    intel_publisher.FLAGS.intel_publish = False
    with patch('perfkitbenchmarker.intel_publisher.SvrinfoS3Publisher'):
      collector = intel_publisher.IntelSampleCollector(publishers=[], add_default_publishers=False)
  samples = [sample.Sample('valuable_metric', 100, 'nanoseconds', {'sample_meta': 'bar'})]
  collector.AddSamples(samples, "internal_pkb_benchmark_name", benchmark_spec)
  return collector


class TestIntelSampleCollector(unittest.TestCase):

  def testAddSamplesRun(self):
    benchmark_spec = CreateBenchmark()
    collector = CreateCollector(benchmark_spec)
    # Test that run was created
    self.assertEqual(collector.run.workload_name, "Test Workload V1.23")

  def testAddSamplesMetadata(self):
    benchmark_spec = CreateBenchmark()
    collector = CreateCollector(benchmark_spec)
    # Test that software config and tunable parameters metadata were created and linked to run
    software_config_metadata_id = None
    tunable_parameters_metadata_id = None
    for metadata in collector.sample_types.get(m.METADATA_COLLECTION, []):
      if metadata.type == m.METADATA_SW_CONFIG_TYPE:
        software_config_metadata_id = metadata.uri
      if metadata.type == m.METADATA_PARAMS_TYPE:
        tunable_parameters_metadata_id = metadata.uri
    self.assertEqual(collector.run.softw_config_uri, software_config_metadata_id)
    self.assertEqual(collector.run.tune_param_uri, tunable_parameters_metadata_id)

  def testAddSamplesPlatform(self):
    benchmark_spec = CreateBenchmark()
    collector = CreateCollector(benchmark_spec)
    # Test SUT platform was created and added to run
    self.assertEqual(collector.run.sut_platform['machine_type'], 'test_machine_type')
    # Test platform is created with correct run_uri
    self.assertEqual(collector.sample_types[m.PLATFORM_COLLECTION][0].run_uri, collector.run.uri)

  def testSetS3ArchiveUrl(self):
    benchmark_spec = CreateBenchmark()
    collector = CreateCollector(benchmark_spec)
    self.assertEqual(collector.run.s3_archive_url, "abc.123.abc/test1234.zip")

  def testStripConstantSampleMetadata(self):
    workload_name = 'test workload'
    run_uri = 'abcd1234'
    sample1 = m.SamplePoint(workload_name, run_uri,
                            sample.Sample('valuable_metric', 100, 'nanoseconds', {'foo': 'not unique',
                                                                                  'foo2': 'is_unique',
                                                                                  'bar': 'different_value'}))
    sample2 = m.SamplePoint(workload_name, run_uri,
                            sample.Sample('valuable_metric', 100, 'nanoseconds', {'foo': 'not unique',
                                                                                  'bar': 'is_unique'}))
    sample3 = m.SamplePoint(workload_name, run_uri,
                            sample.Sample('valuable_metric', 100, 'nanoseconds', {'foo': 'not unique',
                                                                                  'bar': 'is_unique'}))
    global_metadata = intel_publisher.IntelSampleCollector._StripConstantSampleMetadata([sample1, sample2, sample3])
    self.assertEqual(global_metadata, {'foo': 'not unique'})
    self.assertEqual(sample1.sample_metadata, {'foo2': 'is_unique', 'bar': 'different_value'})
    self.assertEqual(sample3.sample_metadata, {'bar': 'is_unique'})

  def testDeDotKeysBeforePublish(self):
    benchmark_spec = CreateBenchmark()
    collector = CreateCollector(benchmark_spec)
    s = sample.Sample('valuable_metric.99%', 100, 'nanoseconds', {'sample_meta.test': 'bar.test'})
    collector.AddSamples([s], "internal_pkb_benchmark_name", benchmark_spec)
    test_publisher = MagicMock()
    test_publisher.PublishSamples = MagicMock()
    collector.intel_publishers.append(test_publisher)
    collector.IntelPublishSamples()
    # sample_meta.test -> sample_meta_test
    expected = {'sample_meta_test': 'bar.test'}
    dedotted_sample_metadata = test_publisher.PublishSamples.call_args[0][0]['samplePoints'][-1]['sample_metadata']
    self.assertEqual(expected, dedotted_sample_metadata)

  def testStripConstantSampleMetadataSingleSample(self):
    workload_name = 'test workload'
    run_uri = 'abcd1234'
    sample1 = m.SamplePoint(workload_name, run_uri,
                            sample.Sample('valuable_metric', 100, 'nanoseconds', {'primary_sample': True}))
    global_metadata = intel_publisher.IntelSampleCollector._StripConstantSampleMetadata([sample1])
    self.assertEqual(global_metadata, {})
    self.assertEqual(sample1.sample_metadata, {'primary_sample': True})


class TestPublishFromFiles(unittest.TestCase):

  def setUp(self):
    intel_publisher.ArchiveToS3 = MagicMock()
    FLAGS.intel_publisher_s3_archive_bucket_url = ""

  def _CreateFiles(self, run_dir):
    benchmark_spec = CreateBenchmark()
    collector = CreateCollector(benchmark_spec)
    collector.intel_publishers.append(intel_publisher.JsonFilePublisher(run_dir))
    collector.IntelPublishSamples()

  def testPublishFromFiles(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      self._CreateFiles(tmpdir)
      with patch('perfkitbenchmarker.intel_publisher.SvrinfoS3Publisher'):
        with patch('perfkitbenchmarker.intel_publisher.MongoDbPublisher'):
          run_uri = intel_publisher.RepublishJSONSamples(tmpdir)
          self.assertEqual(run_uri.split('-')[0], 'test1234')

  def testPreventDuplicates(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      benchmark_spec = CreateBenchmark()
      first_collector = CreateCollector(benchmark_spec)
      first_collector.intel_publishers.append(intel_publisher.JsonFilePublisher(tmpdir))
      first_collector.IntelPublishSamples()
      # Publishing twice should not write more perfkitsamples or platforms
      second_collector = CreateCollector(benchmark_spec)
      second_publisher = intel_publisher.JsonFilePublisher(tmpdir)
      second_collector.intel_publishers.append(second_publisher)
      second_collector.IntelPublishSamples()
      samples = second_publisher._ReadSamples(m.PERFKITRUN_COLLECTION)
      self.assertEqual(1, len(samples))
      platform_samples = second_publisher._ReadSamples(m.PLATFORM_COLLECTION)
      self.assertEqual(1, len(platform_samples))


if __name__ == '__main__':
  unittest.main()
