import uuid
import copy
import os
import json
import logging

PERFKITRUN_COLLECTION = 'perfKitRuns'
PLATFORM_COLLECTION = 'platforms'
SAMPLEPOINT_COLLECTION = 'samplePoints'
METADATA_COLLECTION = 'metadata'
METADATA_SW_CONFIG_TYPE = 'software_config'
METADATA_PARAMS_TYPE = 'params'


def InitializeCollections():
  return {
      PERFKITRUN_COLLECTION: [],
      PLATFORM_COLLECTION: [],
      SAMPLEPOINT_COLLECTION: [],
      METADATA_COLLECTION: [],
  }


class IntelPublisherDocument:

  def todict(self):
    return self.__dict__


class PerfkitRun(IntelPublisherDocument):

  def __init__(self, benchmark_spec, owner):
    self.uri = benchmark_spec.uuid
    self._id = self.uri
    self.timestamp = None
    self.cmd_line = None
    self.run_uri_short = benchmark_spec.uuid.split('-')[0]
    self.perfkitbenchmarker_version = None
    self.tester = owner
    self.workload_name = benchmark_spec.workload_name or benchmark_spec.name
    self.softw_config_uri = None
    self.tune_param_uri = None
    self.s3_archive_url = benchmark_spec.s3_archive_url
    self.sut_platform = {}
    self.primary_sample_point = {}

  def SetSutPlatform(self, platform_short_form):
    self.sut_platform = copy.deepcopy(platform_short_form)

  def SetPrimarySamplePoint(self, sample_point_short_form):
    self.primary_sample_point = copy.deepcopy(sample_point_short_form)


class Platform(IntelPublisherDocument):

  def __init__(self, run_uri, vm, vm_group):
    self.uri = str(uuid.uuid4())
    self._id = self.uri
    self.run_uri = run_uri
    self.pkb_name = vm.name
    self.vm_group = vm_group
    self.server_info = {}
    self.machine_type = vm.machine_type
    self.cloud = vm.CLOUD
    self.num_of_sockets = None
    self.cpu_model = None
    self.total_cpus = 0
    self.manufacturer = None
    self.product_name = None
    self.os_name = None
    self.server_info_html_url = ""
    self.ip_address = None

  def ToShortForm(self):
    return {
        'uri': self.uri,
        'cloud': self.cloud,
        'cpu_model': self.cpu_model,
        'machine_type': self.machine_type,
        'os_name': self.os_name,
        'total_cpus': self.total_cpus,
    }

  def AddSvrinfo(self, pkb_dir, ip_address, s3_bucket_url):
    json_path = self.GetLocalSvrinfoFilename(pkb_dir, self.pkb_name, ip_address, '.json')
    self.server_info_html_url = os.path.join(s3_bucket_url, self.pkb_name + '-svrinfo.html')
    try:
      with open(json_path, 'r') as f:
        self.server_info = json.load(f)
    except Exception as err:
      logging.error("Encountered exception '{}' while attempting read and parse svr_info.".format(err))
    self.ip_address = ip_address
    self.cpu_model = self.server_info.get('cpu', {}).get('Model Name', None)
    self.num_of_sockets = int(self.server_info.get('cpu', {}).get('Sockets', 0))
    self.total_cpus = int(self.server_info.get('cpu', {}).get('Total CPU(s)', 0))
    self.manufacturer = self.server_info.get('sysd', {}).get('Manufacturer', None)
    self.product_name = self.server_info.get('sysd', {}).get('Product Name', None)
    self.os_name = self.server_info.get('sysd', {}).get('OS', None)

  @staticmethod
  def GetLocalSvrinfoFilename(pkb_dir, pkb_vm_name, ip_address, ext):
    local_results_dir = os.path.join(pkb_dir, pkb_vm_name + '-svrinfo')
    return os.path.join(local_results_dir, ip_address + ext)


class SamplePoint(IntelPublisherDocument):
  def __init__(self, workload_name, run_uri, sample):
    self.run_uri = run_uri
    self.workload_name = workload_name
    self.uri = str(uuid.uuid4())
    self._id = self.uri
    self.metric = sample.metric
    self.unit = sample.unit
    self.value = sample.value
    self.timestamp = sample.timestamp
    self.sample_metadata = sample.metadata

  def ToShortForm(self):
    return {
        'uri': self.uri,
        'metric': self.metric,
        'unit': self.unit,
        'value': self.value
    }


class Metadata(IntelPublisherDocument):
  def __init__(self, json, type):
    self.uri = str(uuid.uuid4())
    self._id = self.uri
    self.type = type
    self.json_data = json
