import logging
import posixpath
import re
import os
import yaml
import math

from absl import flags
from perfkitbenchmarker import data
from perfkitbenchmarker import configs
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import sample
from perfkitbenchmarker import disk
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker.linux_packages import hadoop
from perfkitbenchmarker.linux_packages import intel_hibench_spark
from perfkitbenchmarker.linux_packages import maven

FLAGS = flags.FLAGS

HIBENCH_GIT_ARCHIVE = 'https://github.com/Intel-bigdata/HiBench/archive/HiBench-7.0.tar.gz'
HIBENCH_PATH = posixpath.join(INSTALL_DIR, "HiBench")
KMEANS_CONFIG_PATH = posixpath.join(HIBENCH_PATH, "conf", "workloads", "ml")
WORKLOADS = ['kmeans', 'terasort']
FRAMEWORKS = ['spark', 'hadoop']
CONFIG_FILE = os.path.join('intel_hibench_benchmark', 'config.yml')
GENERATED_CONFIG_FILE = "generated_config.yml"
DISK_CONFIG = {}
LIMITS_CONFIG_FILE = posixpath.join('etc', 'security', 'limits.d', '99-pkb.conf')
WORKLOAD_CATEGORIES = {
    'websearch': {
        'workloads': {
            'pagerank',
            'nutchindexing'
        },
        'installed': False
    },
    'ml': {
        'workloads': {
            'lr',
            'svm',
            'bayes',
            'pca',
            'svd',
            'als',
            'lda',
            'linear',
            'kmeans',
            'rf',
            'gbt'
        },
        'installed': False
    },
    'sql': {
        'workloads': {
            'scan',
            'join',
            'aggregation'
        },
        'installed': False
    },
    'graph': {
        'workloads': {
            'nweight'
        },
        'installed': False
    },
    'micro': {
        'workloads': {
            'sort',
            'sleep',
            'dfsioe',
            'wordcount',
            'terasort'
        },
        'installed': False
    }
}
CONFIG_DATA_TEMPLATE = {
    "hibench": {
        "hibench.scale.profile": None,
        "hibench.default.map.parallelism": None,
        "hibench.default.shuffle.parallelism": None
    },
    "spark": {
        "hibench.spark.master": None,
        "hibench.yarn.executor.num": None,
        "hibench.yarn.executor.cores": None,
        "spark.executor.memory": None,
        "spark.driver.memory": None
    },
    "scratch_disks": {
        "mountpoints": None
    },
    "kmeans": {
        "kmeans_num_of_clusters": None,
        "kmeans_dimensions": None,
        "kmeans_num_of_samples": None,
        "kmeans_samples_per_inputfile": None,
        "kmeans_max_iteration": None,
        "kmeans_k": None,
        "kmeans_convergedist": None
    }
}
CONFIG_DATA = {}
# Define Flags
flags.DEFINE_string('intel_hibench_spark_version', '2.2.2', 'The version of spark')
flags.DEFINE_string('intel_hibench_scala_version', '2.11.0', 'The version of scala')
flags.DEFINE_string('intel_hibench_hadoop_version', '2.9.2', 'The version of hadoop.')
flags.DEFINE_string('intel_hibench_framework', 'spark',
                    'Available frameworks: {0}'.format(FRAMEWORKS))
flags.DEFINE_list('intel_hibench_workloads', ['kmeans'],
                  'Available workloads {0}'.format(' '.join(WORKLOADS)))
flags.DEFINE_string('intel_hibench_maven_version', '3.6.1', 'The version of maven')
flags.DEFINE_string('intel_hibench_hibench_scale_profile', None,
                    'Available values: tiny, small, large, huge, gigantic, bigdata')
flags.DEFINE_string('intel_hibench_hibench_default_map_parallelism', None,
                    'Mapper numbers in MR, default parallelism in Spark')
flags.DEFINE_string('intel_hibench_hibench_default_shuffle_parallelism', None,
                    'Reducer number in MR, shuffle partition number in Spark')
flags.DEFINE_string('intel_hibench_hibench_spark_master', None, 'Available values: spark, yarn-client')
flags.DEFINE_integer('intel_hibench_hibench_yarn_executor_num', None, 'Number executors in YARN mode')
flags.DEFINE_integer('intel_hibench_hibench_yarn_executor_cores', None, 'Number executor cores in YARN mode')
flags.DEFINE_string('intel_hibench_spark_executor_memory', None, 'Executor memory, standalone or YARN mode')
flags.DEFINE_string('intel_hibench_spark_driver_memory', None, 'Driver memory, standalone or YARN mode')
flags.DEFINE_list('intel_hibench_mountpoints', None,
                  'Not applicable for cloud. On bare metal, they need to be already mounted prior to running Hibench')
flags.DEFINE_integer('intel_hibench_kmeans_num_of_clusters', None, 'Number of clusters for HiBench Kmeans scale profile')
flags.DEFINE_integer('intel_hibench_kmeans_dimensions', None, 'Number of dimensions for HiBench Kmeans scale profile')
flags.DEFINE_integer('intel_hibench_kmeans_num_of_samples', None, 'Number of samples for HiBench Kmeans scale profile (multiplied by datanodes - 1)')
flags.DEFINE_integer('intel_hibench_kmeans_samples_per_inputfile', None, 'Number of samples per input file for HiBench Kmeans scale profile')
flags.DEFINE_integer('intel_hibench_kmeans_max_iteration', None, 'Max iteration for HiBench Kmeans scale profile')
flags.DEFINE_integer('intel_hibench_kmeans_k', None, 'K for HiBench Kmeans scale profile')
flags.DEFINE_float('intel_hibench_kmeans_convergedist', None, 'Converge distribution for HiBench Kmeans scale profile')

BENCHMARK_NAME = 'intel_hibench'
BENCHMARK_CONFIG = """
intel_hibench:
  description: Build hibench workloads
  vm_groups:
    target:
      os_type: centos7
      disk_spec: *default_disk_300gb_high_speed
      disk_count: 6
      vm_count: 5
      vm_spec: *default_high_compute
  flags:
    ssh_reuse_connections: false
"""
FILES_TO_SAVE = {
    "system_files": [
        "/etc/hosts",
    ],
    "user_files": [
    ]
}

BENCHMARK_DATA = {
    HIBENCH_GIT_ARCHIVE.split('/')[-1]:
        '89b01f3ad90b758f24afd5ea2bee997c3d700ce9244b8a2b544acc462ab0e847'
}
BENCHMARK_DATA_URL = {
    HIBENCH_GIT_ARCHIVE.split('/')[-1]: HIBENCH_GIT_ARCHIVE
}


def _IsStaticDeployment(vm):
  return vm.is_static


def _InitFlags():
  FLAGS.hadoop_version = FLAGS.intel_hibench_hadoop_version
  FLAGS.maven_version = FLAGS.intel_hibench_maven_version


def _PopulateScratchDisks(basic_conf):
  basic_conf["scratch_disks"]["mountpoints"] = []
  disk_count = DISK_CONFIG["disk_count"]
  basic_conf["scratch_disks"]["disk_size"] = DISK_CONFIG["disk_size"]
  logging.info("Adding {} disks to the mountpoint list".format(disk_count))
  if disk_count == 1:
    basic_conf["scratch_disks"]["mountpoints"].append(
        DISK_CONFIG["cloud_mountpoint"])
  else:
    for i in range(0, disk_count):
      basic_conf["scratch_disks"]["mountpoints"].append("{0}{1}".format(
          DISK_CONFIG["cloud_mountpoint"], i))


def _InstallFrameworks(master, hibench_conf):
  hadoop.DATA_FILES = [
      'hadoop/core-site.xml.j2',
      'intel_hibench_benchmark/yarn-site.xml.j2',
      'intel_hibench_benchmark/hdfs-site.xml.j2',
      'intel_hibench_benchmark/mapred-site.xml',
      'hadoop/hadoop-env.sh.j2',
      'hadoop/workers.j2'
  ]
  mountpoints = hibench_conf["scratch_disks"]["mountpoints"]
  config = {
      "dfs_namenode_name_dir": ",".join(
          [posixpath.join(mount, "hadoop_tmp", "hdfs", "namenode") for mount in mountpoints]),
      "dfs_datanode_data_dir": ",".join(
          [posixpath.join(mount, "hadoop_tmp", "hdfs", "datanode") for mount in mountpoints]),
      "yarn_nodemanager_local_dirs": ",".join(
          [posixpath.join(mount, "nmlocaldir") for mount in mountpoints]),
      "yarn_nodemanager_log_dirs": ",".join(
          [posixpath.join(mount, "userlogs") for mount in mountpoints]),
      "vm_memory_mb": int(master.total_memory_kb / 1024),
      "cloud_is_azure": FLAGS.cloud == "Azure"
  }
  _SetHadoopInHomeDir(master)
  _InstallFramework('hadoop', hadoop, master, extra_config=config)
  if FLAGS.intel_hibench_framework == "spark":
    if "yarn-client" == hibench_conf["spark"]["hibench.spark.master"]:
      deploy_mode = "yarn-client"
    else:
      deploy_mode = "standalone"
    _InstallFramework('intel_hibench_spark', intel_hibench_spark, master, deploy_mode)


def _InstallFramework(framework_name, framework_module, master, deploy_mode="", extra_config={}):
  vm_util.RunThreaded(lambda vm: vm.Install(framework_name), [master] + master.slaves)
  try:
    if not deploy_mode:
      framework_module.ConfigureAndStart(master, master.slaves, extra_config=extra_config)
    else:
      framework_module.ConfigureAndStart(master, master.slaves, deploy_mode, extra_config)
  except:
    # Raising here causes Cleanup to be be called
    raise Exception("{0} failed to install or start. Cleaning up and exiting.".format(framework_name))


def _SetHadoopInHomeDir(master):
  out, _ = master.RemoteCommand('pwd')
  hadoop_dir = posixpath.join(out.strip(), 'hadoop')
  _ChangeHadoopDirs(hadoop_dir)


def _ChangeHadoopDirs(hadoop_dir):
  hadoop.HADOOP_DIR = hadoop_dir
  hadoop.HADOOP_BIN = posixpath.join(hadoop.HADOOP_DIR, 'bin')
  hadoop.HADOOP_SBIN = posixpath.join(hadoop.HADOOP_DIR, 'sbin')
  hadoop.HADOOP_CONF_DIR = posixpath.join(hadoop.HADOOP_DIR, 'etc', 'hadoop')
  hadoop.HADOOP_PRIVATE_KEY = posixpath.join(hadoop.HADOOP_CONF_DIR, 'hadoop_keyfile')


def _InstallHibench(master):
  _InstallHibenchPrerequisites(master)
  _BuildHibench(master)


def _InstallHibenchPrerequisites(master):
  master.Install('maven')
  master.Install('python2')
  master.InstallPackages('git bc')


def _BuildHibench(master):
  workloads_to_run = FLAGS.intel_hibench_workloads
  maven_cmd = _CreateMavenBuildCmd(workloads_to_run)
  master.InstallPreprovisionedBenchmarkData(BENCHMARK_NAME, BENCHMARK_DATA,
                                            INSTALL_DIR)
  hibench_remote_path = posixpath.join(INSTALL_DIR,
                                       HIBENCH_GIT_ARCHIVE.split('/')[-1])
  cmds = [
      'test -d {0} && rm -rf {0}; mkdir {0} && tar -C {0} --strip-components=1 -xzf {1}'.format(
          HIBENCH_PATH,
          hibench_remote_path),
      'cd {0}'.format(HIBENCH_PATH),
      maven_cmd
  ]
  master.RemoteCommand(' && '.join(cmds))


def _CreateMavenBuildCmd(workloads_to_run):
  def shorten_version(ver):
    return ver[:ver.rindex('.')]

  categories_flags = ""
  for workload in workloads_to_run:
    for category, entry in WORKLOAD_CATEGORIES.items():
      if workload in entry['workloads']:
        if not entry['installed']:
          categories_flags += "-P{0} ".format(category)
          entry['installed'] = True

  return maven.GetRunCommand("-P{f}bench -Dmodules {c} -Dspark={sp_ver} -Dscala={sc_ver} clean package".format(
      f=FLAGS.intel_hibench_framework,
      c=categories_flags,
      sp_ver=shorten_version(FLAGS.intel_hibench_spark_version),
      sc_ver=shorten_version(FLAGS.intel_hibench_scala_version)))


def _GetHibenchConfiguration(master, hibench_conf):
  spark_conf = _GetSparkConfiguration(master)
  hibench_conf.update(_GetKmeansConfiguration(master))
  mountpoints = hibench_conf["scratch_disks"]["mountpoints"]
  hibench_conf_complete = dict(hibench_conf["hibench"], **hibench_conf["spark"], **hibench_conf["kmeans"])
  _ParseHibenchConfiguration(master, hibench_conf_complete)
  hibench_conf_complete["spark.local.dir"] = ",".join(
      [posixpath.join(mount, "spark_tmp") for mount in mountpoints])
  hibench_conf_complete.update(spark_conf)
  hadoop_conf = _GetHadoopConfiguration(master)
  hibench_conf_complete.update(hadoop_conf)
  if "yarn-client" == hibench_conf["spark"]["hibench.spark.master"]:
    hibench_conf_complete["hibench.spark.master"] = "yarn-client"
  hibench_conf_complete.update(hibench_conf["scratch_disks"])
  hibench_hosts = {
      "master_ip": "{0}:8020".format(master.internal_ip),
      "workers_ip":
          ",".join("{0}:50010".format(vm.internal_ip) for vm in master.slaves)
  }
  hibench_conf_complete.update(hibench_hosts)
  return hibench_conf_complete


def _ParseHibenchConfiguration(master, hibench_conf):
  vcpus = master.NumCpusForBenchmark() - 1
  num_data_nodes = len(master.slaves)
  scale_profile, vcpus, memory = _GetScaleProfile(master)
  logging.info("{} cores and {} G memory available, per data node ({}). Using {} scale profile.".format(
               vcpus,
               memory,
               num_data_nodes,
               scale_profile))
  if hibench_conf["hibench.yarn.executor.cores"] is None:
    hibench_conf["hibench.yarn.executor.cores"] = 5
  executor_cores = hibench_conf["hibench.yarn.executor.cores"]
  if hibench_conf["hibench.yarn.executor.num"] is None:
    hibench_conf["hibench.yarn.executor.num"] = int(
        math.floor((vcpus * num_data_nodes) / executor_cores))

  for param in ("hibench.default.map.parallelism", "hibench.default.shuffle.parallelism"):
    if hibench_conf[param] is None:
      hibench_conf[param] = hibench_conf["hibench.yarn.executor.num"] * executor_cores * 5

  if hibench_conf["spark.executor.memory"] is None:
    mem_per_node_gb = int(master.total_memory_kb / (1024 * 1024))
    hibench_conf["spark.executor.memory"] = "{0}g".format(
        int(math.floor(mem_per_node_gb / (float(vcpus) / executor_cores) * 0.85)))
  if hibench_conf["hibench.scale.profile"] is None:
    hibench_conf["hibench.scale.profile"] = scale_profile
  if hibench_conf["kmeans_num_of_samples"] is not None:
    hibench_conf["kmeans_num_of_samples"] = hibench_conf["kmeans_num_of_samples"] * (num_data_nodes - 1)


def _GetScaleProfile(master):
  vcpus = int(master.NumCpusForBenchmark() - 1)
  memory = int(master.total_memory_kb / 1048576)
  scale_profile = None
  supported_scale_profiles = ["small", "large", "huge", "gigantic", "bigdata"]
  profile_specs = {
      "small": {
          "min_vcpus": 1,
          "max_vcpus": 32,
          "min_memory": 1,
          "max_memory": 128
      },
      "large": {
          "min_vcpus": 32,
          "max_vcpus": 72,
          "min_memory": 1,
          "max_memory": 256
      },
      "huge": {
          "min_vcpus": 72,
          "max_vcpus": 96,
          "min_memory": 1,
          "max_memory": 192
      },
      "gigantic": {
          "min_vcpus": 72,
          "max_vcpus": 96,
          "min_memory": 192,
          "max_memory": 384
      },
      "bigdata": {
          "min_vcpus": 96,
          "max_vcpus": 512,
          "min_memory": 192,
          "max_memory": 384
      }
  }
  for profile in supported_scale_profiles:
    specs = profile_specs[profile]
    if (vcpus >= specs["min_vcpus"] and vcpus < specs["max_vcpus"]
        and memory >= specs["min_memory"] and memory < specs["max_memory"]):
      scale_profile = profile
  if scale_profile is None:
    # Machine types that exceed the bigdata specs above should probably default to bigdata
    scale_profile = "bigdata"
    logging.warn("Optimal scale profile could not be determined! Defaulting to {}.".format(scale_profile))
  return [scale_profile, vcpus, memory]


def _ReadConfig(master):
  config_data = CONFIG_DATA_TEMPLATE
  with open(data.ResourcePath(CONFIG_FILE)) as f:
    configuration_parameters = yaml.load(f, Loader=yaml.SafeLoader)
  for primary_key in config_data.keys():
    # Skip over kmeans because it's formatted differently
    if primary_key == 'kmeans':
      continue
    for secondary_key in list(config_data[primary_key]):
      flag_name = "{0}{1}".format("intel_hibench_", secondary_key.replace(".", "_"))
      if FLAGS[flag_name].present:
        logging.warn("Found {} flag. This overrides the config file.".format(flag_name))
        config_data[primary_key][secondary_key] = FLAGS[flag_name].value
      elif configuration_parameters[primary_key] is not None and secondary_key in configuration_parameters[primary_key]:
          config_data[primary_key][secondary_key] = configuration_parameters[primary_key][secondary_key]
  # If we have a kmeans section in the config
  kmeans_key, hibench_key, hibench_sp_param = ["kmeans", "hibench", "hibench.scale.profile"]
  if configuration_parameters[kmeans_key]:
    # We need the hibench_scale_profile to select the correct parameters for Kmeans
    if not config_data[hibench_key][hibench_sp_param]:
      config_data[hibench_key][hibench_sp_param] = _GetScaleProfile(master)[0]
    hibench_scale_profile = config_data[hibench_key][hibench_sp_param]
    for parameter in config_data[kmeans_key]:
        flag_name = "{0}{1}".format("intel_hibench_", parameter)
        if FLAGS[flag_name].present:
          config_data[kmeans_key][parameter] = FLAGS[flag_name].value
        else:
          config_data[kmeans_key][parameter] = configuration_parameters[kmeans_key][hibench_scale_profile][parameter]
  if "disk_count" in DISK_CONFIG:  # only happens for cloud
    _PopulateScratchDisks(config_data)
  return config_data


def _ReadGeneratedConfig(path):
  with open(path) as f:
    config_data = yaml.load(f, Loader=yaml.SafeLoader)
  return config_data


def _WriteGeneratedConfig(path, config):
  with open(path, "w") as f:
    yaml.safe_dump(config, f, default_flow_style=False)


def _GetSparkConfiguration(master):
  return {
      "hibench.spark.home": intel_hibench_spark.SPARK_PATH,
      "hibench.spark.master": "spark://{0}:7077".format(master.internal_ip),
      "spark.eventLog.dir": "hdfs://{0}:8020/usr/spark_events".format(master.internal_ip)
  }


def _GetHadoopConfiguration(master):
  return {
      "hibench.hadoop.home": hadoop.HADOOP_DIR,
      "hibench.hadoop.executable": posixpath.join(hadoop.HADOOP_BIN, "hadoop"),
      "hibench.hadoop.configure.dir": hadoop.HADOOP_CONF_DIR,
      "hibench.hdfs.master": "hdfs://{0}:8020/".format(master.internal_ip),
      "hibench.hadoop.release": "apache"
  }


def _GetKmeansConfiguration(master):
  return CONFIG_DATA["kmeans"]


def _ApplyConfig(hibench_conf, master):
  vms = [master] + master.slaves
  master.RemoteCommand("{0}/hadoop fs -mkdir -p /usr/spark_events".format(hadoop.HADOOP_BIN))
  for spark_tmp in hibench_conf["spark.local.dir"].split(","):
    vm_util.RunThreaded(
        lambda vm: vm.RemoteCommand("sudo mkdir -p {0} && sudo chmod 777 -R {0}".format(spark_tmp)),
        vms)

  # Transform variables which contain dots in order to work with jinja
  hibench_conf = {k.replace(".", "_"): v for k, v in hibench_conf.items()}

  data_files = [{"remote_path": posixpath.join(HIBENCH_PATH, "conf"),
                 "files": ["hibench.conf.j2", "spark.conf.j2", "hadoop.conf.j2"],
                 "master_only": True},
                {"remote_path": KMEANS_CONFIG_PATH,
                 "files": ["kmeans.conf.j2"],
                 "master_only": True},
                {"remote_path": posixpath.join(intel_hibench_spark.SPARK_PATH, "conf"),
                 "files": ["spark-defaults.conf.j2"],
                 "master_only": False}
                ]
  for elem in data_files:
    for file in elem["files"]:
      local_path = data.ResourcePath(posixpath.join("intel_hibench_benchmark", file))
      remote_path = os.path.splitext(posixpath.join(elem["remote_path"], file))[0]
      if elem["master_only"]:
        master.RenderTemplate(local_path, remote_path, hibench_conf)
      else:
        vm_util.RunThreaded(lambda vm: vm.RenderTemplate(local_path, remote_path, hibench_conf),
                            vms)


def _RunWorkloads(master):
  workloads_to_run = FLAGS.intel_hibench_workloads
  workloads_paths = _GetWorkloadPaths(workloads_to_run)
  for inter_path in workloads_paths:
    workload_path = '{0}/bin/workloads/{1}'.format(HIBENCH_PATH, inter_path)
    prepare_cmd = '{0}/prepare/prepare.sh'.format(workload_path)
    run_cmd = '{0}/{1}/run.sh'.format(workload_path, FLAGS.intel_hibench_framework)
    master.RemoteCommand(prepare_cmd)
    master.RemoteCommand(run_cmd)


def _GetWorkloadPaths(workloads_to_run):
  workloads_paths = []
  for workload in workloads_to_run:
    for category, entry in WORKLOAD_CATEGORIES.items():
      if workload in entry['workloads']:
        workloads_paths.append(posixpath.join(category, workload))
  return workloads_paths


def _ParseRelevantMetricsFile(master, hibench_report_file):
  results = []
  software_metadata = _GetSoftwareMetadata(master)
  basic_conf = _ReadGeneratedConfig(os.path.join(vm_util.GetTempDir(), GENERATED_CONFIG_FILE))
  output_conf = _ParseConfigurationMetadata(basic_conf, master)
  out, _ = master.RemoteCommand('cat {0}'.format(hibench_report_file))
  raw_samples = out.strip().splitlines()
  column_headers = raw_samples[0].split()
  throughput_units = ""
  throughput_index = 0
  for idx, header in enumerate(column_headers):
    match_obj = re.match(r"throughput\((.*)\)", header.lower())
    if match_obj:
      throughput_units = match_obj.groups()[0]
      throughput_index = idx
      break
  for raw_sample in raw_samples[1:]:
    metadata = {"configuration": output_conf}
    metadata.update(software_metadata)
    throughput_value = 0
    for i, column_value in enumerate(raw_sample.split()):
      if i == throughput_index:
        throughput_value = round(float(column_value), 3)
      else:
        metadata[column_headers[i]] = column_value
    results.append(sample.Sample('Throughput', throughput_value, throughput_units, metadata))
  return results


def _GetSoftwareMetadata(master):
  metadata = {}
  regex_obj = re.search(r"(\d+)(\.\d+)?(\.\d+)?", HIBENCH_GIT_ARCHIVE)
  hibench_version = ""
  if regex_obj:
    for group in regex_obj.groups():
      if group:
        hibench_version += group
  metadata["hibench_version"] = hibench_version
  out, _ = master.RemoteCommand('readlink -f `which java`')
  out = out.strip()
  metadata["java_version"] = out[out.index("jvm/") + 4:out.index('/jre')]
  metadata["math_library"] = "F2JBLAS 1.1"
  metadata["spark_version"] = "Apache Spark {0}".format(FLAGS.intel_hibench_spark_version)
  metadata["hadoop_version"] = "Apache Hadoop {0}".format(FLAGS.intel_hibench_hadoop_version)
  metadata["scala_version"] = FLAGS.intel_hibench_scala_version
  hdfs_site_file = data.ResourcePath(posixpath.join("intel_hibench_benchmark", "hdfs-site.xml.j2"))
  replication_factor = _GetHdfsReplicationFactor(hdfs_site_file)
  metadata["filesystem"] = "HDFS (RF = {0})".format(replication_factor)
  return metadata


def _GetHdfsReplicationFactor(file):
  with open(file) as f:
    data = f.read().splitlines()
    replication_factor = ""
    for i, line in enumerate(data):
      if "dfs.replication" in line:
        value = data[i + 1]
        replication_factor = value[value.find("<value>") + 7:value.find("</value>")]
        break
    return replication_factor


def _ParseConfigurationMetadata(basic_conf, master):
  output_conf = {}
  conf_params = [
      "hibench.scale.profile",
      "hibench.default.map.parallelism",
      "hibench.default.shuffle.parallelism",
      "hibench.spark.master",
      "hibench.yarn.executor.num",
      "hibench.yarn.executor.cores",
      "spark.executor.memory",
      "spark.driver.memory"
  ]
  for param in conf_params:
    output_conf[param] = basic_conf[param]
  output_conf["disks_number"] = len(basic_conf["mountpoints"])
  if _IsStaticDeployment(master):
    mountpoint = basic_conf["mountpoints"][0]
    disk_size, _ = master.RemoteCommand(
        "df --total -h {0} | tail -n 1 | awk '{{print $2}}'".format(mountpoint))
    output_conf["disk_size"] = disk_size.strip()
  else:
    output_conf["disk_size"] = "{0}G".format(basic_conf["disk_size"])

  return output_conf


def _GetLogs(vm, logdir):
  logs_archive_vm = posixpath.join(INSTALL_DIR, "hibench-logs.tar.gz")
  vm.RemoteCommand(
      "tar czf {0} -C {1} {2}".format(logs_archive_vm, posixpath.dirname(logdir),
                                      posixpath.basename(logdir)))
  logs_archive = os.path.join(vm_util.GetTempDir(), 'hibench-logs.tar.gz')
  vm.PullFile(logs_archive, logs_archive_vm)


def _CleanupMountpoints(vm):
  mountpoints = CONFIG_DATA["scratch_disks"]["mountpoints"]
  for mnt in mountpoints:
    vm.RemoteCommand("rm -rf {0}".format(posixpath.join(mnt, "*")), ignore_failure=True)


def _StopFirewall(vm):
  if vm.BASE_OS_TYPE == 'debian':
    vm.RemoteCommand("sudo ufw disable",
                     ignore_failure=True,
                     suppress_warning=True)
  elif vm.BASE_OS_TYPE == 'rhel':
    vm.RemoteCommand("sudo service firewalld stop",
                     ignore_failure=True,
                     suppress_warning=True)


def CheckPrerequisites(config):
  if FLAGS.intel_hibench_framework not in FRAMEWORKS:
    raise Exception("Framework {0} not supported".format(FLAGS.intel_hibench_framework))
  for workload in FLAGS.intel_hibench_workloads:
    if workload not in WORKLOADS:
      raise Exception("Workload {0} not supported".format(workload))


def GetConfig(user_config):
  global DISK_CONFIG

  logging.info("HiBench GetConfig")

  # Load the benchmark configuration
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)

  # We do this instead of _IsStaticDeployment because we don't have acces to the vms
  if "static_vms" in config["vm_groups"]["target"]:
    nodes = len(config["vm_groups"]["target"]["static_vms"])
    config["vm_groups"]["target"]["vm_count"] = nodes
  else:
    target_config = config["vm_groups"]["target"]
    DISK_CONFIG["disk_count"] = target_config["disk_count"]
    DISK_CONFIG["cloud_mountpoint"] = target_config["disk_spec"][FLAGS.cloud]["mount_point"]
    DISK_CONFIG["disk_size"] = target_config["disk_spec"][FLAGS.cloud]["disk_size"]
  return config


def _TuneHosts(vms):
  namenode = vms[0]
  limits_conf_template = [
      "{0} hard nofile 200000",
      "{0} soft nofile 100000",
      "{0} hard nproc 200000",
      "{0} soft nproc 100000"
  ]
  limits_conf = '\n'.join(limits_conf_template).format(namenode.user_name)
  tuning_cmds = [
      "sudo sysctl -w  kernel.pid_max=458752",
      "echo 100000 | sudo tee /proc/sys/kernel/threads-max",
      "printf '{0}' | sudo tee /{1}".format(limits_conf, LIMITS_CONFIG_FILE)
  ]
  vm_util.RunThreaded(lambda vm: vm.RemoteCommand(
      '; '.join(tuning_cmds)),
      vms)


def _PrepareEnv(master):
  vms = [master] + master.slaves
  # Backup /etc/hosts before we overwrite it
  vm_util.RunThreaded(lambda vm: vm.BackupFiles(FILES_TO_SAVE), vms)
  # Start with minimal hosts file
  default_hosts = '127.0.0.1 localhost'
  vm_util.RunThreaded(lambda vm: vm.RemoteCommand(
      "echo '{0}' | sudo tee /etc/hosts".format(default_hosts)),
      vms)


def _RestartHadoop(vms):
  master = vms[0]
  hadoop.StopYARN(master)
  hadoop.StopHDFS(master)
  hadoop.StopHistoryServer(master)
  vm_util.RunThreaded(lambda vm: hadoop.CleanHadoopTmp(
      vm, CONFIG_DATA["scratch_disks"]["mountpoints"]), vms)
  hadoop.StartHadoop(master, vms[1:])
  master.RemoteCommand("{0}/hadoop fs -mkdir -p /usr/spark_events".format(
      hadoop.HADOOP_BIN))


def Prepare(benchmark_spec):
  vms = benchmark_spec.vm_groups['target']
  master = vms[0]
  slaves = vms[1:]
  master.slaves = slaves
  # Get CONFIG_DATA. This is so we only run _ReadConfig once.
  global CONFIG_DATA
  CONFIG_DATA = _ReadConfig(master)
  _TuneHosts(vms)
  _PrepareEnv(master)
  vm_util.RunThreaded(_StopFirewall, vms)
  _InitFlags()
  _InstallHibench(master)
  _InstallFrameworks(master, CONFIG_DATA)
  hibench_conf = _GetHibenchConfiguration(master, CONFIG_DATA)
  _WriteGeneratedConfig(os.path.join(vm_util.GetTempDir(), GENERATED_CONFIG_FILE), hibench_conf)
  _ApplyConfig(hibench_conf, master)
  benchmark_spec.always_call_cleanup = True


def Run(benchmark_spec):
  vms = benchmark_spec.vm_groups['target']
  master = vms[0]
  _SetHadoopInHomeDir(master)
  _RestartHadoop(vms)
  _RunWorkloads(master)
  hibench_report_dir = posixpath.join(HIBENCH_PATH, 'report')
  hibench_report_file = posixpath.join(hibench_report_dir, 'hibench.report')
  results = _ParseRelevantMetricsFile(master, hibench_report_file)
  _GetLogs(master, hibench_report_dir)
  return results


def Cleanup(benchmark_spec):
  vms = benchmark_spec.vm_groups['target']
  master = vms[0]
  vm_util.RunThreaded(lambda vm: vm.RestoreFiles(FILES_TO_SAVE), vms)
  _SetHadoopInHomeDir(master)
  vm_util.RunThreaded(_CleanupMountpoints, vms)
  hadoop.StopAll(master)
  # call the command again to cleanup everything that StopAll() sometimes creates
  vm_util.RunThreaded(_CleanupMountpoints, vms)
  if _IsStaticDeployment(master):
    master.RemoteCommand("rm -rf {0}".format(hadoop.HADOOP_LOCAL_SCRATCH),
                         ignore_failure=True)
  vm_util.RunThreaded(lambda vm: vm.RemoteCommand("rm -rf {0}".format(hadoop.HADOOP_DIR), ignore_failure=True), vms)
  vm_util.RunThreaded(lambda vm: vm.RemoteCommand("sudo rm -f /{0}".format(LIMITS_CONFIG_FILE), ignore_failure=True), vms)
  if FLAGS.intel_hibench_framework == "spark":
    intel_hibench_spark.Stop(master)
    vm_util.RunThreaded(lambda vm: vm.Uninstall("intel_hibench_spark"), vms)
  master.Uninstall("maven")
