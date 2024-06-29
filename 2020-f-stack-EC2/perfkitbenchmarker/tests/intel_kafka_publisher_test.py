import unittest
import os
import json
import sys
from unittest.mock import PropertyMock, patch, Mock, MagicMock
import tempfile
from perfkitbenchmarker import intel_kafka_publisher
from perfkitbenchmarker import errors
from absl import flags

FLAGS = flags.FLAGS
FLAGS.mark_as_parsed()


class TestIntelPublisher(unittest.TestCase):

  def testCreatePlatformSamplesVmUnavailable(self):
    with patch.object(intel_kafka_publisher, 'FLAGS', return_value=MagicMock()):
      intel_kafka_publisher.FLAGS.owner = 'test'
      vm = MagicMock()
      spec = MagicMock()
      vm.CheckLsCpu = MagicMock(side_effect=errors.VirtualMachine.RemoteCommandError('Got non-zero return code...'))
      spec.vms = [vm]
      publisher = intel_kafka_publisher.IntelPublisher()
      platforms = publisher._CreatePlatformSamples(spec)

      self.assertTrue('cpu_model' not in platforms[0])


class TestPublishFromPerfkitResultsDir(unittest.TestCase):

  open_fds = []

  def setUp(self):
    intel_kafka_publisher.IntelPublisher._ArchiveToS3 = MagicMock()
    FLAGS.intel_kafka_publisher_s3_archive_bucket_url = ""
    FLAGS.kafka_publish = True

  def tearDown(self):
    for fd in self.open_fds:
      fd.close()

  def CreateIntelPublisherOutput(self, tmpdir, samples):
    os.mkdir(os.path.join(tmpdir, intel_kafka_publisher.INTEL_PUBLISHER_DIR))
    results_filename = os.path.join(tmpdir, intel_kafka_publisher.INTEL_PUBLISHER_DIR,
                                    intel_kafka_publisher.DEFAULT_RESULTS_JSON_FILENAME)
    self.CreatePkbFiles(results_filename, samples)

  def CreateDefaultPublisherOutput(self, tmpdir, samples):
    results_filename = os.path.join(tmpdir, 'perfkitbenchmarker_results.json')
    self.CreatePkbFiles(results_filename, samples)

  def CreatePkbFiles(self, filename, samples):
    fd = open(os.path.join(filename), mode='w')
    for sample in samples:
      fd.write(json.dumps(sample) + '\n')
    fd.seek(0, 0)
    self.open_fds.append(fd)

  def testAddSvrinfoToPlatform(self):
    run_uri = '12345'
    vm_name = 'pkb-12345-0'
    svrinfo_d = {
        'cpu': {"AVX512 Available": "Yes", "VNNI Available": "Yes"},
        'frequencies_measured': {'1': '5000', '2': '5006', '3': '5010'},
        'security_vuln': {'CVE-12345': 'OK'},
        "block_devices": {
            "0": {"FSTYPE": "squashfs", "MIN-IO": "512", "MODEL": "",
                  "MOUNTPOINT": "/snap/snapd/10492", "NAME": "loop0",
                  "RQ-SIZE": "128", "SIZE": "31.1M"},
            "4": {"FSTYPE": "ext4", "MIN-IO": "512", "MODEL": "", "MOUNTPOINT": "/",
                  "NAME": "nvme0n1p1", "RQ-SIZE": "31", "SIZE": "8G"}
        }
    }

    platform = {"name": vm_name, "vm_name": vm_name, "machine_type": None,
                "cloud": "Static", "vm_group": "vm_1", "cpu_model": "CPU",
                "sockets": "1", "num_cpus": 4, "numa_node_count": 1, "memory_gb": 15.483421325683594,
                "image": 'image', "kernel_release": "4.99", "os_type": "ubuntu1604",
                "os_info": "Linux", "uid": "benchmark0", "run_uri": run_uri}

    platform.update(intel_kafka_publisher.SvrInfo.FormatForPlatform(svrinfo_d))
    expected = "{\"CVE-12345\": \"OK\"}"

    self.assertEqual(expected, platform['security_vulnerabilities'])

    blk_expected = [
        '{"FSTYPE": "squashfs", "MIN-IO": "512", "MODEL": "", '
        '"MOUNTPOINT": "/snap/snapd/10492", "NAME": "loop0", '
        '"RQ-SIZE": "128", "SIZE": "31.1M"}',
        '{"FSTYPE": "ext4", "MIN-IO": "512", "MODEL": "", "MOUNTPOINT": "/", '
        '"NAME": "nvme0n1p1", "RQ-SIZE": "31", "SIZE": "8G"}']
    self.assertEqual(blk_expected, platform['blk'])

  def testPublishFromFiles(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      run_uri = 'runid12'
      benchmark_uid1 = 'abc123'
      benchmark_uid2 = 'cba123'
      platforms_1 = [{'vm_name': benchmark_uid1 + '0', 'run_uri': run_uri, 'uid': benchmark_uid1}]
      platforms_2 = [{'vm_name': benchmark_uid2 + '0', 'run_uri': run_uri, 'uid': benchmark_uid2}]


      samples = [
          {'timestamp': 1232, 'test': 'mytest', 'platforms': platforms_1, 'metric': 'throughput',
           'unit': 'ops/sec', 'value': 4000, 'sample_uri': 'abc123', 'run_uri': run_uri,
           'owner': 'test', 'metadata': {'nodes': 1, 'uid': benchmark_uid1}},
          {'timestamp': 1232, 'test': 'mytest', 'platforms': platforms_2, 'metric': 'throughput',
           'unit': 'ops/sec', 'value': 4000, 'sample_uri': 'abc123', 'run_uri': run_uri,
           'owner': 'test', 'metadata': {'nodes': 1, 'uid': benchmark_uid2}}
      ]
      self.CreateIntelPublisherOutput(tmpdir, samples)
      with patch('perfkitbenchmarker.intel_kafka_publisher.SendKafka') as mock:
        with patch('perfkitbenchmarker.intel_kafka_publisher._GetTimestampedFileName') as m:
          m.return_value = None
          intel_kafka_publisher.PublishFromPerfkitResultsDir(tmpdir)
          mock.assert_any_call(intel_kafka_publisher.DEFAULT_RESULTS_TOPIC, [samples[0]])
          mock.assert_any_call(intel_kafka_publisher.DEFAULT_RESULTS_TOPIC, [samples[1]])


if __name__ == '__main__':
  unittest.main()
