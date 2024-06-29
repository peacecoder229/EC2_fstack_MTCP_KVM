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
"""Run MLPerf benchmarks."""

import posixpath
import logging
from perfkitbenchmarker import configs
from perfkitbenchmarker import errors
from absl import flags
from perfkitbenchmarker import sample
from perfkitbenchmarker import data
from perfkitbenchmarker import intel_mlperf_utils as mlperf_utils

FLAGS = flags.FLAGS
flags.DEFINE_enum("mlperf_inference_version", "v0.5", ("v0.5", "v0.7"),
                  "MLPerf Inference version to use")
flags.DEFINE_enum("intel_mlperf_framework", "tensorflow",
                  ("pytorch", "tensorflow", "openvino"), "MLPerf framework to use")
flags.DEFINE_enum("intel_mlperf_model", "resnet50",
                  ("resnet50", "ssd-mobilenet-v1", "ssd-mobilenet", "bert"), "Model to run")
flags.DEFINE_enum("mlperf_device", "cpu", ("cpu", "gpu"), "Device to use")
flags.DEFINE_integer('mlperf_count', -1, 'limits the number of items in the dataset used')
flags.DEFINE_integer('mlperf_time', -1, 'limits the time the benchmark runs')
flags.DEFINE_integer('mlperf_qps', -1, 'Expected QPS')
flags.DEFINE_float('mlperf_max_latency', -1.0, 'the latency used for Server mode')
flags.DEFINE_bool('mlperf_accuracy', False, 'To run with accuracy pass')
flags.DEFINE_bool('mlperf_use_local_data', False, 'Set to use local data for MLPerf runs')
flags.DEFINE_string("imagenet_dataset_tensorflow_localpath",
                    "/home/pkb/intel_mlperf/imagenet_data_tensorflow.tar.gz",
                    "Local path to imagenet dataset copy on PKB host")
flags.DEFINE_string("imagenet_dataset_localpath",
                    "/home/pkb/intel_mlperf/imagenet_data.tar.gz",
                    "Local path to imagenet dataset copy on PKB host")
flags.DEFINE_string("coco_dataset_localpath",
                    "/home/pkb/intel_mlperf/coco_dataset.tar.gz",
                    "Local path to coco dataset copy on PKB host")
flags.DEFINE_string("mlperf_ov_repo_localpath",
                    "/home/pkb/intel_mlperf/mlperf_ext_ov_cpp-master.tar.gz",
                    "Local path to MLPerf Openvino repo copy on PKB host")
flags.DEFINE_string("configs_models_localpath",
                    "/home/pkb/intel_mlperf/configs_models.tar.gz",
                    "Local path to configs-models copy on PKB host")
flags.DEFINE_string("squad_dataset_localpath",
                    "/home/pkb/intel_mlperf/dataset-SQUAD.tar.gz",
                    "Local path to SQUAD dataset copy on PKB host")
flags.DEFINE_integer('intel_mlperf_batch_size', 1, 'Batch size for MLPerf run')
flags.DEFINE_enum("intel_mlperf_loadgen_scenario", "Offline",
                  ("Offline", "SingleStream", "Server", "MultiStream"),
                  "MLPerf Loadgen scenario")
flags.DEFINE_integer('intel_mlperf_num_instances', 1,
                     'Number of instances for MLPerf run')
flags.DEFINE_enum("intel_mlperf_loadgen_mode", "PerformanceOnly",
                  ("PerformanceOnly", "AccuracyOnly"), "MLPerf Loadgen mode")
flags.DEFINE_string('mlperf_ov_repo_url',
                    'https://gitlab.devtools.intel.com/mlperf/mlperf_ext_ov_cpp/-/archive/master/mlperf_ext_ov_cpp-master.tar.gz',
                    'The url where the MLPerf-Openvino workload exists')
flags.DEFINE_string('mlperf_ov_7_repo_url',
                    'https://gitlab.devtools.intel.com/mlperf/mlperf-inference-v0.7-intel-submission/-/archive/master/mlperf-inference-v0.7-intel-submission-master.tar.gz',
                    'The url where the MLPerf-v7-Openvino workload exists')

BENCHMARK_NAME = 'intel_mlperf'
BENCHMARK_CONFIG = """
intel_mlperf:
  description: Runs MLPerf Benchmark.
  vm_groups:
    default:
      os_type: ubuntu1804
      disk_spec: *default_500_gb
      vm_spec:
        GCP:
          machine_type: n1-highcpu-32
          zone: us-east1-b
          boot_disk_size: 100
          min_cpu_platform: skylake
        AWS:
          machine_type: c5.24xlarge
          zone: us-east-2
          boot_disk_size: 100
        Azure:
          machine_type: Standard_F32s_v2
          zone: eastus
          boot_disk_size: 100
"""


def GetConfig(user_config):
  """Load and return benchmark config.

  Args:
    user_config: user supplied configuration (flags and config file)

  Returns:
    loaded benchmark configuration
  """
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
  return config


def CheckPrerequisites(benchmark_config):
  """Verifies that the required configs are present.

  Raises:
    perfkitbenchmarker.errors.Config.InvalidValue: On invalid value.
    perfkitbenchmarker.data.ResourceNotFound: On missing resource.
  """
  logging.info("Checking Prerequisites")
  if FLAGS.intel_mlperf_framework == "tensorflow":
    if FLAGS.mlperf_use_local_data:
      data.ResourcePath(FLAGS.imagenet_dataset_tensorflow_localpath)
    if FLAGS.intel_mlperf_loadgen_scenario == "Server":
      mlperf_utils.CheckServerScenarioPrereqs(FLAGS)
    if FLAGS.intel_mlperf_loadgen_scenario == "MultiStream":
      mlperf_utils.CheckMultiStreamScenarioPrereqs(FLAGS)
  if FLAGS.intel_mlperf_framework == "openvino":
    if FLAGS.mlperf_use_local_data:
      data.ResourcePath(FLAGS.mlperf_ov_repo_localpath)
      if FLAGS.intel_mlperf_model == "resnet50":
        data.ResourcePath(FLAGS.imagenet_dataset_localpath)
      if FLAGS.intel_mlperf_model == "ssd-mobilenet-v1":
        data.ResourcePath(FLAGS.coco_dataset_localpath)


def Prepare(benchmark_spec, vm=None):
  """Install and set up MLPerf on the target vm.

  Args:
    benchmark_spec: The benchmark specification
    vm: The VM to work on
  """
  mlperf_utils.UpdateBenchmarkSpecWithConfig(benchmark_spec)
  if vm is None:
    vm = benchmark_spec.vms[0]
  logging.info("Preparing VM to run MLPerf for CPU")
  mlperf_utils.UpdateBenchmarkSpecWithFlags(benchmark_spec,
                                            mlperf_params={"framework":
                                                           FLAGS.intel_mlperf_framework,
                                                           "mlperf_version":
                                                           FLAGS.mlperf_inference_version,
                                                           "model": FLAGS.intel_mlperf_model,
                                                           "device": FLAGS.mlperf_device,
                                                           "batch_sz":
                                                           FLAGS.intel_mlperf_batch_size,
                                                           "scenario":
                                                           FLAGS.intel_mlperf_loadgen_scenario,
                                                           "num_inst":
                                                           FLAGS.intel_mlperf_num_instances,
                                                           "mode": FLAGS.intel_mlperf_loadgen_mode,
                                                           "count": FLAGS.mlperf_count,
                                                           "time": FLAGS.mlperf_time,
                                                           "qps": FLAGS.mlperf_qps,
                                                           "max_latency": FLAGS.mlperf_max_latency,
                                                           "accuracy": FLAGS.mlperf_accuracy,
                                                           "use_local_data": FLAGS.mlperf_use_local_data,
                                                           "local_datapath": FLAGS.imagenet_dataset_tensorflow_localpath,
                                                           "local_datapath_ov": FLAGS.imagenet_dataset_localpath,
                                                           "local_cocodata_ov": FLAGS.coco_dataset_localpath,
                                                           "local_squaddata_ov": FLAGS.squad_dataset_localpath,
                                                           "local_mlperfov_repo": FLAGS.mlperf_ov_repo_localpath,
                                                           "local_cfg_models_ov7": FLAGS.configs_models_localpath,
                                                           "mlperfv7_openvino_url": FLAGS.mlperf_ov_7_repo_url,
                                                           "openvino_url": FLAGS.mlperf_ov_repo_url})
  mlperf_utils.Prepare(benchmark_spec)


def Run(benchmark_spec):
  """Run MLPerf on the cluster.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
      required to run the benchmark.

  Returns:
    A list of sample.Sample objects.
  """
  samples = []
  logging.info("Running MLPerf for CPU")
  samples = mlperf_utils.Run(benchmark_spec, 'intel_mlperf')
  return samples


def Cleanup(benchmark_spec):
  """Cleanup MLPerf on the cluster.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
      required to run the benchmark.
  """
  logging.info("Cleanup VM after MLPerf for CPU ")
  mlperf_utils.Cleanup(benchmark_spec)
