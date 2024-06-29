## Intel MLPerf benchmark guidelines

#### Benchmark description
MLPerf supports TPU and GPU architectures, this feature will add support for CPU architectures.
MLPerf has Pytorch framework integrated from Intel's submissions to MLPerf org here [inference_results_v0.5](https://github.com/mlperf/inference_results_v0.5/tree/b2e18edae3dcdf18c95af99837fb97ad9f1a6c0b/closed/Intel/measurements/clx-9282-2s_pytorch-caffe2/resnet/Offline#build-deep-learning-math-kernel)
MLPerf also adds support for Tensorflow framework from [MLPerf refrence stack implementation](https://github.com/mlperf/inference/tree/master/v0.5/classification_and_detection) and OpenVINO framework using binaries from https://gitlab.devtools.intel.com/mlperf/mlperf_ext_ov_cpp.git
 
Currently, on the MLPerf-v5 version TensorFlow framework has only been tested on ubuntu 18.04 , PyTorch framework only supports Centos7 and OpenVINO framework only supports Ubuntu 18.04.
On MLPerf-v7 version TensorFlow and Openvino frameworks works on Ubuntu20.04.

Currently MLPerf-v5-Tensorflow and MLPerf-v5-Openvino benchmarks can be run using the local(PKB host) copies of datasets and repo without having to access Cumulus s3 bucket.


## How to run MLPerf with PKB
Get the code
```
git clone https://gitlab.devtools.intel.com/PerfKitBenchmarker/perfkitbenchmarker.git
```
Run on AWS
- Pytorch:
```
./pkb.py --cloud=AWS --benchmarks=intel_mlperf --os_type=centos7 --machine_type=c5.24xlarge --aws_boot_disk_size=100 --zones=us-east-2 --image=ami-01e36b7901e884a10 --intel_mlperf_framework=pytorch --svrinfo --collectd --kafka_publish
```
Note:  MLPerf-Pytorch runs have only been tested on Cascade lake or above system (e.g. on a c5 instance in AWS). The pre-built int8 models we have in our S3 bucket(s3://cumulus/intel_mlperf/int8_models.tar.tgz) were built on a Cascade lake system. If the user has pre-built int8 models that could work on a skylake machine, these can be replaced and run mlperf-pytorch using Cumulus-PKB
- TensorFlow:
```
 ./pkb.py --cloud=AWS --benchmarks=intel_mlperf --os_type=ubuntu1804 --machine_type=m5.12xlarge --aws_boot_disk_size=100 --zones=us-east-2 --image=ami-0b51ab7c28f4bf5a6 --intel_mlperf_framework=tensorflow --intel_mlperf_loadgen_scenario=Offline --intel_mlperf_batch_size=1 --intel_mlperf_model=resnet50 --svrinfo --collectd --kafka_publish
```
- OpenVINO:
```
 ./pkb.py --cloud=AWS --benchmarks=intel_mlperf --os_type=ubuntu1804 --machine_type=m5.12xlarge --aws_boot_disk_size=100 --zones=us-west-2  --image=ami-0b199ce4c7f1a6dd2 --intel_mlperf_framework=openvino --intel_mlperf_loadgen_scenario=SingleStream --intel_mlperf_model=resnet50 --svrinfo --collectd --kafka_publish
```

Flags that can be passed to above MLPerf pkb commands are
- `--mlperf_inference_version`={v0.5|v0.7} ; default is v0.5 version
- `--intel_mlperf_loadgen_scenario`={SingleStream|Offline}
- `--intel_mlperf_model`={resnet50}
- `--intel_mlperf_batch_size`=1 ; this will set --max-batchsize=1.
- `--mlperf_count`=100
- `--mlperf_time`=60
- `--mlperf_qps`=200
- `--mlperf_max_latency`=0.1
- `--mlperf_use_local_data`={True|False}; if set to True the dataset will be used from the local path specified in the config yaml param `imagenet_dataset_localpath` or `coco_dataset_localpath` and the local repo `mlperf_ov_repo_localpath` will be used.


e.g PKB command below to run MLPerf-Tensorflow in Server scenario
```
python3 pkb.py --cloud=AWS --benchmarks=intel_mlperf --os_type=ubuntu1804 --machine_type=m5.12xlarge --aws_boot_disk_size=100 --zones=us-east-2 --image=ami-0b51ab7c28f4bf5a6 --intel_mlperf_framework=tensorflow --intel_mlperf_loadgen_scenario=Server --mlperf_count=100 --mlperf_time=60 --mlperf_qps=200 --mlperf_max_latency=0.1 --intel_mlperf_model=resnet50
```

e.g PKB command below to run MLPerf-Tensorflow SingleStream scenario
```
python3 pkb.py --cloud=AWS --benchmarks=intel_mlperf --os_type=ubuntu1804 --machine_type=m5.12xlarge --aws_boot_disk_size=100 --zones=us-east-2 --image=ami-0b51ab7c28f4bf5a6 --intel_mlperf_framework=tensorflow --intel_mlperf_loadgen_scenario=SingleStream --intel_mlperf_batch_size=1 --intel_mlperf_model=resnet50
```

e.g PKB command below to run MLPerf-Tensorflow MultiStream scenario
```
python3 pkb.py --cloud=AWS --benchmarks=intel_mlperf --os_type=ubuntu1804 --machine_type=m5.12xlarge --aws_boot_disk_size=100 --zones=us-east-2 --image=ami-0b51ab7c28f4bf5a6 --intel_mlperf_framework=tensorflow --intel_mlperf_loadgen_scenario=MultiStream --intel_mlperf_model=resnet50 --mlperf_time=600 --mlperf_qps=24576
```

e.g PKB command below to run MLPerf-Tensorflow with accuracy flag set
```
python3 pkb.py --cloud=AWS --benchmarks=intel_mlperf --os_type=ubuntu1804 --machine_type=m5.12xlarge --aws_boot_disk_size=100 --zones=us-east-2 --image=ami-0b51ab7c28f4bf5a6 --intel_mlperf_framework=tensorflow --intel_mlperf_loadgen_scenario=Server --mlperf_count=100 --mlperf_time=60 --mlperf_qps=200 --mlperf_max_latency=0.1 --intel_mlperf_model=resnet50 --mlperf_accuracy=True
```


e.g PKB command below to run MLPerf-v7-Tensorflow SingleStream scenario
```
python3 pkb.py --cloud=AWS --benchmarks=intel_mlperf --os_type=ubuntu2004 --machine_type=m5.12xlarge --aws_boot_disk_size=100 --zones=us-east-2 --intel_mlperf_framework=tensorflow --intel_mlperf_loadgen_scenario=SingleStream --mlperf_inference_version=v0.7 --intel_mlperf_model=resnet50
```

e.g PKB command below to run MLPerf-v7-Openvino Offline scenario (uses data from Cumulus AWS bucket)
```
python3 pkb.py --cloud=AWS --benchmarks=intel_mlperf --os_type=ubuntu2004 --machine_type=m5.12xlarge --aws_boot_disk_size=100 --zones=us-east-2 --intel_mlperf_framework=openvino --intel_mlperf_loadgen_scenario=Offline --mlperf_inference_version=v0.7 --intel_mlperf_model=resnet50
```

e.g PKB command below to run MLPerf-v7-Openvino SingleStream scenario
```
python3 pkb.py --cloud=AWS --benchmarks=intel_mlperf --os_type=ubuntu2004 --machine_type=m5.12xlarge --aws_boot_disk_size=100 --zones=us-east-2 --intel_mlperf_framework=openvino --intel_mlperf_loadgen_scenario=SingleStream --mlperf_inference_version=v0.7 --intel_mlperf_model=resnet50
```

e.g PKB command below to run MLPerf-v7-Openvino Offline scenario using local data from the PKB host
```
python3 pkb.py --cloud=AWS --benchmarks=intel_mlperf --os_type=ubuntu2004 --machine_type=m5.24xlarge --aws_boot_disk_size=100 --zones=us-east-2 --intel_mlperf_framework=openvino --mlperf_inference_version=v0.7 --mlperf_use_local_data=true --imagenet_dataset_localpath=/home/shashi/AI_DATA/imagenet_data.tar.gz --mlperf_ov_repo_localpath=/home/shashi/AI_DATA/mlperf_ext_ov_cpp-master.tar.gz --configs_models_localpath=/home/shashi/AI_DATA/configs_models.tar.gz
```

Like any other benchmark in pkb, the MLPerf has some configuration parameters which can be modified.
They are present in perfkitbenchmarker/data/intel_mlperf/intel_mlperf_config.yml.

The yaml file has the following parameters:
- `mlperf_framework` : This can be `pytorch` or `tensorflow` or `openvino`. default is set to `tensorflow`
- `mlperf_model`: Model to use, e.g. `resnet50`, `ssd-mobilenet-v1`. `resnet50` is the default. `ssd-mobilenet-v1` is only supported in case of OpenVINO framework
- `mlperf_device`: Model to use, e.g. `cpu`, `gpu`. `cpu` is the default.
- `mlperf_loadgen_scenario`:  for Pytorch currently available values are `Offline` which is the default; for Tensorflow available values are {SingleStream, Offline, MultiStream, Server} and for OpenVINO available values are {SingleStream, Offline}
- `mlperf_count`: number of images used in the dataset for accuracy pass. default is set to `-1`
- `mlperf_time`: limits the time the benchmark runs, metric in seconds. default is set to `-1`
- `mlperf_qps`: expected QPS, queries per second. default is set to `-1`
- `mlperf_max_latency`: the latency used for the server mode, metric in seconds. default is set to `-1.0`
- `mlperf_accuracy`: enables accuracy pass. Default is `False`
- `mlperf_use_local_data`: If set to `True` the benchmark will run using local copy of the dataset, else it will access the dataset from cumulus s3 bucket, by default it is set to `False` for Intel internal usage.
- `mlperf_batch_size`: batch size, default is set to `1`.
- `mlperf_num_instances`: Number of MLPerf instances, e.g. for pytorch each instances requires upto 4 cores, default is set to `1`.
- `mlperf_loadgen_mode`: Loadgen mode available values - PerformanceOnly, AccuracyOnly, default value is `PerformanceOnly`.
- `imagenet_dataset_link` and `imagenet_dataset_s3uri`: dowloadable link and s3 bucket link for imagenet dataset ; these flags are used to run `ResNet50` model of Pytorch and OpenVINO frameworks.
- `imagenet_dataset_localpath`**: set this to local path on the pkb host, where imagnet datset(in TF records format) is present e.g. "/opt/data/intel_mlperf/imagenet_data.tar.gz"
- `coco_dataset_link` and `coco_dataset_s3uri`: dowloadable link and s3 bucket link for coco dataset; these flags are used to run `SSD-MobileNet-v1` model of OpenVINO framework.
- `coco_dataset_localpath`**: set this to local path on the pkb host, where coco datset is present e.g. "/opt/data/intel_mlperf/coco_dataset.tar.gz"
- `imagenet_dataset_tensorflow_link` and `imagenet_dataset_tensorflow_s3uri`: dowloadable link and s3 bucket link for imagenet dataset for TensorFlow; these flags are used to run `resnet50` model of Tensorflow framework.
- `imagenet_dataset_tensorflow_localpath`**: set this to local path on the pkb host, where imagnet datset(in TF records format) is present e.g. "/opt/data/intel_mlperf/imagenet_data_tensorflow.tar.gz"
- `prebuilt_int8models_link` and `prebuilt_int8models_s3uri` : dowloadable link and s3 bucket link for pre-built int8 models used for pytorch runs.
- `intel_parallelstudio_link` and `intel_parllelstudio_s3uri` : dowloadable link and s3 bucket link for Intel Parallel Studio 2019 XE composer edition used for pytorch runs.
- `mlperf_ov_repo_url` : The url where the MLPerf-Openvino workload exists e.g. "https://gitlab.devtools.intel.com/mlperf/mlperf_ext_ov_cpp/-/archive/master/mlperf_ext_ov_cpp-master.tar.gz"
- `mlperf_ov_repo_localpath` **: set this to local path on the pkb host, where mlperf-ov repo is present e.g. "/opt/data/mlperf/mlperf_ext_ov_cpp-master.tar.gz"

**To run intel_mlperf workload on baremetal/on-prem server**

To run intel_mlperf workload on a on-prem SUT, provide a benchmark configuration yaml file that specifies the details of SUT e.g. as below
```YAML
static_vms:
  - &vm1
    ip_address: 10.54.38.91
    user_name: pkb
    ssh_private_key: ~/.ssh/id_rsa
    internal_ip: 10.54.38.91

intel_mlperf:
  vm_groups:
    default:
      static_vms:
        - *vm1
```

Use PKB command line flag, --benchmark_config_file, to use above config file. e.g.

```bash
$ python3 pkb.py --benchmarks=intel_mlperf --benchmark_config_file=<path_to>/mlperf_benchmark_config.yaml --intel_mlperf_framework=tensorflow
```


#### Note
Above MLPerf benchmarks need imagenet or coco datasets, user needs to have a copy of the [imagenet](http://image-net.org/) and [coco](https://cocodataset.org/#home) datasets available and update the links and s3uri in the intel_mlperf_config.yml file to point to their copy of the dataset e.g. on aws s3 bucket etc..
The Tensorflow models repo provides scripts and instructions to [download](https://github.com/tensorflow/models/tree/master/research/slim#an-automated-script-for-processing-imagenet-data), process and convert the Imagenet dataset to the TF records format.

**With pkb flag `mlperf_use_local_data=True` one can use local copy the dataset on their PKB host with config param `imagenet_dataset_tensorflow_localpath` for Tensorflow runs and for Openvino runs `imagenet_dataset_localpath` , `coco_dataset_localpath` and  `mlperf_ov_repo_localpath`. The imagenet, coco datasets and mlperf-ov repo should all be in .tar.gz file format.

e.g. PKB command to run MLPerf-Tensorflow using local dataset copy.
```bash
$ python3 pkb.py --cloud=AWS --benchmarks=intel_mlperf --os_type=ubuntu1804 --machine_type=m5.12xlarge --aws_boot_disk_size=100 --intel_mlperf_framework=tensorflow --intel_mlperf_loadgen_scenario=Offline --intel_mlperf_model=resnet50 --mlperf_use_local_data=True --imagenet_dataset_tensorflow_localpath=/opt/data/intel_mlperf/imagenet_data_tensorflow.tar.gz
```
e.g. PKB command to run MLPerf-Openvino using local repo and dataset copy(resnet50 model uses imagenet dataset and ssd-mobilenet-v1 model uses coco dataset).
```bash
$ python3 pkb.py --cloud=AWS --benchmarks=intel_mlperf --os_type=ubuntu1804 --machine_type=m5.12xlarge --aws_boot_disk_size=100 --intel_mlperf_framework=openvino --intel_mlperf_loadgen_scenario=SingleStream --intel_mlperf_model=resnet50 --mlperf_use_local_data=True --imagenet_dataset_localpath=/opt/data/intel_mlperf/imagenet_data.tar.gz --mlperf_ov_repo_localpath=/opt/data/intel_mlperf/mlperf_ext_ov_cpp-master.tar.gz
```
