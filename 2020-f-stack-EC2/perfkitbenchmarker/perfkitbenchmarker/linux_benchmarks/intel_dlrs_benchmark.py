import collections
import posixpath
import logging
import os
import datetime
import yaml
import json
from perfkitbenchmarker import errors
from perfkitbenchmarker import data
from perfkitbenchmarker import configs
from absl import flags
from perfkitbenchmarker import sample
from perfkitbenchmarker import vm_util
from perfkitbenchmarker.linux_packages import INSTALL_DIR

FLAGS = flags.FLAGS
flags.DEFINE_string('intel_dlrs_precision', 'fp32',
                    'Tensorflow model precision type int8 or fp32')
flags.DEFINE_string('intel_dlrs_image_to_use', 'tensorflow_mkl_image',
                    'Tensorflow image to use')
flags.DEFINE_string('intel_dlrs_dataset_to_use', 'synthetic_data',
                    'Dataset to use {synthetic_data,imagenet}')
flags.DEFINE_string('intel_dlrs_models_to_use', 'tf_benchmarks',
                    'AI models to use {tf_benchmarks,intelai}')
flags.DEFINE_string('cumulus_dlrs_registry_username', '',
                    'The username for the Cumulus ECR login')
flags.DEFINE_string('cumulus_dlrs_registry_password', '',
                    'The password for the Cumulus ECR login')
flags.DEFINE_string('cumulus_dlrs_registry_url', '',
                    'The url for the Cumulus ECR login')
GENERATED_CONFIG_FILE = "generated_config.yml"
SCRIPT_CODE = """#!/bin/bash
source /.bashrc
%s
"""
TF_VER_SCRIPT_CODE = SCRIPT_CODE % "python -c 'import tensorflow as tf; " \
                                   "print(tf.__version__)'"
TF_BENCHMARKS_GIT = "https://github.com/tensorflow/benchmarks"
INTELAI_MODELS_GIT = "https://github.com/IntelAI/models"
PYTORCH_BENCHMARKS_GIT = (
    "https://github.com/intel/optimized-models/archive/v1.0.6.tar.gz")
RESNET50_LINK = "https://download.pytorch.org/models/resnet50-19c8e357.pth"
BENCHMARK_ARGS = {"mkl": "", "mode": ""}
CONFIG_FILE = 'intel_dlrs_benchmark/config.yml'
CONFIG_DATA = {}
RESNET50_MODEL_CONVERTER = """
import torch
import torchvision.models as models
from torch.autograd import Variable
model = models.resnet50(pretrained=False)
m = torch.load('resnet50.pth')
model.load_state_dict(m)
model.train(False)
x = Variable(torch.randn(1, 3, 224, 224))
y = model(x)
torch_out = torch.onnx._export(model,
                               x,
                               'resnet50.onnx',
                               export_params=True)
"""

BENCHMARK_NAME = "intel_dlrs"
BENCHMARK_CONFIG = """
intel_dlrs:
  description: Run dlrs
  vm_groups:
    target:
      os_type: clear
      vm_spec:
        GCP:
          machine_type: n1-highcpu-8
          zone: us-east1-b
          boot_disk_size: 100
          min_cpu_platform: "skylake"
        AWS:
          machine_type: c5.2xlarge
          zone: us-east-2
          boot_disk_size: 100
        Azure:
          machine_type: Standard_F8s_v2
          zone: eastus
          boot_disk_size: 100
        OpenStack:
          machine_type: baremetal
          zone: nova
"""


def _ReadConfig():
  with open(data.ResourcePath(CONFIG_FILE)) as cfg_file:
    global CONFIG_DATA
    CONFIG_DATA = yaml.safe_load(cfg_file)
  CONFIG_DATA["image_to_use"] = FLAGS.intel_dlrs_image_to_use
  CONFIG_DATA["precision"] = FLAGS.intel_dlrs_precision


def _ReadGeneratedConfig(path):
  with open(path) as cfg_file:
    config_data = yaml.safe_load(cfg_file)
  return config_data


def _WriteGeneratedConfig(path, config):
  with open(path, "w") as cfg_file:
    yaml.safe_dump(config, cfg_file, default_flow_style=False)


def _GetVmCpuinfo(vm):
  out, _ = vm.RemoteCommand("lscpu | sed -n 's/Socket(s):[ \t]*//p'")
  sockets = int(out.strip())

  out, _ = vm.RemoteCommand("lscpu | sed -n 's/Core(s) per socket:[ \t]*//p'")
  cores_per_socket = int(out.strip())

  out, _ = vm.RemoteCommand("lscpu | sed -n 's/Thread(s) per core:[ \t]*//p'")
  threads_per_core = int(out.strip())

  result = collections.namedtuple('result', [
      "sockets",
      "cores_per_socket",
      "threads_per_core",
      "num_cores",
  ])
  result.sockets = sockets
  result.cores_per_socket = cores_per_socket
  result.threads_per_core = threads_per_core
  result.num_cores = sockets * cores_per_socket
  return result


def _GetLogs(vm, logdir):
  timestamp = datetime.datetime.today().strftime("%Y%m%d%H%M%S%f")
  logs_archive_vm = posixpath.join(INSTALL_DIR, "dlrs-logs.tar.gz")
  vm.RemoteCommand("tar czf {archive} -C {log_dir} ."
                   .format(archive=logs_archive_vm, log_dir=logdir))
  logs_archive = (os.path.join(vm_util.GetTempDir(),
                               'dlrs-logs-{time_stamp}.tar.gz'
                               .format(time_stamp=timestamp)))
  vm.PullFile(logs_archive, logs_archive_vm)


def _DownloadDataset(vm, destination):
  logging.info("Downloading dataset")
  imagenet_tar_name = ('imagenet.{0}'.format
                       (CONFIG_DATA["dataset_link"][CONFIG_DATA["dataset_link"]
                                                    .rindex(".") + 1:]))
  imagenet_path = posixpath.join(INSTALL_DIR, imagenet_tar_name)
  retcode = 1
  try:
    vm.Install('aws_credentials')
    vm.Install('awscli')
    _, _, retcode = vm.RemoteCommandWithReturnCode(
        "aws s3 cp {0} {1}".format(CONFIG_DATA["dataset_S3Uri"], imagenet_path),
        ignore_failure=True)
  except:
    if retcode != 0:
      vm.RemoteCommand("curl -o {0} {1}".format(imagenet_path,
                                                CONFIG_DATA["dataset_link"]))
  vm.RemoteCommand("mkdir -p {dst} && sudo chmod 775 {dst} && "
                   "tar -xf {img_net_tgz} --strip-components=1 -C {dst}"
                   .format(dst=destination, img_net_tgz=imagenet_path))


def CheckPrerequisites(benchmark_config):
  """Verifies that the required configs are present.

  Raises:
    perfkitbenchmarker.errors.Config.InvalidValue: On invalid value.
  """
  if FLAGS["cumulus_dlrs_registry_username"].present:
    if len(FLAGS.cumulus_dlrs_registry_username.strip()) == 0:
      raise errors.Config.InvalidValue("The Cumulus Docker registry username cannot be empty."
                                       "Please provide username")
    if FLAGS["cumulus_dlrs_registry_password"].present:
      if len(FLAGS.cumulus_dlrs_registry_password.strip()) == 0:
        raise errors.Config.InvalidValue("The Docker registry password cannot be empty."
                                         "Please provide password")
    else:
      raise errors.Config.InvalidValue("You provided a Docker registry username,"
                                       "but no password.Please provide password")


def GetConfig(user_config):
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
  return config


def _GenerateAixprtConfig(batch_sz, num_inst, precision):
  """Generate AIXPRT config for config json file

  Args:
      batch_sz: batch size for the aixprt workload
      num_inst: number of concurrent instances = num of vCPUs
      precision: precision - int8/fp32

  Returns:
      AIXPRT config file path
  """
  aixprt_config = {
      "delayBetweenWorkloads": 0,
      "isDemo": False,
      "iteration": 1,
      "module": "Deep-Learning",
      "runtype": "performance",
      "workloads_config": [
          {
              "batch_sizes": batch_sz,
              "concurrent_instances": num_inst,
              "hardware": "cpu",
              "name": "ResNet-50",
              "precision": precision,
              "runtype": "performance",
              "total_requests": 1000
          }
      ]
  }
  ai_filename = "Throughput_{prec}.json".format(prec=precision)
  ai_filepath = posixpath.join(vm_util.GetTempDir(), ai_filename)
  with open(ai_filepath, "w") as aixprt_config_file:
    aixprt_config_file.write(json.dumps(aixprt_config, indent=4))
  return ai_filepath


def _DownloadBenchmarkCode(vm):
  logging.info("Downloading benchmark code")
  intelai_ver_num = "v1.3.0"
  if BENCHMARK_ARGS["image_type"] == "pytorch":
    archive_path = posixpath.join(INSTALL_DIR, "benchmarks.tar.gz")
    vm.RemoteCommand("curl -o {archive} {pytorch} "
                     .format(archive=archive_path, pytorch=PYTORCH_BENCHMARKS_GIT))
    BENCHMARK_ARGS["benchmarks_dir"] = posixpath.join(INSTALL_DIR,
                                                      "benchmarks")
    vm.RemoteCommand("mkdir -p {dst} && sudo chmod 775 {dst} && "
                     "tar -xf {img_net_tgz} --strip-components=1 -C {dst}"
                     .format(dst=BENCHMARK_ARGS["benchmarks_dir"],
                             img_net_tgz=archive_path))
    vm.RemoteCommand("curl -o {benchmark_dir} {link}"
                     .format(benchmark_dir=posixpath.
                             join(BENCHMARK_ARGS["benchmarks_dir"],
                                  "resnet50.pth"), link=RESNET50_LINK))
    vm.RemoteCommand('echo "{resnet_model_converter}" > '
                     '{conv_path} && chmod 775 {conv_path}'
                     .format(resnet_model_converter=RESNET50_MODEL_CONVERTER,
                             conv_path=posixpath.join
                             (BENCHMARK_ARGS["benchmarks_dir"], "conv.py")))
  elif CONFIG_DATA["image_to_use"] == "tensorflow_mkl_aixprt":
    local_aixprt_config = _GenerateAixprtConfig(CONFIG_DATA["batch_sizes"],
                                                BENCHMARK_ARGS["total_vcpus"],
                                                BENCHMARK_ARGS["precision"])
    ai_filename = "Throughput_{prec}.json".format(
        prec=BENCHMARK_ARGS["precision"])
    dest_path = posixpath.join(INSTALL_DIR, ai_filename)
    vm.PushFile(local_aixprt_config, dest_path)
    return
  else:
    BENCHMARK_ARGS["benchmarks_dir"] = (
        posixpath.join(INSTALL_DIR,
                       TF_BENCHMARKS_GIT[TF_BENCHMARKS_GIT.rindex('/') + 1:]))
    BENCHMARK_ARGS["models_dir"] = posixpath.join(INSTALL_DIR, "models")
    if FLAGS.intel_dlrs_models_to_use.lower() == "intelai":
      vm.RemoteCommand("cd {install_dir}; git clone -b {version} {intelai}"
                       .format(install_dir=INSTALL_DIR,
                               version=intelai_ver_num,
                               intelai=INTELAI_MODELS_GIT))
      vm.RemoteCommand("cd {models_dir}; curl -O {int8_model}; curl -O {fp32_model}"
                       .format(models_dir=BENCHMARK_ARGS["models_dir"],
                               int8_model=CONFIG_DATA["intel_resnet50_int8_pretrained_model"],
                               fp32_model=CONFIG_DATA["intel_resnet50_fp32_pretrained_model"]))
    else:
      vm.RemoteCommand("cd {install_dir}; git clone {tf_git}".format
                       (install_dir=INSTALL_DIR, tf_git=TF_BENCHMARKS_GIT))


def Prepare(benchmark_spec):
  vm = benchmark_spec.vms[0]
  _ReadConfig()
  global BENCHMARK_ARGS
  BENCHMARK_ARGS["train"] = CONFIG_DATA["train"]
  BENCHMARK_ARGS["model"] = CONFIG_DATA["model"]
  BENCHMARK_ARGS["data_format"] = CONFIG_DATA["data_format"]
  logging.info("Obtaining Cpu Information")
  cpuinfo = _GetVmCpuinfo(vm)
  BENCHMARK_ARGS["total_vcpus"] = vm.NumCpusForBenchmark()
  BENCHMARK_ARGS["inter_threads"] = cpuinfo.sockets
  BENCHMARK_ARGS["intra_threads"] = cpuinfo.cores_per_socket * cpuinfo.sockets
  BENCHMARK_ARGS["precision"] = CONFIG_DATA["precision"]
  BENCHMARK_ARGS["docker_runtime"] = CONFIG_DATA["docker_runtime"]
  BENCHMARK_ARGS["dataset"] = FLAGS.intel_dlrs_dataset_to_use.lower()
  benchmark_spec.always_call_cleanup = True
  if not BENCHMARK_ARGS["train"]:
    BENCHMARK_ARGS["mode"] = "--forward_only=True"

  # Install packages
  logging.info("Installing packages")
  vm.Install('docker_ce')
  vm.InstallPackages('git')
  vm.RemoteCommand("sudo systemctl start docker")

  if "kata" in CONFIG_DATA["docker_runtime"]:
    # Install Kata Containers
    logging.info("Installing Kata Containers")
    vm.Install("kata")
    vm.RemoteCommand("sudo kata-runtime kata-check")

  # Pull images with either eigen or mkl
  logging.info("Pulling docker image")

  BENCHMARK_ARGS["image"] = CONFIG_DATA["images"][CONFIG_DATA["image_to_use"]]
  BENCHMARK_ARGS["image_type"] = (CONFIG_DATA["image_to_use"]
                                  [:CONFIG_DATA["image_to_use"].
                                   index('_')].lower())
  if FLAGS.cumulus_dlrs_registry_username != "":
    retry_count = 0
    while retry_count < 3:
      retry_count = retry_count + 1
      vm.RemoteCommand("sudo docker login --username {username} --password {password} {url}"
                       .format(
                           username=FLAGS.cumulus_dlrs_registry_username,
                           password=FLAGS.cumulus_dlrs_registry_password,
                           url=FLAGS.cumulus_dlrs_registry_url
                       ))
  if "mkl" in BENCHMARK_ARGS["image"]:
    BENCHMARK_ARGS["math_libraries"] = "MKL-DNN"
    BENCHMARK_ARGS["mkl"] = "--mkl=True"
  vm.RemoteCommand("sudo docker pull {}".format(BENCHMARK_ARGS["image"]))

  # Download benchmark code
  _DownloadBenchmarkCode(vm)

  # Download dataset
  destination = posixpath.join(INSTALL_DIR, "IMAGENET_DIR")
  BENCHMARK_ARGS["data_dir"] = destination
  if FLAGS.intel_dlrs_dataset_to_use.lower() == "imagenet":
    _DownloadDataset(vm, destination)


def _GetDockerRunCommand():
  if FLAGS.intel_dlrs_models_to_use.lower() == "intelai":
    if FLAGS.intel_dlrs_dataset_to_use.lower() == "imagenet":
      docker_run_cmd = "sudo docker run --privileged -id -v " \
                       "{models_dir}:/models -v " \
                       "{data_dir}:/imagenet --rm {image}"\
          .format(**BENCHMARK_ARGS)
    else:
      docker_run_cmd = "sudo docker run --privileged -id -v " \
                       "{models_dir}:/models " \
                       "--rm {image}".format(**BENCHMARK_ARGS)
  elif CONFIG_DATA["image_to_use"] == "tensorflow_mkl_aixprt":
    docker_run_cmd = "sudo docker run --privileged -id --rm {image}".format(**BENCHMARK_ARGS)
  else:
    if FLAGS.intel_dlrs_dataset_to_use.lower() == "imagenet":
      docker_run_cmd = "sudo docker run --privileged -id " \
                       "-v {benchmarks_dir}:/benchmarks " \
                       "-v {data_dir}:/imagenet " \
                       "--rm {image}".format(**BENCHMARK_ARGS)
    else:
      docker_run_cmd = "sudo docker run --privileged -id " \
                       "-v {benchmarks_dir}:/benchmarks " \
                       "--rm {image}".format(**BENCHMARK_ARGS)
  return docker_run_cmd


def _GetIntelaiFp32Command():
  cmd = "python /models/benchmarks/launch_benchmark.py " \
        "--in-graph /models/resnet50_fp32_pretrained_model.pb " \
        "--model-name {model} --framework tensorflow --precision " \
        "{precision} --mode inference --batch-size={batch_size} " \
        "--socket-id 0 --num-inter-threads=1 --num-intra-threads=" \
        "{intra_threads} --num-cores={intra_threads}".format(**BENCHMARK_ARGS)
  return cmd


def _GetIntelaiInt8Command():
  cmd = "python /models/benchmarks/launch_benchmark.py " \
        "--in-graph /models/resnet50_int8_pretrained_model.pb " \
        "--model-name {model} --framework tensorflow --precision " \
        "{precision} --data-num-inter-threads=1 " \
        "--data-num-intra-threads={intra_threads} " \
        "--mode inference --batch-size={batch_size} --socket-id 0 " \
        "--num-inter-threads=1 --num-intra-threads={intra_threads} " \
        "--num-cores={intra_threads}".format(**BENCHMARK_ARGS)
  if FLAGS.intel_dlrs_dataset_to_use.lower() == "imagenet":
    cmd = cmd + " --data-location=/imagenet/"
  return cmd


def _GetCommandToLaunchBenchmark(cmd):
  # Create the command to launch the benchmark
  if (FLAGS.intel_dlrs_models_to_use.lower() == "intelai" and
      BENCHMARK_ARGS["precision"].lower() == "int8"):
    # ResNet50 INT8 VNNI inference only with MKL image
    cmd = _GetIntelaiInt8Command()
  elif (FLAGS.intel_dlrs_models_to_use.lower() == "intelai" and
        BENCHMARK_ARGS["precision"].lower() == "fp32"):
    # ResNet50 FP32+AVX512 inference only with MKL image
    cmd = _GetIntelaiFp32Command()
  else:
    # default FLAGS.intel_dlrs_models_to_use is = "tf_benchmarks"
    if FLAGS.intel_dlrs_dataset_to_use.lower() == "imagenet":
      cmd = "python " \
            "/benchmarks/scripts/tf_cnn_benchmarks/tf_cnn_benchmarks.py " \
            "--device=cpu --nodistortions {mkl} {mode} " \
            "--data_format={data_format} --model={model} " \
            "--data_dir=/imagenet/ --data_name=imagenet " \
            "--num_inter_threads={inter_threads} " \
            "--num_intra_threads={intra_threads} " \
            "--batch_size={batch_size}".format(**BENCHMARK_ARGS)
    else:
      cmd = "python " \
            "/benchmarks/scripts/tf_cnn_benchmarks/tf_cnn_benchmarks.py " \
            "--device=cpu --nodistortions {mkl} {mode} " \
            "--data_format={data_format} --model={model} " \
            "--num_inter_threads={inter_threads} " \
            "--num_intra_threads={intra_threads} " \
            "--batch_size={batch_size}".format(**BENCHMARK_ARGS)
  return cmd


def _ReadAIXPRTResults(out, vm, logdir):
  """Read AIXPRT Results and gather metrics

  Args:
      out: output after docker exec command
      vm: vm from benchmark_spec
      logidr: pkb logs dir location

  Returns:
      Dictionary object of results
  """
  results_file_path = None
  result_obj = None
  for line in reversed(out.splitlines()):
    if "Completed running" in line and line.endswith(".json"):
      results_file_path = line.rsplit(' ', 1)[1]
      file_name = os.path.basename(results_file_path)
  if results_file_path is not None:
    vm.RemoteCommand("sudo docker cp {container_id}:{file_path} {log_dir}"
                     .format(container_id=BENCHMARK_ARGS["container_id"],
                             file_path=results_file_path, log_dir=logdir))
    aixprt_results_file_path = posixpath.join(logdir, file_name)
    vm.PullFile(vm_util.GetTempDir(), aixprt_results_file_path)
    aixprt_results_file = os.path.join(vm_util.GetTempDir(), file_name)
    with open(aixprt_results_file, 'r') as json_file:
      aixprt_results = json.load(json_file)
      for item in aixprt_results['Result']["Deep-Learning"]['Workloads']:
        json_results = item.get('results')
        for obj in json_results:
          if obj.get('system_throughput_units') == 'imgs/sec':
            result_obj = obj
            result_obj.update(item.get("workload run information"))
  else:
    logging.info("AIXPRT results file not found")
  return result_obj


def _GetThroughputMetrics(out, throughput_search_string):
  # Get relevant metrics from output
  imgs_per_sec = 0
  if FLAGS.intel_dlrs_models_to_use.lower() == "intelai":
    for line in reversed(out.splitlines()):
      if line.startswith("Throughput:") and line.endswith("images/sec"):
        idx = line.find("Throughput:")
        if idx > -1:
          imgs_per_sec = float(line.split()[1])
          break
  else:
    for line in reversed(out.splitlines()):
      idx = line.find(throughput_search_string)
      if idx > -1:
        imgs_per_sec = (float(line[idx +
                                   len(throughput_search_string):].strip()))
        break
  return imgs_per_sec


def Run(benchmark_spec):
  docker_exec_cmd = "sudo docker exec -i %s %s"
  if FLAGS.intel_dlrs_models_to_use.lower() == "intelai":
    script_in_docker = ('echo "{script_code}" > '
                        '{models_dir}/{file}; chmod +x {models_dir}/{file}')
  else:
    script_in_docker = ('echo "{script_code}" > '
                        '{benchmarks_dir}/{file}; '
                        'chmod +x {benchmarks_dir}/{file}')
  vm = benchmark_spec.vms[0]

  # Create logdir
  logdir = posixpath.join(INSTALL_DIR, "logs")
  vm.RemoteCommand("mkdir -p {logdir} ; "
                   "chmod 777 {logdir}".format(logdir=logdir))
  # Launch docker container
  docker_run_cmd = _GetDockerRunCommand()
  container_id, _ = vm.RemoteCommand(docker_run_cmd)
  container_id = container_id.strip()
  BENCHMARK_ARGS["container_id"] = container_id
  BENCHMARK_ARGS["batch_size"] = "{batch_size}"
  cmd_in_container = ""
  throughput_search_string = ""
  if BENCHMARK_ARGS["image_type"] == "pytorch":
    BENCHMARK_ARGS["intra_threads"] -= 1
    if BENCHMARK_ARGS["train"]:
      cmd_in_container = "numactl --physcpubind=0-{intra_threads} " \
                         "--membind=0 python3.7 " \
                         "/benchmarks/pytorch/benchmark_tools/run_caffe2.py " \
                         "-m resnet50 -tp /imagenet/dataset_train/train " \
                         "-l /imagenet/dataset_train/train.txt -r training " \
                         "-w 5 -d cpu -b {batch_size} -i 1 " \
                         "-e error ".format(**BENCHMARK_ARGS)
    else:
      cmd_in_container = "numactl --physcpubind=0-{intra_threads} " \
                         "--membind=0 python3.7 " \
                         "/benchmarks/pytorch/benchmark_tools/run_caffe2.py " \
                         "-m resnet50 -p /imagenet/ILSVRC2012_img_val " \
                         "-v /imagenet/val.txt -w 5 -d cpu -b {batch_size} " \
                         "-i 1 -e error -onnx".format(**BENCHMARK_ARGS)
    throughput_search_string = "Images per second:"
    # Convert model to onnx
    script_code = (SCRIPT_CODE %
                   "cd /benchmarks && python3.7 conv.py && cp resnet50.onnx "
                   "pytorch/benchmark_tools/inference/models/resnet50")
    vm.RemoteCommand(script_in_docker.format(
        script_code=script_code,
        benchmarks_dir=BENCHMARK_ARGS["benchmarks_dir"], file="conv.sh"))
    cmd = docker_exec_cmd % (container_id, "/benchmarks/conv.sh")
    vm.RemoteCommand(cmd)
  elif CONFIG_DATA["image_to_use"] == "tensorflow_mkl_aixprt":
    WORKSPACE = "/workspace"
    ai_file_vm = posixpath.join(INSTALL_DIR,
                                "Throughput_{}.json".format
                                (BENCHMARK_ARGS["precision"]))
    aixprt_config_container = posixpath.join(WORKSPACE, "AIXPRT", "Config")
    vm.RemoteCommand("sudo docker cp {config} {container}:{config_path}"
                     .format(config=ai_file_vm, container=container_id,
                             config_path=aixprt_config_container))
    cmd_in_container = "bash {0}".format(posixpath.join(WORKSPACE,
                                                        "aixprt",
                                                        "run_aixprt.sh"))
  else:
    if FLAGS.intel_dlrs_models_to_use.lower() == "tf_benchmarks":
      # Check the tf version in the container
      vm.RemoteCommand(script_in_docker.format(
          script_code=TF_VER_SCRIPT_CODE,
          benchmarks_dir=BENCHMARK_ARGS["benchmarks_dir"], file="ver.sh"))
      out, _ = vm.RemoteCommand(docker_exec_cmd % (
          container_id, "/benchmarks/ver.sh"))
      tf_ver = out.strip()

      # Change the benchmark branch in order to match the tf version
      benchmark_branch = "cnn_tf_v{}_compatible".format(tf_ver[:tf_ver.rfind('.')])
      vm.RemoteCommand("cd {benchmark_dir}; git checkout {branch}; git pull"
                       .format(benchmark_dir=BENCHMARK_ARGS["benchmarks_dir"],
                               branch=benchmark_branch))
      throughput_search_string = "total images/sec:"
    else:
      throughput_search_string = "images/sec:"

    # Create the command to launch the benchmark
    cmd_in_container = _GetCommandToLaunchBenchmark(cmd_in_container)
  if (BENCHMARK_ARGS["mkl"] and
      FLAGS.intel_dlrs_models_to_use.lower() == "tf_benchmarks"):
    script_code = SCRIPT_CODE % (cmd_in_container.format(batch_size=r"\$1"))
    if FLAGS.intel_dlrs_models_to_use.lower() == "tf_benchmarks":
      vm.RemoteCommand(script_in_docker.format(
          script_code=script_code,
          benchmarks_dir=BENCHMARK_ARGS["benchmarks_dir"], file="start.sh"))
      cmd_in_container = "/benchmarks/start.sh {batch_size}"
    else:
      vm.RemoteCommand(script_in_docker.format(
          script_code=script_code,
          benchmarks_dir=BENCHMARK_ARGS["models_dir"], file="start.sh"))
  cmd = docker_exec_cmd % (container_id, cmd_in_container)
  # Run the benchmark
  batches = CONFIG_DATA["batch_sizes"]
  repeat_count = CONFIG_DATA["repeat_count"]
  results = []
  for batch in batches:
    for i in range(repeat_count):
      complete_cmd = cmd.format(batch_size=batch)
      out, _ = vm.RemoteCommand(complete_cmd)
      vm.RemoteCommand('echo "{out}" > '
                       '{logdir}/batch_{batch_size}_iter_{rep}.log'.
                       format(out=out, logdir=logdir, batch_size=batch, rep=i))

      # Get relevant metrics from output
      imgs_per_sec = 0
      if CONFIG_DATA["image_to_use"] == "tensorflow_mkl_aixprt":
        result_obj = _ReadAIXPRTResults(out, vm, logdir)
        if result_obj is not None:
          batch = int(result_obj.get('label').rsplit(' ', 1)[1])
          imgs_per_sec = result_obj.get('system_throughput')
          BENCHMARK_ARGS["aixprt_results"] = str(result_obj)
      else:
        imgs_per_sec = _GetThroughputMetrics(out, throughput_search_string)
      # Get GCC version
      gcc_version, _ = vm.RemoteCommand('gcc --version | head -n 1', retries=1, ignore_failure=True)
      BENCHMARK_ARGS["gcc_version"] = gcc_version
      BENCHMARK_ARGS["batch_size"] = batch
      metadata = BENCHMARK_ARGS
      results.append(sample.Sample(
          "Throughput", imgs_per_sec, "Images/sec", metadata))

  logging.info("Downloading logs")
  _GetLogs(vm, logdir)
  _WriteGeneratedConfig(os.path.join(vm_util.GetTempDir(),
                                     GENERATED_CONFIG_FILE), BENCHMARK_ARGS)
  return results


def Cleanup(benchmark_spec):
  vm = benchmark_spec.vms[0]
  BENCHMARK_ARGS = _ReadGeneratedConfig(
      os.path.join(vm_util.GetTempDir(), GENERATED_CONFIG_FILE))
  cmds = [
      "sudo docker rm -f {0}".format(BENCHMARK_ARGS["container_id"]),
      "sudo docker rmi {0}".format(BENCHMARK_ARGS["image"]),
  ]
  vm.RemoteCommand(' && '.join(cmds))
