import collections
import posixpath
import logging
import os
import datetime
import yaml
import json
import re
from perfkitbenchmarker import errors
from perfkitbenchmarker import data
from perfkitbenchmarker import configs
from absl import flags
from perfkitbenchmarker import sample
from perfkitbenchmarker import vm_util
from perfkitbenchmarker.linux_packages import INSTALL_DIR

FLAGS = flags.FLAGS
flags.DEFINE_string('intel_stacks_precision', 'fp32',
                    'Tensorflow model precision type int8 or fp32')
flags.DEFINE_string('intel_stacks_image_to_use', 'tensorflow_mkl_image_latest',
                    'Tensorflow image to use')
flags.DEFINE_string('intel_stacks_models_to_use', 'phoronix',
                    'Phoronix test suite model')
flags.DEFINE_string('cumulus_stacks_registry_username', '',
                    'The username for the Cumulus ECR login')
flags.DEFINE_string('cumulus_stacks_registry_password', '',
                    'The password for the Cumulus ECR login')
flags.DEFINE_string('cumulus_stacks_registry_url', '',
                    'The url for the Cumulus ECR login')
GENERATED_CONFIG_FILE = "generated_config.yml"
BENCHMARK_ARGS = {"mkl": "", "mode": ""}
CONFIG_FILE = 'intel_community/intel_stacks_benchmark/config_phoronix.yml'
CONFIG_DATA = {}

BENCHMARK_NAME = "intel_stacks"
BENCHMARK_CONFIG = """
intel_stacks:
  description: Run stacks
  vm_groups:
    target:
      os_type: clear
      vm_spec:
        GCP:
          machine_type: n1-highcpu-8
          zone: us-east1-b
          image: null
          boot_disk_size: 100
          min_cpu_platform: "skylake"
        AWS:
          machine_type: c5.2xlarge
          zone: us-east-2
          image: ami-00e94a7124f1c803d
          boot_disk_size: 100
        Azure:
          machine_type: Standard_F8s_v2
          zone: eastus
          image: null
          boot_disk_size: 100
        OpenStack:
          machine_type: baremetal
          zone: nova
          image: null
"""


def _ReadConfig():
    with open(data.ResourcePath(CONFIG_FILE)) as cfg_file:
        global CONFIG_DATA
        CONFIG_DATA = yaml.load(cfg_file)
    CONFIG_DATA["image_to_use"] = FLAGS.intel_stacks_image_to_use
    CONFIG_DATA["precision"] = FLAGS.intel_stacks_precision


def _ReadGeneratedConfig(path):
    with open(path) as cfg_file:
        config_data = yaml.load(cfg_file)
    return config_data


def _WriteGeneratedConfig(path, config):
    with open(path, "w") as cfg_file:
        yaml.safe_dump(config, cfg_file, default_flow_style=False)


def _GetVmCpuinfo(vm):
    out, _ = vm.RemoteCommand("lscpu | sed -n 's/Socket(s):[ \t]*//p'")
    sockets = int(out.strip())

    out, _ = \
        vm.RemoteCommand("lscpu | sed -n 's/Core(s) per socket:[ \t]*//p'")
    cores_per_socket = int(out.strip())

    out, _ = \
        vm.RemoteCommand("lscpu | sed -n 's/Thread(s) per core:[ \t]*//p'")
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
    logs_archive_vm = posixpath.join(INSTALL_DIR, "stacks-logs.tar.gz")
    vm.RemoteCommand("tar czf {archive} -C {log_dir} ."
                     .format(archive=logs_archive_vm, log_dir=logdir))
    logs_archive = (os.path.join(vm_util.GetTempDir(),
                                 'stacks-logs-{time_stamp}.tar.gz'
                                 .format(time_stamp=timestamp)))
    vm.PullFile(logs_archive, logs_archive_vm)


def CheckPrerequisites(benchmark_config):
    """Verifies that the required configs are present.

    Raises:
    perfkitbenchmarker.errors.Config.InvalidValue: On invalid value.
    """
    if FLAGS["cumulus_stacks_registry_username"].present:
        if len(FLAGS.cumulus_stacks_registry_username.strip()) == 0:
            raise errors.Config.InvalidValue
            ("The Cumulus Docker registry username cannot be empty."
                "Please provide username")
        if FLAGS["cumulus_stacks_registry_password"].present:
            if len(FLAGS.cumulus_stacks_registry_password.strip()) == 0:
                raise errors.Config.InvalidValue(
                    "The Docker registry password cannot be empty."
                    "Please provide password")
        else:
            raise errors.Config.InvalidValue(
                "You provided a Docker registry username,"
                "but no password.Please provide password")


def GetConfig(user_config):
    config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
    return config


def Prepare(benchmark_spec):
    vm = benchmark_spec.vms[0]
    _ReadConfig()
    global BENCHMARK_ARGS
    BENCHMARK_ARGS["train"] = CONFIG_DATA["train"]
    BENCHMARK_ARGS["model"] = CONFIG_DATA["model"]
    BENCHMARK_ARGS["clean_up"] = CONFIG_DATA["clean_up"]
    BENCHMARK_ARGS["pts-bench"] = CONFIG_DATA["pts-bench"]
    BENCHMARK_ARGS["data_format"] = CONFIG_DATA["data_format"]
    logging.info("Obtaining Cpu Information")
    cpuinfo = _GetVmCpuinfo(vm)
    BENCHMARK_ARGS["total_vcpus"] = vm.NumCpusForBenchmark()
    BENCHMARK_ARGS["inter_threads"] = cpuinfo.sockets
    BENCHMARK_ARGS["intra_threads"] = cpuinfo.cores_per_socket * cpuinfo.sockets
    BENCHMARK_ARGS["precision"] = CONFIG_DATA["precision"]
    BENCHMARK_ARGS["docker_runtime"] = CONFIG_DATA["docker_runtime"]
    benchmark_spec.always_call_cleanup = True
    if not BENCHMARK_ARGS["train"]:
        BENCHMARK_ARGS["mode"] = "--forward_only=True"

    # Install packages
    logging.info("Installing packages")
    vm.Install('docker_ce')
    vm.InstallPackages('git wget')
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
    if CONFIG_DATA["model"] != "phoronix":
        vm.RemoteCommand("sudo docker pull {}".format(BENCHMARK_ARGS["image"]))


def _GetDockerRunCommand():
    if CONFIG_DATA["model"] == "phoronix":
        docker_run_cmd = "sudo docker run --privileged -id "\
            "--rm {image}".format(**BENCHMARK_ARGS)
    return docker_run_cmd


def _GetCommandToLaunchBenchmark(cmd):
    if (FLAGS.intel_stacks_models_to_use.lower() == "phoronix"):
        cmd = "phoronix-test-suite batch-benchmark {pts-bench}"\
            .format(**BENCHMARK_ARGS)
    return cmd


def _GetThroughputMetrics(out, search_string):
    # Get relevant metrics from output
    for line in reversed(out.splitlines()):
        idx = line.find(search_string)
        if idx > -1:
            value_tmp = line.split(':')[1].strip()
            value = re.sub(r'[^\d\.]', '', value_tmp).strip()
            metric = re.sub(r'[\d\.]', '', value_tmp).strip()
            break
    return value, metric


def Run(benchmark_spec):
    docker_exec_cmd = "sudo docker exec -i %s %s"
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
    if CONFIG_DATA["model"] == "phoronix":
        BENCHMARK_ARGS["image_type"] = "phoronix"
        FLAGS.intel_stacks_models_to_use = "phoronix"
        throughput_search_string = "Average"

    # Create the command to launch the benchmark
    cmd_in_container = _GetCommandToLaunchBenchmark(cmd_in_container)
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
                             '{logdir}/batch_{batch_size}_iter_{rep}.log'
                             .format(out=out, logdir=logdir,
                                     batch_size=batch, rep=i))

        # Get relevant metrics from output
        value, metric = _GetThroughputMetrics(out, throughput_search_string)
        BENCHMARK_ARGS["batch_size"] = batch
        metadata = BENCHMARK_ARGS
        results.append(sample.Sample("Result", value, metric, metadata))

    logging.info("Downloading logs")
    _GetLogs(vm, logdir)
    _WriteGeneratedConfig(os.path.join(vm_util.GetTempDir(),
                                       GENERATED_CONFIG_FILE), BENCHMARK_ARGS)
    return results


def Cleanup(benchmark_spec):
    if CONFIG_DATA["clean_up"] == "true":
        vm = benchmark_spec.vms[0]
        BENCHMARK_ARGS = _ReadGeneratedConfig(
            os.path.join(vm_util.GetTempDir(), GENERATED_CONFIG_FILE))
        cmds = [
            "sudo docker rm -f {0}".format(BENCHMARK_ARGS["container_id"]),
            "sudo docker rmi {0}".format(BENCHMARK_ARGS["image"]),
        ]
        vm.RemoteCommand(' && '.join(cmds))
