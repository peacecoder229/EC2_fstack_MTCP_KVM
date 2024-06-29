## Intel DLRS benchmark guidelines

#### Benchmark description
Cumulus-PKB v1.4.intel has DLRS stack v1, v3 and v4 versions integrated.
DLRS v1 stack uses the official [tensorflow cnn benchmarks](https://github.com/tensorflow/benchmarks/tree/master/scripts/tf_cnn_benchmarks)
and DLRS v3 stack uses Intel optimized AI models [intelai](https://github.com/IntelAI/models) and
DLRS v4 stack uses Intel AIXPRT tool [aixprt](https://gitlab.devtools.intel.com/epark/AIXPRT) and OpenVINO tool kit.

Use the flag --intel_dlrs_models_to_use to choose either v1,v3 or v4 version of the stack.
Default is set to use v1 stack.


## How to run DLRS with PKB
Get the code
```
git clone https://gitlab.devtools.intel.com/PerfKitBenchmarker/perfkitbenchmarker.git
```
Run on AWS
```
python3 pkb.py --cloud=AWS --benchmarks=intel_dlrs --os_type=ubuntu1804 --zones=us-east-1b
--machine_type=c5.24xlarge --intel_dlrs_models_to_use=intelai --intel_dlrs_precision=int8
```
e.g to run DLRS-v4 stack on AWS, make use of tensorflow_mkl_aixprt image as below
```
python3 pkb.py --cloud=AWS --benchmarks=intel_dlrs --os_type=ubuntu1804 --machine_type=m5.12xlarge --intel_dlrs_image_to_use=tensorflow_mkl_aixprt
--cumulus_dlrs_registry_username=AWS --cumulus_dlrs_registry_url=https://177285167832.dkr.ecr.us-east-2.amazonaws.com/dlrs
--cumulus_dlrs_registry_password=`aws ecr get-login --no-include-email --region us-east-2 | awk '{print $6}'`
```
Note: DLRS v4 stack pulls the modified stacks-tensorflow-mkl image from the Cumulus ECR repo. This image comes with AIXPRT pre-installed and this
image is based off of amr-registry-pre.caas.intel.com/clearlinux/stacks-tensorflow-mkl:1790_AIXPRT.

Run on on-prem server
```
python3 pkb.py --benchmark_config_file=~/baremetal_dlrs_config.yaml --benchmarks=intel_dlrs --os_type=ubuntu1804
--intel_dlrs_models_to_use=tf_benchmarks --intel_dlrs_precision=fp32
```

Flags that can be passed to above pkb command are
- `--intel_dlrs_models_to_use` = {tf_benchmarks, intelai}
- `--intel_dlrs_precision` = {fp32, int8}
- `--intel_dlrs_dataset_to_use` = {synthetic_data, imagenet}
- `--intel_dlrs_image_to_use` = {tensorflow_mkl_image, ..}

Like any other benchmark in pkb, the DLRS has some configuration parameters which can be modified.
They are present in [perfkitbenchmarker/data/intel_dlrs_benchmark/config.yml](config.yml).

The yaml file has the following parameters:
- `data_format` . This can be either `NHWC` or `NCHW`. Only `NHWC` is supported on cpu so we use this by default.
- `model`. Model to use, e.g. `resnet50`, `inception3`, `vgg16`, and `alexnet`. `resnet50` is the default.
- `docker_runtime`.  Docker runtime to use, the available values are `runc` which is the default and `kata`. Note that `kata` will work only on baremetal machines.
- `train`. If set to `True` the benchmark will run in train mode else it will run it inference mode, by default it is set to `False`.
- `repeat_count`. Number of iterations the benchmark will run for each batch size. e.g if we have 2 `batch_sizes` and `repeat_count` is set to 3, we will have 6 runs in total. Default is set to 1.
- `batch_sizes`. This parameter is a list of batch sizes. Its default value is `[128]`.
- `dataset_link` and `dataset_S3Uri`. Link and aws s3 bucket uri to the dataset. Replace with link and uri for your copy of imagenet dataset.
- `intel_resnet50_int8_pretrained_model` and `intel_resnet50_fp32_pretrained_model` . links to download pre-trained resnet50 models
- `images`. Dictionary which contains the available docker images.
- `image_to_use`. Choose one from the `images` defined above. Default is `tensorflow_mkl_image`.

Note: Tags are mutable whereas sha256 identifier guarantees that every instance of the service is running exactly the same code.
In order to maintain container image revision control `images` dictionary in the above config.yml takes
sha256 identifier for the images instead of tags. e.g.
```
tensorflow_mkl_image: "clearlinux/stacks-dlrs-mkl@sha256:b6e9f25f90c71c4e76c5109b94dc6d56fb8c7204e68d4d262bbc40c5d7b943dc"
`image_to_use`: tensorflow_mkl_image
```


#### Note
DLRS will run on imagenet(synthetic-data) by default, to make runs on actual imagenet dataset, user needs to have a copy of the [imagenet](http://image-net.org/) dataset available and update the links in the config.yml file params `dataset_link` and `dataset_S3Uri` to point to their copy of the dataset.
The Tensorflow models repo provides scripts and instructions to [download](https://github.com/tensorflow/models/tree/master/research/slim#an-automated-script-for-processing-imagenet-data), process and convert the Imagenet dataset to the TF records format.
