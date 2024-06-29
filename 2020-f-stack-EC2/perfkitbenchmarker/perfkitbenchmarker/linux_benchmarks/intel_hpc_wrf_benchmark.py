import logging
import re
from absl import flags
from perfkitbenchmarker import configs
from perfkitbenchmarker import sample
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import intel_hpc_utils
from perfkitbenchmarker import data
from perfkitbenchmarker import flag_util


FLAGS = flags.FLAGS
flags.DEFINE_integer('intel_hpc_wrf_nodes', '1', 'The number of nodes to use', lower_bound=1)
flags.DEFINE_string('intel_hpc_wrf_image_type', 'avx512', 'Image type for wrf')
flags.DEFINE_string('intel_hpc_wrf_image_version', 'Feb2021', 'Image version for wrf')
flags.DEFINE_string('intel_hpc_wrf_fss_type', 'NFS', 'File Shared System type: FSX or NFS')
flags.DEFINE_boolean('intel_hpc_wrf_CC', False, 'If benchmark runs or not with Cluster Checker')

flags.DEFINE_integer('intel_hpc_wrf_num_tiles', '90', 'The number of tiles to use', lower_bound=90)
flags.DEFINE_integer('intel_hpc_wrf_omp_num_threads', '1', 'The number of threads to use', lower_bound=1)


BENCHMARK_NAME = 'intel_hpc_wrf'
BENCHMARK_CONFIG = """
intel_hpc_wrf:
  description: Runs HPC wrf
  vm_groups:
    head_node:
      os_type: centos7
      vm_spec: *default_hpc_head_node_vm_spec
      disk_spec: *default_hpc_head_node_disk_spec
    compute_nodes:
      os_type: centos7
      vm_spec: *default_hpc_compute_nodes_vm_spec
      disk_spec: *default_hpc_compute_nodes_disk_spec
  flags:
    enable_transparent_hugepages: false
"""
workload = "wrf"


###############################################################################
def CheckPrerequisites(config):
  intel_hpc_utils.CheckPrerequisites(workload)


def GetConfig(user_config):
  # Load the benchmark configuration
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
  config = intel_hpc_utils.GetConfig(config, FLAGS.intel_hpc_wrf_nodes)
  return config


def _GetPackageFromS3(vm, hpc_benchmarks_config):
  mnt_dir = vm.GetScratchDir()
  wrf_bench_package = hpc_benchmarks_config[workload]["package"]
  if vm.CLOUD == 'Static':
    wrf_package_path = hpc_benchmarks_config["image-uri"]
    wrf_bench_package_gz = wrf_bench_package + ".tar.gz"
    _, _, retcode = vm.RemoteCommandWithReturnCode('cd {0} && wget {1}/{2} -O {2}'.format
                                                   (mnt_dir, wrf_package_path,
                                                    wrf_bench_package_gz), ignore_failure=True)
    vm.RemoteCommand("cd {0} && tar -xzf {1}".format(mnt_dir, wrf_bench_package_gz))
  else:
    wrf_package_path = hpc_benchmarks_config["image-bucket"]
    stdout, _ = vm.RemoteCommand('aws s3 ls {0}/{1}'.format(wrf_package_path,
                                 wrf_bench_package))
    if not stdout:
      raise Exception('Package not found!')
    vm.RemoteCommand('cd {0} &&  sudo chmod 775 -R {0} && aws s3 cp {1}/{2} {2} --recursive'
                     .format(mnt_dir, wrf_package_path, wrf_bench_package))
  vm.RemoteCommand("sed -i '/io_form_history/s/2/5/g' {0}/{1}/namelist.input.rst"
                   .format(mnt_dir, wrf_bench_package))


def Prepare(benchmark_spec):
  logging.info("Intel HPC Prepare")
  benchmark_spec.workload_name = "HPC WRF"
  benchmark_spec.sut_vm_group = "compute_nodes"
  intel_hpc_utils.Prepare(benchmark_spec, FLAGS.intel_hpc_wrf_nodes, workload,
                          FLAGS.intel_hpc_wrf_image_type, FLAGS.intel_hpc_wrf_image_version,
                          FLAGS.intel_hpc_wrf_fss_type,
                          FLAGS.intel_hpc_wrf_CC, FLAGS.cloud)

  hpc_benchmarks_config = intel_hpc_utils.GetHpcBenchmarksConfig()
  wrf_bench_package = hpc_benchmarks_config[workload]["package"]

  if intel_hpc_utils.IsClusterMode(FLAGS.intel_hpc_wrf_nodes):
    head_node = benchmark_spec.vm_groups['head_node'][0]
    _GetPackageFromS3(head_node, hpc_benchmarks_config)

    head_node.RemoteCommand("echo -e '\nexport OMP_NUM_THREADS=2' | tee -a ~/.bashrc")
    head_node.RemoteCommand("echo -e '\nexport WRF_NUM_TILES=20' | tee -a ~/.bashrc")
    head_node.RemoteCommand("echo -e '\nexport KMP_AFFINITY=granularity=fine,compact,1,0' | tee -a ~/.bashrc")
    head_node.RemoteCommand("echo -e '\nexport I_MPI_EXTRA_FILESYSTEM=1' | tee -a ~/.bashrc")
    head_node.RemoteCommand("echo -e '\nexport I_MPI_ADJUST_GATHERV=3' | tee -a ~/.bashrc")
    head_node.RemoteCommand("echo -e '\nexport I_MPI_ADJUST_SCATTERV=2' | tee -a ~/.bashrc")
    head_node.RemoteCommand("echo -e '\nexport I_MPI_ADJUST_ALLREDUCE=5' | tee -a ~/.bashrc")
    head_node.RemoteCommand("echo -e '\nexport I_MPI_COLL_INTRANODE=pt2pt' | tee -a ~/.bashrc")
    head_node.RemoteCommand("echo -e '\nexport I_MPI_JOB_RESPECT_PROCESS_PLACEMENT=0' | tee -a ~/.bashrc")
    head_node.RemoteCommand("echo -e '\nexport I_MPI_LUSTRE_STRIPE_AWARE=1' | tee -a ~/.bashrc")
  else:
    vm = benchmark_spec.vms[0]
    mnt_dir = vm.GetScratchDir()
    # If user wants to upload package from the PKB host to SUT
    if "data_search_paths" in flag_util.GetProvidedCommandLineFlags():
      wrf_bench_package = wrf_bench_package + ".tar.bz2"
      localImagePath = data.ResourcePath(wrf_bench_package)
      destPath = mnt_dir
      # Push image from local PKB host machine to VM
      vm.PushFile(localImagePath, destPath)
      vm.RemoteCommand("cd {0} && tar -xjvf {1}".format(mnt_dir, wrf_bench_package))
    else:
      # Get it from S3
      _GetPackageFromS3(vm, hpc_benchmarks_config)

    vm.RemoteCommand("echo -e '\nexport I_MPI_PIN_DOMAIN=auto' | tee -a /tmp/env")
    vm.RemoteCommand("echo -e '\nexport I_MPI_PIN_ORDER=bunch' | tee -a /tmp/env")
    vm.RemoteCommand("echo -e '\nexport OMP_PLACES=cores' | tee -a /tmp/env")
    vm.RemoteCommand("echo -e '\nexport OMP_PROC_BIND=close' | tee -a /tmp/env")
    vm.RemoteCommand("echo -e '\nexport I_MPI_DEBUG=5' | tee -a /tmp/env")
    if FLAGS.intel_hpc_wrf_image_type == 'avx512':
      vm.RemoteCommand("echo -e '\nexport OMP_NUM_THREADS=1' | tee -a /tmp/env")
      vm.RemoteCommand("echo -e '\nexport WRF_NUM_TILES=90' | tee -a /tmp/env")
      vm.RemoteCommand("echo -e '\nexport KMP_STACKSIZE=512M' | tee -a /tmp/env")
      vm.RemoteCommand("echo -e '\nexport WRFIO_NCD_LARGE_FILE_SUPPORT=1' | tee -a /tmp/env")
    elif FLAGS.intel_hpc_wrf_image_type == 'amd':
      vm.RemoteCommand("echo -e '\nexport OMP_NUM_THREADS=4' | tee -a /tmp/env")
      vm.RemoteCommand("echo -e '\nexport OMP_STACKSIZE=512M' | tee -a /tmp/env")
      vm.RemoteCommand("echo -e '\nexport WRF_NUM_TILES=128' | tee -a /tmp/env")


def _DisplayWRFOptions():
  output = ('WRF needs a lot of tuning depending on the machine type.\n' +
            'Please set flags intel_hpc_wrf_num_tiles and intel_hpc_wrf_omp_num_threads \n' +
            'using the combinations below if your run has failed \n' +
            '1 node: WRF_NUM_TILES=90, OMP_NUM_THREADS=1 \n' +
            '2 nodes: WRF_NUM_TILES=80, OMP_NUM_THREADS=2 \n' +
            '4 nodes: WRF_NUM_TILES=60, OMP_NUM_THREADS=2 \n' +
            '8 nodes: WRF_NUM_TILES=100, OMP_NUM_THREADS=4 \n' +
            '16 nodes: WRF_NUM_TILES=20, OMP_NUM_THREADS=2')
  raise Exception(output)


def _CheckFlags(vm):
  if "intel_hpc_wrf_num_tiles" in flag_util.GetProvidedCommandLineFlags():
    vm.RemoteCommand("echo -e '\nexport WRF_NUM_TILES={0}' | tee -a /tmp/env"
                     .format(FLAGS.intel_hpc_wrf_num_tiles))
  if "intel_hpc_wrf_num_omp_threads" in flag_util.GetProvidedCommandLineFlags():
    vm.RemoteCommand("echo -e '\nexport OMP_NUM_THREADS={0}' | tee -a  /tmp/env"
                     .format(FLAGS.intel_hpc_wrf_omp_num_threads))


def Run(benchmark_spec):
  logging.info("Intel HPC Run")
  # PKB bug: If the results array contains no Sample, PKB will execute
  # the Run() method again after the Teardown
  results = []

  if intel_hpc_utils.IsClusterMode(FLAGS.intel_hpc_wrf_nodes):
    head_node = benchmark_spec.vm_groups['head_node'][0]
    compute_nodes = benchmark_spec.vm_groups['compute_nodes']

    cpuinfo = intel_hpc_utils.GetVmCpuinfo(compute_nodes[0])
    num_cores = cpuinfo.num_cores
    np = num_cores * FLAGS.intel_hpc_wrf_nodes

    _CheckFlags(head_node)
    mnt_dir = head_node.GetScratchDir()
    rdma_cmd = ''
    if FLAGS.aws_efa:
      rdma_cmd = ' -B /home/centos/rdma-core:/rdma-core '

    head_node.RemoteCommand('source ~/.bashrc && '
                            'source /opt/intel/psxe_runtime/linux/mpi/intel64/bin/mpivars.sh && '
                            '/opt/intel/psxe_runtime/linux/mpi/intel64/bin/mpiexec.hydra '
                            '-genv I_MPI_DEBUG 5 '
                            '-hostfile {0}/hosts '
                            '-ppn {1} -np {2} '
                            'singularity run -B {0}/bench_2.5km/:/benchmark '
                            .format(mnt_dir, num_cores, np) +
                            rdma_cmd +
                            '--writable-tmpfs --app multinode {0}/{1}.simg '
                            .format(mnt_dir, workload))

    intel_hpc_utils.RunSysinfo(compute_nodes[0], mnt_dir, workload)
    compute_nodes[0].RemoteCommand('singularity run --writable-tmpfs --app multinodeResults {0}/{1}.simg'
                                   .format(mnt_dir, workload))
    vm = compute_nodes[0]
  else:
    vm = benchmark_spec.vms[0]
    _CheckFlags(vm)
    mnt_dir = vm.GetScratchDir()
    vm.RemoteCommand('ulimit -s unlimited && source /tmp/env && singularity run -B '
                     ' {0}/conus2.5km:/benchmark --writable-tmpfs --app '
                     ' singlenode {1}/{2}.simg'.format(mnt_dir, INSTALL_DIR, workload))

    intel_hpc_utils.RunSysinfo(vm, INSTALL_DIR, workload)

  stdout, _ = vm.RemoteCommand("cat {0}*/{1}.results.* | grep merit".format(workload, workload))
  found = re.search(r'(Figure of merit :\s+\w+:)\s+([0-9]*\.[0-9]*) (\w\/\w+)', stdout)
  if found:
    results.append(sample.Sample(found.group(1), found.group(2), found.group(3),
                                 {'primary_sample': True}))
  intel_hpc_utils.GetNodeArchives(vm, vm, workload, FLAGS.intel_hpc_wrf_CC)
  if len(results) == 0:
    _DisplayWRFOptions()
    raise Exception("No results were collected. Please check the log files for possible errors.")

  return results


def Cleanup(benchmark_spec):
  logging.info("Intel HPC Clean")
  intel_hpc_utils.Cleanup(benchmark_spec, FLAGS.intel_hpc_wrf_nodes,
                          workload, FLAGS.intel_hpc_wrf_fss_type, FLAGS.cloud, FLAGS.intel_hpc_wrf_CC)
