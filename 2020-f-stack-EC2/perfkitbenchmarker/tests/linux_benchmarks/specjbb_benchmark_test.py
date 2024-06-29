import os
import unittest
import mock
from perfkitbenchmarker.linux_benchmarks import specjbb_benchmark
from perfkitbenchmarker import sample
from tests import test_utils
from tests.ignite_virtual_machine import Ubuntu2004BasedIgniteVirtualMachine
from absl import flags
import tempfile
import warnings
import posixpath


# Enable for viewing logging
# import logging
# import sys
# logger = logging.getLogger()
# logger.level = logging.INFO
# stream_handler = logging.StreamHandler(sys.stdout)
# logger.addHandler(stream_handler)

FLAGS = flags.FLAGS


class SpecjbbBenchmarkTest(unittest.TestCase):

  def setUp(self):
    pass

  def tearDown(self):
    pass

  def testJvmFailedToStart(self):
    vm = mock.MagicMock()
    vm.RemoteHostCommand = mock.MagicMock(return_value=('12\n13\n', 0))
    vm.RemoteCopy = mock.MagicMock()
    groups = 4
    self.assertRaises(Exception, specjbb_benchmark._CheckJvmProcesses, vm, {'BACKEND': groups, 'TXINJECTOR': groups})

  def testAutomaticConfigurationParameters(self):
    vm = mock.MagicMock()
    spec = mock.MagicMock()
    spec.vm_groups = {specjbb_benchmark.VM_GROUP: [vm]}
    vm.num_cpus = 112
    vm.CheckLsCpu = mock.MagicMock(return_value=mock.MagicMock)
    vm.CheckLsCpu().numa_node_count = 4
    tuning_params = spec.tunable_parameters_metadata = {}
    specjbb_benchmark._GenerateMetadataFromFlags(spec)
    self.assertEqual(28, tuning_params['specjbb_gc_threads'])
    self.assertEqual(4, tuning_params['specjbb_groups'])
    self.assertEqual(196, tuning_params['specjbb_tier_1_threads'])
    self.assertEqual(7, tuning_params['specjbb_tier_2_threads'])
    self.assertEqual(33, tuning_params['specjbb_tier_3_threads'])
    self.assertEqual('28g', tuning_params['specjbb_xmx'])
    self.assertEqual('28g', tuning_params['specjbb_xms'])
    self.assertEqual('26g', tuning_params['specjbb_xmn'])

    vm.num_cpus = 8
    vm.CheckLsCpu().numa_node_count = 1
    specjbb_benchmark._GenerateMetadataFromFlags(spec)
    self.assertEqual(8, tuning_params['specjbb_gc_threads'])
    self.assertEqual(1, tuning_params['specjbb_groups'])
    self.assertEqual(56, tuning_params['specjbb_tier_1_threads'])
    self.assertEqual(2, tuning_params['specjbb_tier_2_threads'])
    self.assertEqual(9, tuning_params['specjbb_tier_3_threads'])
    self.assertEqual('8g', tuning_params['specjbb_xmx'])
    self.assertEqual('8g', tuning_params['specjbb_xms'])
    self.assertEqual('6g', tuning_params['specjbb_xmn'])


  def testHeapCalculation(self):
    vm = mock.MagicMock()
    spec = mock.MagicMock()
    spec.vm_groups = {specjbb_benchmark.VM_GROUP: [vm]}
    vm.num_cpus = 80
    vm.CheckLsCpu = mock.MagicMock(return_value=mock.MagicMock)
    vm.CheckLsCpu().numa_node_count = 2
    tuning_params = spec.tunable_parameters_metadata = {}
    specjbb_benchmark._GenerateMetadataFromFlags(spec)
    self.assertEqual('31g', tuning_params['specjbb_xmx'])
    self.assertEqual('31g', tuning_params['specjbb_xms'])
    self.assertEqual('29g', tuning_params['specjbb_xmn'])

    vm.num_cpus = 160
    specjbb_benchmark._GenerateMetadataFromFlags(spec)
    self.assertEqual('80g', tuning_params['specjbb_xmx'])
    self.assertEqual('80g', tuning_params['specjbb_xms'])
    self.assertEqual('78g', tuning_params['specjbb_xmn'])


  @mock.patch('time.time', mock.MagicMock(return_value=1550279509.59))
  def testParseResults(self):
    test_path = os.path.join(os.path.dirname(__file__), '../data', 'specjbb_controller_output.txt')
    with mock.patch.object(posixpath, 'join') as posixpath_mock:
      posixpath_mock.return_value = test_path
      vm = mock.MagicMock()
      vm.RemoteCopy = mock.MagicMock()
      samples = specjbb_benchmark._GetResults(vm)
    expected = [
        sample.Sample(metric='max-jOPS', value=143034.0, unit='operations/sec',
                      metadata={'primary_sample': True}, timestamp=1550279509.59),
        sample.Sample(metric='critical-jOPS', value=66401.0, unit='operations/sec',
                      metadata={}, timestamp=1550279509.59)
    ]
    self.assertEqual(expected, samples)

  def testParseFailedResults(self):
    test_path = os.path.join(os.path.dirname(__file__), '../data', 'specjbb_controller_failure_output.txt')
    metadata = {'specjbb_kitversion': 'NA'}
    with mock.patch.object(posixpath, 'join') as posixpath_mock:
      posixpath_mock.return_value = test_path
      vm = mock.MagicMock()
      vm.RemoteCopy = mock.MagicMock()
    self.assertRaises(Exception, specjbb_benchmark._GetResults, vm, metadata)


class SpecjbbIgniteBenchmarkTest(unittest.TestCase):

  def setUp(self):
    warnings.simplefilter("ignore", category=ResourceWarning)
    benchmark_uid = 'specjbb0'
    self.temp_dir_obj = tempfile.TemporaryDirectory()
    FLAGS.temp_dir = self.temp_dir_obj.name
    try:
      vm = Ubuntu2004BasedIgniteVirtualMachine(benchmark_uid + '_vm')
      FLAGS.http_proxy = 'http://proxy-chain.intel.com:911'
      FLAGS.https_proxy = 'http://proxy-chain.intel.com:912'
      vms = [vm]
      self.spec = test_utils.CreateBenchmarkSpec(specjbb_benchmark, vms, benchmark_uid)
      self.spec.vm_groups[specjbb_benchmark.VM_GROUP] = vms
    except Exception as e:
      self.skipTest("Encountered exception while provisioning Ignite VM: {}".format(e))

  def tearDown(self):
    for vm in self.spec.vms:
      vm.teardown()
    self.temp_dir_obj.cleanup()

  def testPrepare(self):
    specjbb_benchmark.Prepare(self.spec)
    vm = self.spec.vms[0]
    _, _, retcode = vm.RemoteCommandWithReturnCode('java -version')
    self.assertEqual(0, retcode, "Java installation found.")

    specjbb_installation = '/opt/pkb/SPECjbb2015'
    stdout, _ = vm.RemoteCommand('ls -d {}'.format(specjbb_installation))
    self.assertEqual(specjbb_installation, stdout.rstrip(), "Specjbb installation found.")


if __name__ == '__main__':
  unittest.main()
