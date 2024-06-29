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

"""Run TensorFlow Inference Benchmarks using Intel Model Zoo.

For more details, see https://github.com/IntelAI/models/tree/master/benchmarks

"""
from numpy import median
from perfkitbenchmarker import configs
from absl import flags
from perfkitbenchmarker import sample
from perfkitbenchmarker import errors
from perfkitbenchmarker.regex_util import ExtractExactlyOneMatch, ExtractAllMatches
from time import sleep
import os

FLAGS = flags.FLAGS


class BaseModel(object):
    """
    BaseModel assumes the following:
    - model is hosted on intel tensorflow models repository
    - no additional steps to prepare and run the model are needed
    """

    _INTEL_TENSORFLOW_MODELS_BASE_URL = "https://storage.googleapis.com/intel-optimized-tensorflow/models/v1_5"

    def __init__(self, name, filename, precision):
        """

        :param name: name of the model to be passed to launch_benchmark script
        :param filename: name of the model filename that will be downloaded and used
        :param precision: int8 or fp32
        """
        self.name = name
        self.filename = filename
        self.precision = precision

    def get_url(self):
        return "{}/{}".format(BaseModel._INTEL_TENSORFLOW_MODELS_BASE_URL, self.filename)

    def prepare(self, vm):
        pass

    def get_samples(self, stdout):
        raise NotImplementedError()

    def get_framework_params(self):
        """

        :return: List of parameters to be passed to launch_benchmark.py script
        """
        params = []

        framework = FLAGS.intel_tensorflow_framework
        mode = FLAGS.intel_tensorflow_mode
        batch_size = FLAGS.intel_tensorflow_batch_size
        docker_image = FLAGS.intel_tensorflow_docker_image
        socket_id = FLAGS.intel_tensorflow_socket_id
        num_intra_threads = FLAGS.intel_tensorflow_num_intra_threads
        num_inter_threads = FLAGS.intel_tensorflow_num_inter_threads
        data_num_intra_threads = FLAGS.intel_tensorflow_data_num_intra_threads
        data_num_inter_threads = FLAGS.intel_tensorflow_data_num_inter_threads

        params.extend(['--benchmark-only'])
        params.extend(['--model-name', self.name])
        params.extend(['--precision', self.precision])
        params.extend(['--framework', framework])
        params.extend(['--mode', mode])

        # Optional params
        if batch_size is not None:
            params.extend(['--batch-size', str(batch_size)])
        if docker_image is not None:
            params.extend(['--docker-image', docker_image])
        if socket_id is not None:
            params.extend(['--socket-id', str(socket_id)])
        if num_intra_threads is not None:
            params.extend(['--num-intra-threads', str(num_intra_threads)])
        if num_inter_threads is not None:
            params.extend(['--num-inter-threads', str(num_inter_threads)])
        if data_num_intra_threads is not None:
            params.extend(['--data-num-intra-threads', str(data_num_intra_threads)])
        if data_num_inter_threads is not None:
            params.extend(['--data-num-inter-threads', str(data_num_inter_threads)])
        if FLAGS.intel_tensorflow_dataset_location:
            params.extend(['--data-location', "{}/{}".format(BaseModel.get_models_dir(), basename(FLAGS.intel_tensorflow_dataset_location))])

        return params

    @staticmethod
    def get_model_params():
        """

        :return: List of parameters to be passed to model after arguments to launch_benchmark.py script (after '--')
        """
        params = []

        omp_num_threads = FLAGS.intel_tensorflow_omp_num_threads
        if omp_num_threads is not None:
            params.append("OMP_NUM_THREADS={}".format(omp_num_threads))

        kmp_blocktime = FLAGS.intel_tensorflow_kmp_blocktime
        params.append("KMP_BLOCKTIME={}".format(kmp_blocktime))

        kmp_aff_granularity = FLAGS.intel_tensorflow_kmp_affinity_granularity
        kmp_aff_respect = FLAGS.intel_tensorflow_kmp_affinity_respect
        kmp_aff_verbose = FLAGS.intel_tensorflow_kmp_affinity_verbose
        kmp_aff_warnings = FLAGS.intel_tensorflow_kmp_affinity_warnings
        kmp_aff_type = FLAGS.intel_tensorflow_kmp_affinity_type
        kmp_aff_permute = FLAGS.intel_tensorflow_kmp_affinity_permute
        kmp_aff_offset = FLAGS.intel_tensorflow_kmp_affinity_offset
        kmp_aff = "KMP_AFFINITY=granularity={},{},{},{},{},{},{}".format(kmp_aff_granularity, kmp_aff_respect,
                                                                         kmp_aff_verbose, kmp_aff_warnings,
                                                                         kmp_aff_type, kmp_aff_permute, kmp_aff_offset)
        params.append(kmp_aff)
        return params

    @staticmethod
    def get_models_dir():
        return "{}/downloads".format(FLAGS.intel_model_zoo_dir)

    @staticmethod
    def get_tensorflow_models_dir():
        return "{}/tensorflow-models".format(BaseModel.get_models_dir())

    @staticmethod
    def download_tensorflow_models_repo(vm):
        cmd = 'mkdir -p {tf_dir}; cd {tf_dir} ; if [ ! -d .git ] ; then git clone {url} . ; fi'.format(
            tf_dir=BaseModel.get_tensorflow_models_dir(), url="https://github.com/tensorflow/models")
        vm.RemoteCommand(cmd)


class ResnetModel(BaseModel):

    def get_samples(self, stdout):
        samples = []

        throughput = ExtractExactlyOneMatch(r'Throughput: (\d+\.\d+) images/sec', stdout)
        samples.append(sample.Sample('throughput', float(throughput), 'images/sec'))

        # Latency is only reported for batch-size == 1
        if FLAGS.intel_tensorflow_batch_size == 1:
            latency = ExtractExactlyOneMatch(r'Latency: (\d+\.\d+) ms', stdout)
            samples.append(sample.Sample('latency', float(latency), 'ms'))

        return samples

    def get_framework_params(self):
        params = super().get_framework_params()
        params.extend(['--in-graph', "{}/{}".format(BaseModel.get_models_dir(), self.filename)])
        return params

    @staticmethod
    def get_model_params():
        params = super(ResnetModel, ResnetModel).get_model_params()

        # Tensorflow ignores KMP_BLOCKTIME environment variable and needs another argument passed
        kmp_blocktime = FLAGS.intel_tensorflow_kmp_blocktime
        params.append("kmp_blocktime={}".format(kmp_blocktime))

        return params


class MobilenetV1ModelInt8(BaseModel):

    def get_samples(self, stdout):
        samples = []

        throughput = ExtractAllMatches(r', (\d+\.\d+) images/sec', stdout)
        average_throughput = sum([float(t) for t in throughput]) / len(throughput)
        samples.append(sample.Sample('throughput', average_throughput, 'images/sec'))

        return samples

    def get_framework_params(self):
        params = super().get_framework_params()
        params.extend(['--in-graph', "{}/{}".format(BaseModel.get_models_dir(), self.filename)])
        return params

    def get_model_params(self):
        params = super().get_model_params()
        params.extend(['input_height=224'])
        params.extend(['input_width=224'])
        params.extend(['warmup_steps=10'])
        params.extend(['steps=50'])
        params.extend(['input_layer=input'])
        params.extend(['output_layer=MobilenetV1/Predictions/Reshape_1'])
        return params


class MobilenetV1ModelFP32(BaseModel):

    def _get_model_dir(self):
        return "{}/mobilenetfp32".format(BaseModel.get_models_dir())

    def get_url(self):
        return "http://download.tensorflow.org/models/mobilenet_v1_2018_08_02/{}".format(self.filename)

    def prepare(self, vm):
        # Download mobilenet_v1 checkpoint files
        cmd = "cd {models_dir} ; mkdir -p {model_dir} ; tar -xf {filename} -C {model_dir}".format(
            models_dir=BaseModel.get_models_dir(), model_dir=self._get_model_dir(), filename=self.filename)
        vm.RemoteCommand(cmd)
        # Download tensorflow models repository
        BaseModel.download_tensorflow_models_repo(vm)

    def get_samples(self, stdout):
        samples = []

        throughput = ExtractExactlyOneMatch(r'Total images/sec = (\d+\.\d+)', stdout)
        samples.append(sample.Sample('throughput', float(throughput), 'images/sec'))

        # Latency is only reported for batch-size == 1
        if FLAGS.intel_tensorflow_batch_size == 1:
            latency = ExtractExactlyOneMatch(r'Latency ms/step = (\d+\.\d+)', stdout)
            samples.append(sample.Sample('latency', float(latency), 'ms'))

        return samples

    def get_framework_params(self):
        params = super().get_framework_params()
        params.extend(['--model-source-dir', "{}".format(BaseModel.get_tensorflow_models_dir())])
        params.extend(['--checkpoint', "{}".format(self._get_model_dir())])
        return params


class WideAndDeepLarge(BaseModel):

    def _get_model_dir(self):
        return "{}/wideanddeep".format(BaseModel.get_models_dir())

    def prepare(self, vm):
        if not FLAGS.intel_tensorflow_dataset_location:
            raise errors.VirtualMachine.RemoteCommandError("No data specified: Wide and Deep Large requires a dataset to run.")

    def get_samples(self, stdout):
        samples = []

        throughput = ExtractExactlyOneMatch(r'Throughput is \(records/sec\)  :  (\d+\.\d+)', stdout)
        samples.append(sample.Sample('throughput', float(throughput), 'images/sec'))

        latency = ExtractExactlyOneMatch(r'Average Latency \(ms/batch\)   :  (\d+\.\d+)', stdout)
        samples.append(sample.Sample('latency', float(latency), 'ms'))

        return samples

    def get_framework_params(self):
        params = super().get_framework_params()
        params.extend(['--in-graph', "{}/{}".format(BaseModel.get_models_dir(), self.filename)])
        if FLAGS.intel_tensorflow_num_cores:
            params.extend(['--num-cores {}'.format(FLAGS.intel_tensorflow_num_cores)])
        return params

    def get_model_params(self):
        params = super().get_model_params()
        params.extend(["num_omp_threads={}".format(FLAGS.intel_tensorflow_omp_num_threads)])
        return params


class MaskRCNN(BaseModel):

    def _get_model_dir(self):
        return "{}/maskrcnn".format(BaseModel.get_models_dir())

    def prepare(self, vm):
        if not FLAGS.intel_tensorflow_dataset_location:
            raise errors.VirtualMachine.RemoteCommandError("No data specified: MaskRCNN requires a dataset to run.")
        if FLAGS.intel_tensorflow_batch_size != 1:
            raise errors.VirtualMachine.RemoteCommandError("MaskRCNN benchmark only supports a batch size of 1")

        cmd = ('mkdir -p {source} ; cd {source} ; if [ ! -d .git ] ; '
               'then git clone {rcnn_url} . ; fi ; wget -q {model_url} ; '
               'mkdir -p coco ; cd coco ; if [ ! -d .git ] ; '
               'then git clone {coco_url} . ; fi ').format(rcnn_url='https://github.com/matterport/Mask_RCNN.git',
                                                           coco_url='https://github.com/waleedka/coco.git',
                                                           model_url=self.filename,
                                                           source=self._get_model_dir())
        vm.RemoteCommand(cmd)
        vm.RemoteCommand('pip3 install Cython')
        vm.RemoteCommand('pip3 install matplotlib')
        # There sometimes is an error with pip installing pycocotools. If that happens, use the following command to download it from the github repo
        # vm.RemoteCommand('pip3 install -U \'git+https://github.com/cocodataset/cocoapi.git#subdirectory=PythonAPI\'')
        vm.RemoteCommand('pip3 install pycocotools')
        vm.RemoteCommand('pip3 install numpy')

    def get_samples(self, stdout):
        samples = []

        throughput = ExtractExactlyOneMatch(r'Total samples/sec: (\d+\.\d+) samples/s', stdout)
        samples.append(sample.Sample('throughput', float(throughput), 'images/sec'))

        latency = ExtractExactlyOneMatch(r'Time spent per BATCH: (\d+\.\d+) ms', stdout)
        samples.append(sample.Sample('latency', float(latency), 'ms'))

        return samples

    def get_framework_params(self):
        params = super().get_framework_params()
        params.extend(['--model-source-dir', "{}".format(self._get_model_dir())])
        return params

    def get_model_params(self):
        params = super().get_model_params()
        return params


class SSDVGG(BaseModel):

    def _get_model_dir(self):
        return "{}/ssdvgg".format(BaseModel.get_models_dir())

    def get_url(self):
        return "https://storage.googleapis.com/intel-optimized-tensorflow/models/{}".format(self.filename)

    def prepare(self, vm):
        if FLAGS.intel_tensorflow_batch_size != 1:
            raise errors.VirtualMachine.RemoteCommandError("SSD-VGG16 benchmark only supports a batch size of 1")

        cmd = ('mkdir -p {source} ; cd {source} ; if [ ! -d .git ] ; '
               'then git clone {vgg_url} . ; fi ; '
               'cd SSD.TensorFlow ; git checkout {branch} ').format(vgg_url='https://github.com/HiKapok/SSD.TensorFlow.git',
                                                                    branch='2d8b0cb9b2e70281bf9dce438ff17ffa5e59075c',
                                                                    source=self._get_model_dir())
        vm.RemoteCommand(cmd)

    def get_samples(self, stdout):
        samples = []

        throughput = ExtractExactlyOneMatch(r'Throughput: (\d+\.\d+) images/sec', stdout)
        samples.append(sample.Sample('throughput', float(throughput), 'images/sec'))

        latency = ExtractExactlyOneMatch(r'Latency: (\d+\.\d+) ms', stdout)
        samples.append(sample.Sample('latency', float(latency), 'ms'))

        return samples

    def get_framework_params(self):
        params = super().get_framework_params()
        params.extend(['--model-source-dir', "{}".format(self._get_model_dir())])
        params.extend(['--in-graph', "{}/{}".format(BaseModel.get_models_dir(), self.filename)])
        return params

    def get_model_params(self):
        params = super().get_model_params()
        params.extend(['warmup_steps=100'])
        params.extend(['steps=500'])
        return params


class NCF(BaseModel):

    def _get_model_dir(self):
        return "{}/ncf".format(BaseModel.get_models_dir())

    def get_url(self):
        return "https://storage.googleapis.com/intel-optimized-tensorflow/models/ncf_fp32_pretrained_model.tar.gz"

    def prepare(self, vm):
        cmd = ('mkdir -p {source} ; cd {source} && if [ ! -d .git ] ; '
               'then git clone {ncf_url} . && '
               'git checkout {branch} && sed -i.bak \'s/atexit.register/# atexit.register/g\' '
               ' official/recommendation/data_async_generation.py && '
               'sed -i.bak -e \'381s/^/\ \ /\' -e \'382s/^/\ \ /\' official/utils/logs/logger.py && '
               'sed -i.bak \'381i \ \ \ \ if "brand" in info.keys():\' official/utils/logs/logger.py && '
               'sed -i.bak \'383i \ \ \ \ if "hz_advertised_raw" in info.keys():\' '
               'official/utils/logs/logger.py ; fi ').format(ncf_url='https://github.com/tensorflow/models.git',
                                                             branch='v1.11',
                                                             source=self._get_model_dir())
        vm.RemoteCommand(cmd)
        vm.RemoteCommand('cd {source} ; tar -xf {file}'.format(source=BaseModel.get_models_dir(), file=self.filename))

    def get_samples(self, stdout):
        samples = []
        _, throughput, latency = ExtractExactlyOneMatch(r'Average recommendations/sec across (\d+) steps: (\d+.\d+) \((\d+\.\d+) msec/batch\)', stdout)
        samples.append(sample.Sample('throughput', float(throughput), 'recommendations/sec'))
        samples.append(sample.Sample('latency', float(latency), 'ms'))
        return samples

    def get_framework_params(self):
        params = super().get_framework_params()
        params.extend(['--model-source-dir', "{}".format(self._get_model_dir())])
        params.extend(['--checkpoint', "{}/{}".format(BaseModel.get_models_dir(), "ncf_trained_movielens_1m")])
        return params

    def get_model_params(self):
        params = super().get_model_params()
        return params


class Wavenet(BaseModel):

    def _get_model_dir(self):
        return "{}/wavenet".format(BaseModel.get_models_dir())

    def get_url(self):
        return "https://storage.googleapis.com/intel-optimized-tensorflow/models/{}".format(self.filename)

    def prepare(self, vm):
        cmd = ('mkdir -p {source} ; cd {source} ; if [ ! -d .git ] ; '
               'then git clone {wavenet_url} . ; fi ; '
               'git fetch origin pull/352/head:cpu_optimized ; '
               'git checkout cpu_optimized').format(wavenet_url='https://github.com/ibab/tensorflow-wavenet.git',
                                                    source=self._get_model_dir())
        vm.RemoteCommand(cmd)
        vm.RemoteCommand('cd {source} ; tar -xf {file}'.format(source=BaseModel.get_models_dir(), file=self.filename))
        vm.RemoteCommand('pip3 install librosa')
        vm.RemoteCommand('pip3 install numba==0.43.0')
        vm.RemoteCommand('pip3 install llvmlite==0.32.1')

    def get_samples(self, stdout):
        samples = []
        throughput = ExtractExactlyOneMatch(r'Average Throughput of whole run: Samples / sec: (\d+\.\d+)', stdout)
        samples.append(sample.Sample('throughput', float(throughput), 'Samples/sec'))
        latency = ExtractExactlyOneMatch(r'Average Latency of whole run: msec / sample: (\d+\.\d+)', stdout)
        samples.append(sample.Sample('latency', float(latency), 'ms'))
        return samples

    def get_framework_params(self):
        params = super().get_framework_params()
        params.extend(['--model-source-dir', "{}".format(self._get_model_dir())])
        params.extend(['--checkpoint', "{}/{}".format(BaseModel.get_models_dir(), "wavenet_checkpoints")])
        params.extend(['--num-cores {}'.format(FLAGS.intel_tensorflow_num_cores)])
        return params

    def get_model_params(self):
        params = super().get_model_params()
        params.extend(["checkpoint_name=model.ckpt-99"])
        params.extend(["sample=8510"])
        return params


SUPPORTED_MODELS = {
    ('resnet50', 'int8'): ResnetModel('resnet50', 'resnet50_int8_pretrained_model.pb', 'int8'),
    ('resnet50', 'fp32'): ResnetModel('resnet50', 'resnet50_fp32_pretrained_model.pb', 'fp32'),
    ('mobilenetv1', 'int8'): MobilenetV1ModelInt8('mobilenet_v1', 'mobilenetv1_int8_pretrained_model.pb', 'int8'),
    ('mobilenetv1', 'fp32'): MobilenetV1ModelFP32('mobilenet_v1', 'mobilenet_v1_1.0_224.tgz', 'fp32'),
    ('wideanddeeplarge', 'fp32'): WideAndDeepLarge('wide_deep_large_ds', 'wide_deep_fp32_pretrained_model.pb', 'fp32'),
    ('wideanddeeplarge', 'int8'): WideAndDeepLarge('wide_deep_large_ds', 'wide_deep_int8_pretrained_model.pb', 'int8'),
    ('maskrcnn', 'fp32'): MaskRCNN('maskrcnn', 'https://github.com/matterport/Mask_RCNN/releases/download/v2.0/mask_rcnn_coco.h5', 'fp32'),
    ('ssdvgg16', 'fp32'): SSDVGG('ssd_vgg16', 'ssdvgg16_fp32_pretrained_model.pb', 'fp32'),
    ('ssdvgg16', 'int8'): SSDVGG('ssd_vgg16', 'ssdvgg16_int8_pretrained_model.pb', 'int8'),
    ('ncf', 'fp32'): NCF('ncf', 'ncf_fp32_pretrained_model.tar.gz', 'fp32'),
    ('wavenet', 'fp32'): Wavenet('wavenet', 'wavenet_fp32_pretrained_model.tar.gz', 'fp32')
}

# Benchmark execution flags
flags.DEFINE_enum('intel_tensorflow_model_name',
                  'resnet50',
                  list({k[0] for k in SUPPORTED_MODELS.keys()}),
                  'Pretrained model name.')

flags.DEFINE_enum('intel_tensorflow_precision',
                  'fp32',
                  list({k[1] for k in SUPPORTED_MODELS.keys()}),
                  'Precision to be used with the model. Please note that not all models support all precisions.')

flags.DEFINE_string('intel_tensorflow_docker_image',
                    None,
                    'If set, Specify the docker image/tag to use when running benchmarking within a container. If no '
                    'docker image is specified, then no docker container will be used.')

flags.DEFINE_string('intel_tensorflow_dataset_location',
                    None,
                    'If set, Specify the location of the dataset for inference. If no '
                    'location is specified, then no real data will be used. This may cause failure for some workloads.')

flags.DEFINE_bool('intel_tensorflow_optimized_model_download',
                  True,
                  'If set, will download optimized model from intel model zoo'
                  'some models download pretrained models from else where')

flags.DEFINE_enum('intel_tensorflow_framework',
                  'tensorflow',
                  ['tensorflow'],
                  'Specify the name of the deep learning framework to use.')

flags.DEFINE_enum('intel_tensorflow_mode',
                  'inference',
                  ['inference', 'training'],
                  'Specify the type training or inference.')

flags.DEFINE_integer('intel_tensorflow_batch_size',
                     None,
                     'Specify the batch size. If this parameter is not specified or is -1, the largest ideal batch '
                     'size for the model will be used',
                     lower_bound=-1)

flags.DEFINE_integer('intel_tensorflow_num_cores',
                     None,
                     'Specify the number of cores to use. If the parameter is not specified or is -1, all cores will '
                     'be used.')

flags.DEFINE_integer('intel_tensorflow_socket_id',
                     None,
                     'Specify which socket to use. Only one socket will be used when this value is set. If used in '
                     'conjunction with intel_tensorflow_num_cores, all cores will be allocated on the single socket.')

flags.DEFINE_integer('intel_tensorflow_num_intra_threads',
                     None,
                     'Specify the number of threads within the layer')

flags.DEFINE_integer('intel_tensorflow_num_inter_threads',
                     None,
                     'Specify the number of threads between layers')

flags.DEFINE_integer('intel_tensorflow_data_num_intra_threads',
                     None,
                     'The number intra op threads for the data layer config')

flags.DEFINE_integer('intel_tensorflow_data_num_inter_threads',
                     None,
                     'The number inter op threads for the data layer config')

# Benchmark environment flags
flags.DEFINE_integer('intel_tensorflow_kmp_blocktime',
                     200,
                     'Sets the time, in milliseconds, that a thread should wait, after completing the execution of a '
                     'parallel region, before sleeping.')

flags.DEFINE_integer('intel_tensorflow_omp_num_threads',
                     None,
                     'https://software.intel.com/en-us/mkl-windows-developer-guide-improving-performance-with-threading')

KMP_AFFINITY_LINK = "https://software.intel.com/en-us/cpp-compiler-developer-guide-and-reference-thread-affinity-interface-linux-and-windows"

flags.DEFINE_enum('intel_tensorflow_kmp_affinity_granularity',
                  'core',
                  ['fine', 'thread', 'core', 'tile'],
                  KMP_AFFINITY_LINK)

flags.DEFINE_enum('intel_tensorflow_kmp_affinity_respect',
                  'respect',
                  ['respect', 'norespect'],
                  KMP_AFFINITY_LINK)

flags.DEFINE_enum('intel_tensorflow_kmp_affinity_verbose',
                  'noverbose',
                  ['verbose', 'noverbose'],
                  KMP_AFFINITY_LINK)

flags.DEFINE_enum('intel_tensorflow_kmp_affinity_warnings',
                  'warnings',
                  ['warnings', 'nowarnings'],
                  KMP_AFFINITY_LINK)

flags.DEFINE_enum('intel_tensorflow_kmp_affinity_type',
                  'none',
                  ['balanced', 'compact', 'disabled', 'explicit', 'none', 'scatter'],
                  KMP_AFFINITY_LINK)

flags.DEFINE_integer('intel_tensorflow_kmp_affinity_permute',
                     0,
                     KMP_AFFINITY_LINK,
                     lower_bound=0)

flags.DEFINE_integer('intel_tensorflow_kmp_affinity_offset',
                     0,
                     KMP_AFFINITY_LINK,
                     lower_bound=0)

# Miscellaneous flags
flags.DEFINE_integer('intel_tensorflow_warmup_runs',
                     5,
                     'The number of warmup runs for which no metrics will be stored.',
                     lower_bound=0)

flags.DEFINE_integer('intel_tensorflow_benchmark_runs',
                     10,
                     'The number times to run the benchmark. Metrics will be summarized and presented as mean+average.',
                     lower_bound=1)

flags.DEFINE_integer('intel_tensorflow_benchmark_pause',
                     1,
                     'Number of seconds to pause in between benchmark runs.',
                     lower_bound=0)

flags.DEFINE_boolean('intel_tensorflow_benchmark_remove_models',
                     False,
                     'If set, Models directory will be removed after the workload is finished.')

BENCHMARK_NAME = 'intel_tensorflow'
BENCHMARK_CONFIG = """
intel_tensorflow:
  description: Runs Intel AI TensorFlow benchmark
  vm_groups:
    default:
      vm_spec: *default_single_core
"""


def GetConfig(user_config):
    return configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)


def _GetModel():
    model_name = FLAGS.intel_tensorflow_model_name
    precision = FLAGS.intel_tensorflow_precision
    try:
        return SUPPORTED_MODELS[(model_name, precision)]
    except KeyError:
        raise ValueError("Unsupported combination of model {} and precision {}, please consult the README.".format(
            model_name, precision
        ))


def Prepare(benchmark_spec):
    vm = benchmark_spec.vms[0]

    vm.Install('wget')
    vm.Install('numactl')
    vm.Install('intel_tensorflow')
    vm.Install('intel_model_zoo')

    if FLAGS.intel_tensorflow_docker_image is not None:
        vm.Install('docker_ce')

    model = _GetModel()
    model_url = model.get_url()
    models_dir = BaseModel.get_models_dir()
    vm.RemoteCommand('sudo mkdir -p {path} ; sudo chown {user} {path}'.format(path=models_dir, user=vm.user_name))

    if FLAGS.intel_tensorflow_dataset_location:
        cmd = "[ -f \"{}/{}\" ]".format(BaseModel.get_models_dir(), basename(FLAGS.intel_tensorflow_dataset_location))
        _, _, retcode = vm.RemoteCommandWithReturnCode(cmd, ignore_failure=True, suppress_warning=True)
        if retcode:
            vm.RemoteHostCopy(FLAGS.intel_tensorflow_dataset_location, BaseModel.get_models_dir())

    if FLAGS.intel_tensorflow_optimized_model_download:
        vm.RemoteCommand('cd {} ; if [ ! -f {} ] ; then wget {}; fi'.format(models_dir, model.filename, model_url))

    model.prepare(vm)


def _GetLaunchBenchmarkCmd():
    model = _GetModel()

    cmd = []

    cmd.extend(['cd', '{}/benchmarks'.format(FLAGS.intel_model_zoo_dir), ';'])
    cmd.extend(['python3', 'launch_benchmark.py'])
    cmd.extend(model.get_framework_params())
    # Model parameters should be passed after '--'
    cmd.extend(['--'])
    cmd.extend(model.get_model_params())

    return ' '.join(cmd)


def _GetAverages(samples):
    sample_groups = {}

    # Split samples by their metric
    for s in samples:
        if s.metric not in sample_groups:
            sample_groups[s.metric] = []
        sample_groups[s.metric].append(s)

    averages = []

    for _, grouped_samples in sample_groups.items():
        metric = grouped_samples[0].metric
        unit = grouped_samples[0].unit
        values = [s.value for s in grouped_samples]
        _average = sum(values) / len(values)
        averages.append(sample.Sample('average {}'.format(metric), _average, unit))
        _median = median(values)
        averages.append(sample.Sample('median {}'.format(metric), _median, unit))

    return averages


def Run(benchmark_spec):
    samples = []
    vm = benchmark_spec.vms[0]
    cmd = _GetLaunchBenchmarkCmd()
    model = _GetModel()

    for i in range(FLAGS.intel_tensorflow_warmup_runs):
        vm.RemoteCommand(cmd)
        sleep(FLAGS.intel_tensorflow_benchmark_pause)

    for i in range(FLAGS.intel_tensorflow_benchmark_runs):
        stdout, _ = vm.RemoteCommand(cmd)
        samples.extend(model.get_samples(stdout))
        sleep(FLAGS.intel_tensorflow_benchmark_pause)

    samples.extend(_GetAverages(samples))

    return samples


def Cleanup(benchmark_spec):
    if FLAGS.intel_tensorflow_benchmark_remove_models:
        vm = benchmark_spec.vms[0]
        vm.RemoveFile(BaseModel.get_models_dir())


def basename(name):
    head, tail = os.path.split(name)
    return tail or os.path.basename(head)
