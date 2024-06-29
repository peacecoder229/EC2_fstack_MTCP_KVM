"""Utilities for running MLPerf workloads"""

import json
import logging
import collections
import os
import re
import posixpath
from six import StringIO
import yaml

from perfkitbenchmarker import data
from perfkitbenchmarker import errors
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import sample
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import temp_dir

INFERENCE_DIR = posixpath.join('$HOME', "inference")
LOADGEN_DIR = posixpath.join(INFERENCE_DIR, "loadgen")


def _GetVmCpuinfo(vm):
  """Returns cpu info for vm"""
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
      "omp_num_threads",
  ])
  result.sockets = sockets
  result.cores_per_socket = cores_per_socket
  result.threads_per_core = threads_per_core
  result.num_cores = sockets * cores_per_socket
  result.omp_num_threads = threads_per_core
  return result


def _ReadConfig():
  """Reads intel_mlperf config yml from pkb data/intel_mlperf/ dir"""
  mlperf_dir = "intel_mlperf"
  mlperf_config = "intel_mlperf_config.yml"
  config_file = posixpath.join(mlperf_dir, mlperf_config)
  config_data = {}
  with open(data.ResourcePath(config_file)) as cfg_file:
    config_data = yaml.safe_load(cfg_file)
  return config_data


def CheckServerScenarioPrereqs(flags):
  """Verifies that the required configs are present for Server scenario.

  Raises:
    perfkitbenchmarker.errors.Config.InvalidValue: On invalid value.
  """
  if (flags.mlperf_count == -1) | (flags.mlperf_time == -1) | \
     (flags.mlperf_qps == -1) | (flags.mlperf_max_latency == -1.0):
    raise errors.Config.InvalidValue(
        'To run MLPerf-Tensorflow in Server scenario please set a valid value '
        'for mlperf_count|mlperf_time|mlperf_qps|mlperf_max_latency')


def CheckMultiStreamScenarioPrereqs(flags):
  """Verifies that the required configs are present for MultiStream scenario.

  Raises:
    perfkitbenchmarker.errors.Config.InvalidValue: On invalid value.
  """
  if (flags.mlperf_time == -1) | (flags.mlperf_qps == -1):
    raise errors.Config.InvalidValue(
        'To run MLPerf-Tensorflow in MultiStream scenario please set a valid '
        'value for mlperf_time|mlperf_qps')


def UpdateBenchmarkSpecWithConfig(benchmark_spec):
  """Update the benchmark_spec with intel_mlperf config yml values.

  Args:
    benchmark_spec: benchmark specification to update
  """
  logging.info("Updating Benchmark spec with intel_mlperf config")
  config = _ReadConfig()
  benchmark_spec.mlperf_framework = config["mlperf_framework"]
  benchmark_spec.mlperf_batch_size = config["mlperf_batch_size"]
  benchmark_spec.mlperf_loadgen_scenario = config["mlperf_loadgen_scenario"]
  benchmark_spec.mlperf_num_instances = config["mlperf_num_instances"]
  benchmark_spec.mlperf_model = config["mlperf_model"]
  benchmark_spec.mlpert_device = config["mlperf_device"]
  benchmark_spec.mlperf_loadgen_mode = config["mlperf_loadgen_mode"]
  benchmark_spec.mlperf_count = config["mlperf_count"]
  benchmark_spec.mlperf_time = config["mlperf_time"]
  benchmark_spec.mlperf_qps = config["mlperf_qps"]
  benchmark_spec.mlperf_max_latency = config["mlperf_max_latency"]
  benchmark_spec.mlperf_accuracy = config["mlperf_accuracy"]
  benchmark_spec.mlperf_use_local_data = config["mlperf_use_local_data"]
  benchmark_spec.imagenetdata_tensorflow_localpath = config[
      "imagenet_dataset_tensorflow_localpath"]
  benchmark_spec.imagenetdata_openvino_localpath = config[
      "imagenet_dataset_localpath"]
  benchmark_spec.coco_dataset_localpath = config["coco_dataset_localpath"]
  benchmark_spec.squad_dataset_localpath = config["squad_dataset_localpath"]
  benchmark_spec.mlperfov_repo_localpath = config["mlperf_ov_repo_localpath"]
  benchmark_spec.mlperf_v7_ov_cfg_models = config["configs_models_localpath"]
  benchmark_spec.mlperfov_repo_url = config["mlperf_ov_repo_url"]


def UpdateBenchmarkSpecWithFlags(benchmark_spec, mlperf_params):
  """Update the benchmark_spec with supplied command line flags.

  Args:
    benchmark_spec: benchmark specification to update
    mlperf_params: dictionary for supplied CLI flags
  """
  logging.info("Updating Benchmark spec with cli flags")
  benchmark_spec.mlperf_framework = mlperf_params["framework"]
  benchmark_spec.mlperf_version = mlperf_params["mlperf_version"]
  benchmark_spec.mlperf_batch_size = mlperf_params["batch_sz"]
  benchmark_spec.mlperf_loadgen_scenario = mlperf_params["scenario"]
  benchmark_spec.mlperf_num_instances = mlperf_params["num_inst"]
  benchmark_spec.mlperf_model = mlperf_params["model"]
  benchmark_spec.mlperf_device = mlperf_params["device"]
  benchmark_spec.mlperf_loadgen_mode = mlperf_params["mode"]
  benchmark_spec.mlperf_count = mlperf_params["count"]
  benchmark_spec.mlperf_time = mlperf_params["time"]
  benchmark_spec.mlperf_qps = mlperf_params["qps"]
  benchmark_spec.mlperf_max_latency = mlperf_params["max_latency"]
  benchmark_spec.mlperf_accuracy = mlperf_params["accuracy"]
  benchmark_spec.mlperf_use_local_data = mlperf_params["use_local_data"]
  benchmark_spec.imagenetdata_tensorflow_localpath = mlperf_params[
      "local_datapath"]
  benchmark_spec.imagenetdata_openvino_localpath = mlperf_params[
      "local_datapath_ov"]
  benchmark_spec.coco_dataset_localpath = mlperf_params["local_cocodata_ov"]
  benchmark_spec.squad_dataset_localpath = mlperf_params["local_squaddata_ov"]
  benchmark_spec.mlperfov_repo_localpath = mlperf_params["local_mlperfov_repo"]
  benchmark_spec.mlperf_v7_ov_cfg_models = mlperf_params["local_cfg_models_ov7"]
  benchmark_spec.mlperfov_repo_url = mlperf_params["openvino_url"]
  benchmark_spec.mlperf_v7_ov_repo_url = mlperf_params["mlperfv7_openvino_url"]


def _PrepareMLPerfTensorflow(benchmark_spec):
  vm = benchmark_spec.vms[0]
  logging.info("Installing required packages for MLPerf-Tensorflow benchmark and building MLPerf")
  prereq_pkgs = ["python3", "python3-pip", "git", "gcc"]
  vm.InstallPackages(' '.join(prereq_pkgs))

  PYTHON_PKGS = ['tensorflow']
  for pkg in PYTHON_PKGS:
    vm.RemoteHostCommand('pip3 install {pkg}'.format(pkg=pkg))

  if benchmark_spec.mlperf_version == "v0.7":
    branch = "r0.7"
    benchmark_spec.CND_DIR = posixpath.join(INFERENCE_DIR, "vision",
                                            "classification_and_detection")
  else:
    branch = "r0.5"
    benchmark_spec.CND_DIR = posixpath.join(INFERENCE_DIR, "v0.5",
                                            "classification_and_detection")
  vm.RemoteCommand("git clone --recurse-submodules "
                   "https://github.com/mlperf/inference.git -b {br}".format(br=branch))
  if benchmark_spec.mlperf_use_local_data:
    _CopyLocalDataset(benchmark_spec)
  else:
    _DownloadDataset(vm)
  commands = [
      'pip3 install pybind11 absl-py',
      'pip3 install --upgrade cython',
      'cd {loadgen}'.format(loadgen=LOADGEN_DIR),
      'CFLAGS=\"-std=c++14\" python3 setup.py develop --user ',
      'cd {cd_dir} '.format(cd_dir=benchmark_spec.CND_DIR),
      'curl -O https://zenodo.org/record/2535873/files/resnet50_v1.pb ',
      'sed -i \"s/pycocotools/pycocotools==2.0.0/\" setup.py ',
      'sudo python3 setup.py develop'
  ]
  vm.RemoteCommand(" && ".join(commands))


def _CopyLocalDataset(benchmark_spec):
  logging.info("Flag mlperf_use_local_data is set, hence "
               "copying imagenet dataset from local folder to VM")
  vm = benchmark_spec.vms[0]
  destination = posixpath.join(INSTALL_DIR, "MLPERF_DIR")
  local_path = benchmark_spec.imagenetdata_tensorflow_localpath
  imagenet_filename = os.path.basename(local_path)
  remote_path = posixpath.join(INSTALL_DIR, imagenet_filename)
  vm.RemoteCopy(local_path, remote_path)
  vm.RemoteCommand("mkdir -p {dest} && chmod 775 {dest} && "
                   "tar -xf {img_net_tgz} --strip-components=1 -C {dest}"
                   .format(dest=destination, img_net_tgz=remote_path))


def _DownloadDataset(vm):
  logging.info("Downloading imagenet tensorflow dataset")
  imagenet_tar_name = ('imagenet_data_tensorflow.tar.gz')
  imagenet_path = posixpath.join(INSTALL_DIR, imagenet_tar_name)
  destination = posixpath.join(INSTALL_DIR, "MLPERF_DIR")
  config_Data = _ReadConfig()
  retcode = 1
  try:
    vm.Install('aws_credentials')
    if vm.OS_TYPE == 'ubuntu2004':
      logging.info("Ubuntu 2004 detected, installing awscli apt packages")
      vm.InstallPackages('awscli')
    else:
      logging.info("Installing awscli with pip")
      vm.Install('awscli')
    _, _, retcode = vm.RemoteCommandWithReturnCode(
        "aws s3 cp {0} {1}".format(config_Data["imagenet_dataset_tensorflow_s3uri"],
                                   imagenet_path), ignore_failure=True)
  except:
    if retcode != 0:
      vm.RemoteCommand("curl -o {0} {1}".format(
          imagenet_path, config_Data["imagenet_dataset_tensorflow_link"]))
  finally:
    vm.Uninstall('aws_credentials')
    if vm.OS_TYPE == 'ubuntu2004':
      logging.info("Ubuntu 2004 detected, uninstalling awscli with pip3")
      vm.RemoteHostCommand('pip3 uninstall -y awscli')
    else:
      logging.info("Uninstalling awscli with pip")
      vm.Uninstall('awscli')
  vm.RemoteCommand("mkdir -p {dest} && chmod 775 {dest} && "
                   "tar -xf {img_net_tgz} --strip-components=1 -C {dest}"
                   .format(dest=destination, img_net_tgz=imagenet_path))


def _DownloadMLPerfOVRepo(benchmark_spec):
  vm = benchmark_spec.vms[0]
  openvino_tar = "mlperf_ext_ov_cpp-master.tar.gz"
  url = benchmark_spec.mlperfov_repo_url
  repo_dir = posixpath.join('$HOME')
  if benchmark_spec.mlperf_use_local_data:
    logging.info("Copying MLPerf Openvino repo from local folder to SUT")
    local_path = benchmark_spec.mlperfov_repo_localpath
    vm.RemoteCopy(local_path, repo_dir)
  else:
    logging.info("Downloading MLPerf-Openvino repo locally to PKB host, before copying to SUT")
    openvino_path = vm_util.PrependTempDir(openvino_tar)
    cmd_download = ['curl', '-SL', url, '-o', openvino_path]
    vm_util.IssueCommand(cmd_download)
    logging.info("copying openvino tarball to VM")
    vm.RemoteCopy(openvino_path, repo_dir)
    vm_util.IssueCommand(['rm', openvino_path])
  vm.RemoteHostCommand('cd {dir} && tar -xvzf {ov}'.format(dir=repo_dir, ov=openvino_tar))
  vm.RemoteHostCommand(
      'cd {0} && mv -f mlperf_ext_ov_cpp-master mlperf_ext_ov_cpp'.format(repo_dir))
  ov_dir = posixpath.join(repo_dir, 'mlperf_ext_ov_cpp')
  sh_cmd = "-exec chmod +x {} \;"
  vm.RemoteHostCommand('find {dir} -type f -iname "*.sh" {cmd}'
                       .format(dir=ov_dir, cmd=sh_cmd))


def _DownloadDatasetOpenvino(benchmark_spec, config_data):
  logging.info("Downloading dataset ")
  vm = benchmark_spec.vms[0]
  model = (benchmark_spec.mlperf_model).lower()
  if model == "ssd-mobilenet-v1" or model == "ssd-mobilenet":
    dataset_tar_name = 'coco_dataset.tar.gz'
    dataset_s3 = config_data["coco_dataset_s3uri"]
    dataset_link = config_data["coco_dataset_link"]
    dataset_local = benchmark_spec.coco_dataset_localpath
  elif model == "resnet50":
    dataset_tar_name = 'imagenet_data.tar.gz'
    dataset_s3 = config_data["imagenet_dataset_s3uri"]
    dataset_link = config_data["imagenet_dataset_link"]
    dataset_local = benchmark_spec.imagenetdata_openvino_localpath
  elif model == "bert":
    dataset_tar_name = 'dataset-SQUAD.tar.gz'
    dataset_s3 = config_data["squad_dataset_s3uri"]
    dataset_link = config_data["squad_dataset_link"]
    dataset_local = benchmark_spec.squad_dataset_localpath

  dataset_path = posixpath.join(INSTALL_DIR, dataset_tar_name)
  destination = posixpath.join(INSTALL_DIR, "MLPERF_DIR")

  if benchmark_spec.mlperf_use_local_data:
    logging.info("Flag mlperf_use_local_data is set, "
                 "hence copying dataset from local folder to VM")
    vm.RemoteCopy(dataset_local, dataset_path)
  else:
    retcode = 1
    try:
      vm.Install('aws_credentials')
      if vm.OS_TYPE == 'ubuntu2004':
        logging.info("Ubuntu 2004 detected, installing awscli apt packages")
        vm.InstallPackages('awscli')
      else:
        logging.info("Installing awscli with pip")
        vm.Install('awscli')
      _, _, retcode = vm.RemoteCommandWithReturnCode(
          "aws s3 cp {0} {1}".format(dataset_s3, dataset_path), ignore_failure=True)
    except:
      if retcode != 0:
        vm.RemoteCommand("curl -o {0} {1}".format(dataset_path, dataset_link))
    finally:
      vm.Uninstall('aws_credentials')
      if vm.OS_TYPE == 'ubuntu2004':
        logging.info("Ubuntu 2004 detected, uninstalling awscli with pip3")
        vm.RemoteHostCommand('pip3 uninstall -y awscli')
      else:
        logging.info("Uninstalling awscli with pip")
        vm.Uninstall('awscli')
  vm.RemoteCommand("mkdir -p {dest} && chmod 775 {dest} && "
                   "tar -xf {datset_tgz} -C {dest}"
                   .format(dest=destination, datset_tgz=dataset_path))


def _PrepareMLPerfOpenvino_v5(benchmark_spec):
  """Prepare VM for MLPerf-Openvino runs"""
  vm = benchmark_spec.vms[0]
  logging.info("Preparing MLPerf Openvino")
  vm.Install('numactl')
  config_data = _ReadConfig()
  _DownloadMLPerfOVRepo(benchmark_spec)
  _DownloadDatasetOpenvino(benchmark_spec, config_data)


def _DownloadMLPerfv7OVRepo(benchmark_spec):
  vm = benchmark_spec.vms[0]
  openvino_tar = "mlperf-inference-v0.7-intel-submission-master.tar.gz"
  url = benchmark_spec.mlperf_v7_ov_repo_url
  repo_dir = posixpath.join('$HOME')
  logging.info("Downloading MLPerf-v7-Openvino repo locally to PKB host, before copying to SUT")
  openvino_path = vm_util.PrependTempDir(openvino_tar)
  cmd_download = ['curl', '-SL', url, '-o', openvino_path]
  vm_util.IssueCommand(cmd_download)
  logging.info("copying openvino tarball to VM")
  vm.RemoteCopy(openvino_path, repo_dir)
  vm_util.IssueCommand(['rm', openvino_path])
  vm.RemoteHostCommand('cd {dir} && tar -xvzf {ov}'.format(dir=repo_dir, ov=openvino_tar))
  vm.RemoteHostCommand(
      'cd {0} && mv -f mlperf-inference-v0.7-intel-submission-master mlperf_v7_ov_cpp'.format(repo_dir))
  ov_dir = posixpath.join(repo_dir, 'mlperf_v7_ov_cpp')
  sh_cmd = "-exec chmod +x {} \;"
  vm.RemoteHostCommand('find {dir} -type f -iname "*.sh" {cmd}'
                       .format(dir=ov_dir, cmd=sh_cmd))


def _DownloadConfigsModels(benchmark_spec):
  vm = benchmark_spec.vms[0]
  logging.info("Downloading configs and models for MLPerf v7 Openvino runs")
  models_tar_name = ('configs_models.tar.gz')
  cfg_models_path = posixpath.join('$HOME', models_tar_name)
  cfg_modles_local = benchmark_spec.mlperf_v7_ov_cfg_models
  config_Data = _ReadConfig()
  if benchmark_spec.mlperf_use_local_data:
    logging.info("Flag mlperf_use_local_data is set, "
                 "hence copying dataset from local folder to VM")
    vm.RemoteCopy(cfg_modles_local, cfg_models_path)
  else:
    retcode = 1
    try:
      vm.Install('aws_credentials')
      if vm.OS_TYPE == 'ubuntu2004':
        logging.info("Ubuntu 2004 detected, installing awscli with apt")
        vm.InstallPackages('awscli')
      else:
        logging.info("Installing awscli with pip")
        vm.Install('awscli')
      _, _, retcode = vm.RemoteCommandWithReturnCode(
          "aws s3 cp {0} {1}".format(config_Data["configs_models_s3uri"],
                                     cfg_models_path), ignore_failure=True)
    except:
      if retcode != 0:
        vm.RemoteCommand("curl -o {0} {1}".format(cfg_models_path,
                                                  config_Data["configs_models_link"]))
    finally:
      vm.Uninstall('aws_credentials')
      if vm.OS_TYPE == 'ubuntu2004':
        logging.info("Ubuntu 2004 detected, uninstalling awscli with pip3")
        vm.RemoteHostCommand('pip3 uninstall -y awscli')
      else:
        logging.info("Uninstalling awscli with pip")
        vm.Uninstall('awscli')
  vm.RemoteCommand("cd {dest} && tar -xf {cfg_models_tgz} --strip-components=1 -C {dest} && "
                   "rm -rf {cfg_models_tgz}".format(dest='$HOME', cfg_models_tgz=cfg_models_path))


def _RunMLPerfv7OpenvinoPrepareScript(vm):
  """Runs the intel_mlperf prepare script on the vm"""
  logging.info("Running MLPerf_v7_Openvino e2e prepare script")
  ov_script = 'intel_mlperf_openvino_v0.7.sh'
  mlperf_prepare_script = 'intel_mlperf/{0}'.format(ov_script)
  script_path = data.ResourcePath(mlperf_prepare_script)
  dest_path = "$HOME/{0}".format(ov_script)
  vm.PushFile(script_path, dest_path)
  cpuinfo = _GetVmCpuinfo(vm)
  ncores = cpuinfo.num_cores
  vm.RemoteCommand("chmod u+x $HOME/{scr} && $HOME/{scr} {cores}".
                   format(scr=ov_script, cores=ncores))


def _PrepareMLPerfOpenvino_v7(benchmark_spec):
  """Prepare VM for MLPerf-Openvino-v0.7 runs"""
  vm = benchmark_spec.vms[0]
  logging.info("Preparing MLPerf_v0.7 Openvino")
  vm.RemoteCommand("sudo apt update && sudo apt install -y cmake gcc g++ make wget unzip")
  vm.InstallPackages('numactl')
  _DownloadMLPerfv7OVRepo(benchmark_spec)
  _RunMLPerfv7OpenvinoPrepareScript(vm)
  config_data = _ReadConfig()
  _DownloadDatasetOpenvino(benchmark_spec, config_data)
  _DownloadConfigsModels(benchmark_spec)


def Prepare(benchmark_spec):
  """Prepare VM for MLPerf runs """
  vm = benchmark_spec.vms[0]
  benchmark_spec.always_call_cleanup = True
  if benchmark_spec.mlperf_version == "v0.7":
    logging.info("Preparing VM for MLPerf-Inference v0.7 run")
    if benchmark_spec.mlperf_framework == "tensorflow":
      _PrepareMLPerfTensorflow(benchmark_spec)
    elif benchmark_spec.mlperf_framework == "openvino":
      _PrepareMLPerfOpenvino_v7(benchmark_spec)
  else:
    logging.info("Preparing VM for MLPerf-Inference v0.5 run")
    if benchmark_spec.mlperf_framework == "pytorch":
      vm.Install('intel_mlperf_pytorch')
    elif benchmark_spec.mlperf_framework == "tensorflow":
      _PrepareMLPerfTensorflow(benchmark_spec)
    elif benchmark_spec.mlperf_framework == "openvino":
      _PrepareMLPerfOpenvino_v5(benchmark_spec)


def _RunMLPerfLoadgenTest(benchmark_spec):
  """Run Loadgen Test for MLPerf-Pytorch benchmark"""
  vm = benchmark_spec.vms[0]
  logging.info("Run MLPerf Loadgen Test")
  batch_size = benchmark_spec.mlperf_batch_size
  loadgen_scenario = (benchmark_spec.mlperf_loadgen_scenario).lower()
  model_to_test = benchmark_spec.mlperf_model
  loadgen_mode = benchmark_spec.mlperf_loadgen_mode
  cpuinfo = _GetVmCpuinfo(vm)
  num_cores = cpuinfo.num_cores
  num_instances = num_cores // 4
  LOADRUN = posixpath.join('$HOME', 'mlperf_submit', 'pytorch',
                           'mlperf-inference-loadgen-app-cpp', 'loadrun')
  out, _ = vm.RemoteCommand(
      "source /opt/intel/compilers_and_libraries/linux/bin/compilervars.sh "
      "intel64 && cd {loadrun_dir} && ./run_loadrun.sh {batch_sz} {scenario} "
      "{num_inst} {model} {cores} {mode}".
      format(loadrun_dir=LOADRUN, batch_sz=batch_size,
             scenario=loadgen_scenario, num_inst=num_instances,
             model=model_to_test, cores=num_cores, mode=loadgen_mode))
  return out


def _GetMLperfResults(benchmark_spec):
  """Returns MLPerf results dictionary"""
  logging.info("Copying MLPerf workload output to local run output dir")
  vm = benchmark_spec.vms[0]
  results_file = "mlperf_log_summary.txt"
  model = "resnet"
  scenario = "Offline"
  if benchmark_spec.mlperf_model == "resnet50":
    model = "resnet"
  if benchmark_spec.mlperf_loadgen_scenario == "offline":
    scenario = "Offline"
  if benchmark_spec.mlperf_framework == "pytorch":
    mlperf_logs_dir = "$HOME/mlperf_submit/pytorch/" \
                      "mlperf-inference-loadgen-app-cpp/loadrun/results/{mod}/" \
                      "{scen}/performance/".format(mod=model, scen=scenario)
  elif benchmark_spec.mlperf_framework == "tensorflow":
    mlperf_logs_dir = posixpath.join(benchmark_spec.CND_DIR, 'output', 'tf-cpu', 'resnet50')
  elif benchmark_spec.mlperf_framework == "openvino":
    if benchmark_spec.mlperf_version == "v0.7":
      mlperf_logs_dir = posixpath.join('$HOME', 'mlperf_v7_ov_cpp', 'closed',
                                       'Intel', 'code', 'resnet', 'resnet-ov')
    else:
      mlperf_logs_dir = posixpath.join('$HOME', 'mlperf_ext_ov_cpp', 'build_files')

  mlperf_results_file = posixpath.join(mlperf_logs_dir, results_file)
  vm.PullFile(vm_util.GetTempDir(), mlperf_results_file)
  mlperf_results_summary = {}
  with open(vm_util.PrependTempDir(results_file), 'r') as results_file:
    read = True
    while read:
      line = results_file.readline()
      if not line:
        read = False
        break
      if not line.startswith("=="):
        if line.startswith(("MLPerf Results Summary", "Additional Stats",
                            "Test Parameters")) or ":" not in line:
          continue
        key = line.split(":")[0].strip()
        value = line.split(":")[1].strip()
        mlperf_results_summary[key] = value
  return mlperf_results_summary


def _UpdateMetadata(benchmark_spec):
  data = {}
  data["Framework is"] = benchmark_spec.mlperf_framework.upper()
  data["Model is"] = benchmark_spec.mlperf_model.upper()
  return data


def _RunMLPerfPytorch(benchmark_spec, samples):
  """Runs MLPerf-Resnet50 for Pytorch framework"""
  logging.info("Running MLPerf Pytorch benchmark")
  _RunMLPerfLoadgenTest(benchmark_spec)
  sps = 0
  metadata = {}
  mlperf_results_summary = _GetMLperfResults(benchmark_spec)
  sps = mlperf_results_summary.get("Samples per second")
  metadata = mlperf_results_summary
  metadata.update(_UpdateMetadata(benchmark_spec))
  samples.append(sample.Sample("Samples per second", sps, "samples/sec", metadata))
  vm = benchmark_spec.vms[0]
  results_dir = posixpath.join('$HOME', 'mlperf_submit', 'pytorch',
                               'mlperf-inference-loadgen-app-cpp', 'loadrun',
                               'results', 'resnet', 'Offline')
  vm.RemoteCommand('cd {dir} && tar cvfz resnet50.tar.gz performance/'.
                   format(dir=results_dir))
  vm_result_dir = posixpath.join(results_dir, 'resnet50.tar.gz')
  host_log_dir = temp_dir.GetRunDirPath()
  _DownloadResultsToPkbHost(vm, host_log_dir, vm_result_dir)
  return samples


def _GetTensorFlowRunParameters(benchmark_spec):
  """Gets all the run parameters for TensorFlow"""
  count_to_test = benchmark_spec.mlperf_count
  time_to_test = benchmark_spec.mlperf_time
  qps_to_test = benchmark_spec.mlperf_qps
  latency_to_test = benchmark_spec.mlperf_max_latency
  count = ('--count ' + str(count_to_test) + ' ') if count_to_test != -1 else ''
  time = ('--time ' + str(time_to_test) + ' ') if time_to_test != -1 else ''
  qps = ('--qps ' + str(qps_to_test) + ' ') if qps_to_test != -1 else ''
  latency = ('--max-latency ' + str(latency_to_test) + ' ') if latency_to_test > -1.0 else ''
  pass_accuracy = ('--accuracy ') if benchmark_spec.mlperf_accuracy else ''
  return count + time + qps + latency + pass_accuracy


def _printAccuracyResults(benchmark_spec):
  vm = benchmark_spec.vms[0]
  logging.info("Printing accuracy results")
  log_accuracy = posixpath.join(benchmark_spec.CND_DIR, 'output', 'tf-cpu', 'resnet50', 'mlperf_log_accuracy.json')
  dataset_dir = posixpath.join('$HOME', INSTALL_DIR, 'MLPERF_DIR',
                               'dataset-imagenet-ilsvrc2012-val')
  out, _ = vm.RemoteCommand('cd {cnd_dir} && '
                            'python3 tools/accuracy-imagenet.py --mlperf-accuracy-file '
                            '{mlperf_log_accuracy} '
                            '--imagenet-val-file {dataset}'
                            '/val_map.txt'.format(mlperf_log_accuracy=log_accuracy,
                                                  cnd_dir=benchmark_spec.CND_DIR,
                                                  dataset=dataset_dir))
  logging.info(out)
  accuracy = 0.0
  for str in out.split(","):
    if (str.strip()).startswith("accuracy="):
      start = str.find("=")
      end = str.find("%")
      accuracy = float(str[start + 1:end])
  return accuracy


def _RunMLPerfTensorFlow(benchmark_spec, samples):
  logging.info("Running MLPerf TensorFlow benchmark")
  vm = benchmark_spec.vms[0]
  model_to_test = benchmark_spec.mlperf_model
  device_to_test = benchmark_spec.mlperf_device
  scenario_to_test = benchmark_spec.mlperf_loadgen_scenario
  param_to_test = _GetTensorFlowRunParameters(benchmark_spec)
  batchsize = benchmark_spec.mlperf_batch_size

  DATA_DIR = posixpath.join('$HOME', INSTALL_DIR, 'MLPERF_DIR', 'dataset-imagenet-ilsvrc2012-val')
  out, _ = vm.RemoteCommand(
      'export DATA_DIR={data_dir} &&'
      'export MODEL_DIR={cnd_dir} && '
      'cd {cnd_dir} && '
      'sed -i "s/python python/python3 python/g" run_local.sh && '
      './run_local.sh tf {model} {device} {param} --scenario {scenario} '
      '--max-batchsize {batch}'.format(data_dir=DATA_DIR,
                                       cnd_dir=benchmark_spec.CND_DIR,
                                       model=model_to_test,
                                       device=device_to_test,
                                       param=param_to_test,
                                       batch=batchsize,
                                       scenario=scenario_to_test))

  if not benchmark_spec.mlperf_accuracy:
    metadata = {}
    latency = 0
    line = (out.splitlines()[-1]).strip()
    if "TestScenario" in line:
      mlperf_results_summary = _GetMLperfResults(benchmark_spec)
      metadata = mlperf_results_summary
      metadata.update(_UpdateMetadata(benchmark_spec))
      if scenario_to_test == 'SingleStream':
        latency = mlperf_results_summary.get("90.00 percentile latency (ns)")
        samples.append(sample.Sample("90.00 percentile latency (ns)",
                                     latency, "nanosecond", metadata))
      elif scenario_to_test == 'MultiStream':
        spq = mlperf_results_summary.get("Samples per query")
        samples.append(sample.Sample("Samples per query",
                                     spq, "spq", metadata))
      elif scenario_to_test == 'Server':
        ssps = mlperf_results_summary.get("Scheduled samples per second")
        samples.append(sample.Sample("Scheduled samples per second",
                                     ssps, "second", metadata))
      elif scenario_to_test == 'Offline':
        sps = mlperf_results_summary.get("Samples per second")
        samples.append(sample.Sample("Samples per second",
                                     sps, "Second", metadata))
  elif benchmark_spec.mlperf_accuracy:
    accuracy = _printAccuracyResults(benchmark_spec)
    samples.append(sample.Sample("Accuracy", accuracy, "%", None))
  tf_cpu_dir = posixpath.join(benchmark_spec.CND_DIR, 'output', 'tf-cpu')
  vm.RemoteCommand('cd {cd_tf_cpu_dir} && '
                   'tar cvfz resnet50.tar.gz resnet50/'.format(cd_tf_cpu_dir=tf_cpu_dir))
  vm_result_dir = posixpath.join(tf_cpu_dir, 'resnet50.tar.gz')
  host_log_dir = temp_dir.GetRunDirPath()

  _DownloadResultsToPkbHost(vm, host_log_dir, vm_result_dir)

  return samples


def _DownloadResultsToPkbHost(vm, host_log_dir, vm_result_dir):
  """Download MLPerf benchmark results to the PKB host"""

  try:
    vm.PullFile(host_log_dir, vm_result_dir)
  except:
    logging.info('Unable to download results from {vm}'.format(vm=vm.ip_address))


def _GetOpenvinoCommandToRun(vm, model, scenario, batch_sz):
  """Returns command for MLPerf-v5 Openvino runs"""
  cpuinfo = _GetVmCpuinfo(vm)
  config = "mlperf.conf"
  if model == "resnet50":
    dataset = "imagenet"
    model_name = "resnet50"
    user_conf = "resnet50_user.conf"
    model_path = posixpath.join('models', 'resnet50', 'resnet50_int8.xml')
    extra_params = " --batch_size {0} --device cpu".format(batch_sz)
    dataset_path = posixpath.join(INSTALL_DIR, 'MLPERF_DIR', 'imagenet_data',
                                  'dataset-imagenet-ilsvrc2012-val/')
  elif model == "ssd-mobilenet-v1":
    dataset = "coco"
    model_name = "ssd-mobilenet"
    user_conf = "ssdmobilenet_user.conf"
    model_path = posixpath.join('models', 'ssd-mobilenet', 'ssd-mobilenet_int8.xml')
    extra_params = ""
    dataset_path = posixpath.join(INSTALL_DIR, 'MLPERF_DIR',
                                  'dataset-coco-2017-val/')

  if scenario == "singlestream":
    scen = "SingleStream"
    num_threads = cpuinfo.cores_per_socket
    cores = cpuinfo.cores_per_socket - 1
    cmd = "numactl --physcpubind=0-{core} --membind=0 Release_OMP/ov_mlperf " \
          "--scenario {s} --mode Performance --mlperf_conf_filename \"{conf}\" " \
          "--user_conf_filename \"{u_conf}\" --data_path \"{d_path}\" " \
          "--dataset {dt} --model_path \"{model}\" " \
          "--model_name {md_name} --nthreads {nt} --nwarmup_iters 100 ".\
          format(core=cores, s=scen, conf=config, dt=dataset, u_conf=user_conf,
                 d_path=dataset_path, model=model_path, md_name=model_name,
                 nt=num_threads)
    cmd = cmd + extra_params
  else:
    scen = "Offline"
    total_cores = cpuinfo.num_cores * cpuinfo.threads_per_core
    n_streams = cpuinfo.cores_per_socket * cpuinfo.threads_per_core
    cmd = "Release_OMP/ov_mlperf --scenario {s} --mode Performance " \
          "--mlperf_conf_filename \"{conf}\" " \
          "--user_conf_filename \"{u_conf}\" --data_path \"{d_path}\" " \
          "--dataset {dt} --model_path \"{model}\" " \
          "--model_name {md_name} --nstreams {ns} --batch_size {sz} " \
          "--nireq {tc} --nthreads {tc} --nwarmup_iters 1000 ".\
          format(s=scen, conf=config, dt=dataset, u_conf=user_conf,
                 d_path=dataset_path, model=model_path, md_name=model_name,
                 sz=batch_sz, ns=n_streams, tc=total_cores)
  return cmd


def _RunMLPerfOpenvinoScenario(vm, model, scenario, batch_sz):
  logging.info("running MLPerf Openvino for scenario={sc}, on model={m}"
               .format(sc=scenario, m=model))
  mlperf_path = posixpath.join('$HOME', 'mlperf_ext_ov_cpp', 'ov-custom-omp')
  build_files = posixpath.join('$HOME', 'mlperf_ext_ov_cpp', 'build_files')
  ld_path = posixpath.join('$HOME', 'mlperf_ext_ov_cpp', 'build_files',
                           'build', 'ie_cpu_extension')
  lib_path = posixpath.join('$HOME', 'mlperf_ext_ov_cpp', 'build_files',
                            'build')
  cmd_to_run = _GetOpenvinoCommandToRun(vm, model.lower(), scenario, batch_sz)
  commands = [
      'cd {mlperf} && source bin/setupvars.sh && cd {bd_files}'
      .format(mlperf=mlperf_path, bd_files=build_files),
      'export LD_LIBRARY_PATH={lib}/:$LD_LIBRARY_PATH'.format(lib=ld_path),
      'export LD_LIBRARY_PATH={ld}/:$LD_LIBRARY_PATH'.format(ld=lib_path),
      '{cmd}'.format(cmd=cmd_to_run)
  ]
  vm.RemoteCommand(" && ".join(commands))
  return cmd_to_run


def _GetMLPerfv7OpenvinoCommandToRun(vm, model, scenario, batch_sz):
  """Returns command for MLPerf-v7 Openvino runs"""
  cpuinfo = _GetVmCpuinfo(vm)
  configs_path = posixpath.join('$HOME', 'Configs')
  models_path = posixpath.join('$HOME', 'models')
  config = posixpath.join(configs_path, 'mlperf.conf')
  if model == "resnet50":
    dataset = "imagenet"
    model_name = "resnet50"
    user_conf = posixpath.join(configs_path, model_name, 'user.conf')
    model_path = posixpath.join(models_path, model_name, 'resnet50_int8.xml')
    dataset_path = posixpath.join(INSTALL_DIR, 'MLPERF_DIR', 'imagenet_data',
                                  'dataset-imagenet-ilsvrc2012-val/')
    extra_params = ""
  elif model == "ssd-mobilenet":
    dataset = "coco"
    model_name = "ssd-resnet34"
    user_conf = posixpath.join(configs_path, model_name, 'user.conf')
    model_path = posixpath.join(models_path, model_name, 'ssd-resnet34_int8.xml')
    dataset_path = posixpath.join(INSTALL_DIR, 'MLPERF_DIR', 'dataset-coco-2017-val/')
    extra_params = ""
  elif model == "bert":
    dataset = "squad"
    model_name = "bert"
    user_conf = posixpath.join(configs_path, model_name, 'user.conf')
    model_path = posixpath.join(models_path, model_name, 'bert_int8.xml')
    dataset_path = posixpath.join(INSTALL_DIR, 'MLPERF_DIR', 'dataset-SQUAD/')
    extra_params = " --nseq 128 --nseq_step 64"

  if scenario == "singlestream":
    scen = "SingleStream"
    num_threads = cpuinfo.cores_per_socket
    cores = cpuinfo.cores_per_socket - 1
    cmd = "numactl --cpunodebind=0 --membind=0 ./Release/ov_mlperf " \
          "--scenario {s} --mlperf_conf \"{conf}\" " \
          "--user_conf \"{u_conf}\" --model_name {md_name}  " \
          "--data_path \"{d_path}\" --model_path \"{model}\"  " \
          "--nthreads {nt} --nireq 1 --nstreams 1 " \
          "--total_sample_count 5000 --warmup_iters 500".\
          format(core=cores, s=scen, conf=config, dt=dataset, u_conf=user_conf,
                 d_path=dataset_path, model=model_path, md_name=model_name,
                 nt=num_threads)
  elif scenario == "offline":
    scen = "Offline"
    total_cores = cpuinfo.num_cores * cpuinfo.threads_per_core
    n_threads = cpuinfo.cores_per_socket * cpuinfo.threads_per_core
    cmd = "./Release/ov_mlperf --scenario {s} " \
          "--mlperf_conf \"{conf}\" --user_conf \"{u_conf}\" " \
          "--model_name {md_name} --data_path \"{d_path}\" " \
          "--model_path \"{model}\"  --nstreams {tc}  --nireq {tc} " \
          "--nthreads {nt} --batch_size {sz} --total_sample_count 5000 " \
          "--warmup_iters 1000 ".format(s=scen, conf=config, dt=dataset,
                                        u_conf=user_conf, d_path=dataset_path,
                                        model=model_path, md_name=model_name,
                                        sz=batch_sz, nt=n_threads, tc=total_cores)
    cmd = cmd + extra_params
  else:
    scen = "Server"
    total_cores = cpuinfo.num_cores * cpuinfo.threads_per_core
    n_threads = cpuinfo.cores_per_socket * cpuinfo.threads_per_core
    cmd = "./Release/ov_mlperf --scenario {s} " \
          "--mlperf_conf \"{conf}\" --user_conf \"{u_conf}\" " \
          "--model_name {md_name} --data_path \"{d_path}\" " \
          "--model_path \"{model}\" --nireq {tc} --nthreads {nt} " \
          "--nstreams {ns} --total_sample_count 5000 " \
          "--warmup_iters 1000 ".format(s=scen, conf=config, dt=dataset,
                                        u_conf=user_conf, d_path=dataset_path,
                                        model=model_path, md_name=model_name,
                                        sz=batch_sz, nt=n_threads,
                                        ns=cpuinfo.num_cores, tc=total_cores)
    cmd = cmd + extra_params

  return cmd


def _RunMLPerfv7OpenvinoScenario(vm, model, scenario, batch_sz):
  logging.info("running MLPerf-v7 Openvino for scenario={sc}, on model={m}"
               .format(sc=scenario, m=model))
  mlperf_v7_ov_path = posixpath.join('$HOME', 'mlperf_v7_ov_cpp', 'closed',
                                     'Intel', 'code', 'resnet', 'resnet-ov')
  cmd_to_run = _GetMLPerfv7OpenvinoCommandToRun(vm, model.lower(), scenario, batch_sz)
  commands = [
      'cd {mlperf} && {cmd}'.format(mlperf=mlperf_v7_ov_path, cmd=cmd_to_run)
  ]
  vm.RemoteCommand(" && ".join(commands))
  return cmd_to_run


def _RunMLPerfOpenvino(benchmark_spec, samples):
  """Runs MLPerf-Resnet50 for Openvino framework"""
  logging.info("Running MLPerf Openvino")
  vm = benchmark_spec.vms[0]
  model = benchmark_spec.mlperf_model
  scenario = benchmark_spec.mlperf_loadgen_scenario.lower()
  batch_sz = benchmark_spec.mlperf_batch_size
  if benchmark_spec.mlperf_version == "v0.7":
    cmd_to_run = _RunMLPerfv7OpenvinoScenario(vm, model, scenario, batch_sz)
  else:
    cmd_to_run = _RunMLPerfOpenvinoScenario(vm, model, scenario, batch_sz)
  metadata = {}
  mlperf_results_summary = _GetMLperfResults(benchmark_spec)
  metadata = mlperf_results_summary
  metadata.update(_UpdateMetadata(benchmark_spec))
  metadata["ov_command"] = cmd_to_run
  metadata["batch_size"] = batch_sz
  if scenario == 'singlestream':
    latency = mlperf_results_summary.get("90.00 percentile latency (ns)")
    samples.append(sample.Sample("90.00 percentile latency (ns)",
                                 latency, "nanosecond", metadata))
  elif scenario == 'offline':
    sps = mlperf_results_summary.get("Samples per second")
    samples.append(sample.Sample("Samples per second",
                                 sps, "Second", metadata))
  if benchmark_spec.mlperf_version == "v0.7":
    results_dir = posixpath.join('$HOME', 'mlperf_v7_ov_cpp', 'closed',
                                 'Intel', 'code', 'resnet', 'resnet-ov')
  else:
    results_dir = posixpath.join('$HOME', 'mlperf_ext_ov_cpp', 'build_files')
  vm.RemoteCommand('cd {dir} && tar cvfz results.tar.gz *.txt *.json'.
                   format(dir=results_dir))
  vm_result_dir = posixpath.join(results_dir, 'results.tar.gz')
  host_log_dir = temp_dir.GetRunDirPath()
  _DownloadResultsToPkbHost(vm, host_log_dir, vm_result_dir)
  return samples


def Run(benchmark_spec, workload_name):
  """MLPerf workload run on VM"""
  logging.info("run mlperf benchmark for CPU")
  samples = []
  if benchmark_spec.mlperf_version == "v0.7":
    logging.info("MLPerf-Inference v0.7 run")
    if benchmark_spec.mlperf_framework == "tensorflow":
      samples = _RunMLPerfTensorFlow(benchmark_spec, samples)
    elif benchmark_spec.mlperf_framework == "openvino":
      samples = _RunMLPerfOpenvino(benchmark_spec, samples)
  else:
    logging.info("MLPerf-Inference v0.5 run")
    if benchmark_spec.mlperf_framework == "pytorch":
      samples = _RunMLPerfPytorch(benchmark_spec, samples)
    elif benchmark_spec.mlperf_framework == "tensorflow":
      samples = _RunMLPerfTensorFlow(benchmark_spec, samples)
    elif benchmark_spec.mlperf_framework == "openvino":
      samples = _RunMLPerfOpenvino(benchmark_spec, samples)
  return samples


def Cleanup(benchmark_spec):
  """Cleanup MLPerf on the vm.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
      required to run the benchmark.
  """
  logging.info("Cleanup VM after MLPerf run")
  vm = benchmark_spec.vms[0]
  boost_ver_num = "1_72_0"
  cmake_ver_num = "3.16.0-Linux-x86_64"
  if benchmark_spec.mlperf_framework == "pytorch":
    mlperf_dir = "$HOME/mlperf_submit"
    optimized_models = "$HOME/optimized_models"
    commands = [
        "rm -rf {0} {1}".format(mlperf_dir, optimized_models),
        "rm -rf {0} {1}".format("$HOME/boost_{0}".format(boost_ver_num),
                                "$HOME/cmake-{0}".format(cmake_ver_num))
    ]
    vm.RemoteCommand(" && ".join(commands))
  if benchmark_spec.mlperf_framework == "tensorflow":
    vm.RemoteCommand('sudo rm -rf {dir1}'.format(dir1=INFERENCE_DIR))
  if benchmark_spec.mlperf_framework.lower() == "openvino":
    mlperf_dir = posixpath.join('$HOME', 'mlperf_ext_ov_cpp')
    vm.RemoteCommand("rm -rf {0}".format(mlperf_dir))
