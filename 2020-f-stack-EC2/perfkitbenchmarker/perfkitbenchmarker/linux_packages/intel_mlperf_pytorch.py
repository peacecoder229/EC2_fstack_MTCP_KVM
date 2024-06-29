import logging
import collections
import posixpath
import textwrap
import yaml

from perfkitbenchmarker import data
from perfkitbenchmarker import errors
from absl import flags
from perfkitbenchmarker.linux_packages import INSTALL_DIR

PYTHON_PKGS = ['numpy==1.16.4', 'PyYAML==5.3', 'absl-py']
CENTOS_PKGS = ['python-pip', 'git', 'numactl', 'python36', 'python-devel',
               'python3-devel', 'centos-release-scl', 'devtoolset-7-gcc*'
               'epel-release', 'python-pip', 'opencv', 'opencv-devel',
               'opencv-python', 'boost-devel', 'gflags', 'gflags-devel']
PREREQ_PKGS = ["gcc", "python", "python3", "python3-pip", "urllib3", "bzip2",
               "gcc", "gcc-c++", "gmp-devel", "mpfr-devel",
               "libmpc-devel", "make", "openssl-devel", "bzip2-devel",
               "libffi-devel", "git", "libaio-devel", "libaio", "zlib-devel"]


def _ReadMLPerfConfigYml():
  """Returns Intel MLPerf config yml file data"""
  config_file = 'intel_mlperf/intel_mlperf_config.yml'
  config_data = {}
  with open(data.ResourcePath(config_file)) as cfg_file:
    config_data = yaml.safe_load(cfg_file)
  return config_data


def _DownloadMKL(vm, config_data):
  """Downloads MKL 2019 """
  logging.info("Downloading MKL 2019 ")
  mkl_ver = "mkl2019_3"
  mkl_tar_name = "{0}.tar.gz".format(mkl_ver)
  mkl_path = posixpath.join("$HOME", mkl_tar_name)
  destination = posixpath.join("$HOME", mkl_ver)
  _, _, retcode = vm.RemoteCommandWithReturnCode(
      "aws s3 cp {0} {1}".format(config_data["mkl_s3uri"],
                                 mkl_path), ignore_failure=True)
  if retcode != 0:
    vm.RemoteCommand("curl -o {0} {1}".format(
        mkl_path, config_data["mkl_link"]))
  vm.RemoteCommand("mkdir -p {dest} && sudo chmod 775 {dest} && "
                   "tar -xf {mkl_tgz} --strip-components=1 -C {dest}"
                   .format(dest=destination, mkl_tgz=mkl_path))


def _DownLoadIntelParallelStudioXE(vm, config_data):
  """Downloads Intel Parallel Studio 2019 XE edition"""
  logging.info("Downloading Intel Parallel Studio XE 2019 Composer Edition")
  ips_tar_name = "ipsXE_2019.tgz"
  ips_path = posixpath.join(INSTALL_DIR, ips_tar_name)
  destination = posixpath.join(INSTALL_DIR, "IntelPSXE")
  _, _, retcode = vm.RemoteCommandWithReturnCode(
      "aws s3 cp {0} {1}".format(config_data["intel_parllelstudio_s3uri"],
                                 ips_path), ignore_failure=True)
  if retcode != 0:
    vm.RemoteCommand("curl -o {0} {1}".format(
        ips_path, config_data["intel_parallelstudio_link"]))
  vm.RemoteCommand("mkdir -p {dest} && sudo chmod 775 {dest} && "
                   "tar -xf {ips_tgz} --strip-components=1 -C {dest}"
                   .format(dest=destination, ips_tgz=ips_path))


def _DownloadInt8Models(vm, config_data):
  """Downloads Pre-built(skx, clx) int8 models """
  logging.info("Downloading prebuilt int8 models")
  int8models_tar_name = ('int8_models.tar.tgz')
  int8models_path = posixpath.join(INSTALL_DIR, int8models_tar_name)
  destination = posixpath.join(INSTALL_DIR, "MLPERF_DIR")
  _, _, retcode = vm.RemoteCommandWithReturnCode(
      "aws s3 cp {0} {1}".format(config_data["prebuilt_int8models_s3uri"],
                                 int8models_path), ignore_failure=True)
  if retcode != 0:
    vm.RemoteCommand("curl -o {0} {1}".
                     format(int8models_path,
                            config_data["prebuilt_int8models_link"]))
  vm.RemoteCommand("mkdir -p {dest} && sudo chmod 775 {dest} && "
                   "tar -xf {int8models_tgz} --strip-components=1 -C {dest}"
                   .format(dest=destination, int8models_tgz=int8models_path))


def _DownloadDataset(vm, config_data):
  """Downloads Imagenet dataset"""
  logging.info("Downloading imagenet dataset")
  imagenet_tar_name = ('imagenet_data.tar.gz')
  imagenet_path = posixpath.join(INSTALL_DIR, imagenet_tar_name)
  destination = posixpath.join(INSTALL_DIR, "MLPERF_DIR")
  _, _, retcode = vm.RemoteCommandWithReturnCode(
      "aws s3 cp {0} {1}".format(config_data["imagenet_dataset_s3uri"],
                                 imagenet_path), ignore_failure=True)
  if retcode != 0:
    vm.RemoteCommand("curl -o {0} {1}".
                     format(imagenet_path,
                            config_data["imagenet_dataset_link"]))
  vm.RemoteCommand("mkdir -p {dest} && sudo chmod 775 {dest} && "
                   "tar -xf {img_net_tgz} --strip-components=1 -C {dest}"
                   .format(dest=destination, img_net_tgz=imagenet_path))


def _RunMLPerfPrepareScript(vm, config_data):
  """Runs the intel_mlperf prepare script on the vm"""
  logging.info("Loading the MLPerf Pytorch prepare script")
  pytorch_scriptname = 'intel_mlperf_pytorch_v0.5.sh'
  if config_data["mlperf_pytorch_version"] == 0.5:
    pytorch_scriptname = 'intel_mlperf_pytorch_v0.5.sh'
  mlperf_prepare_script = 'intel_mlperf/{0}'.format(pytorch_scriptname)
  script_path = data.ResourcePath(mlperf_prepare_script)
  dest_path = "$HOME/{0}".format(pytorch_scriptname)
  vm.PushFile(script_path, dest_path)
  logging.info("Preparing MLPerf Pytorch using {0}".format(pytorch_scriptname))
  cpuinfo = _GetVmCpuinfo(vm)
  ncores = cpuinfo.num_cores
  vm.RemoteCommand("chmod u+x $HOME/{scr} && $HOME/{scr} {cores}".
                   format(scr=pytorch_scriptname, cores=ncores))


def _InstallBoost(vm):
  """Installs the Boost_1_72_0 library"""
  logging.info("Install Boost library")
  boost_ver_num = "1_72_0"
  boost_release = "1.72.0"
  commands = [
      'cd $HOME && curl -SL -O https://dl.bintray.com/boostorg/release/{rel}/source/'
      'boost_{ver}.tar.gz'.format(rel=boost_release, ver=boost_ver_num),
      'cd $HOME && tar -xvzf boost_{ver}.tar.gz && '
      'cd $HOME/boost_{ver}'.format(ver=boost_ver_num),
      'echo "\nexport BOOST_ROOT=$HOME/boost_{ver}" | '
      'sudo tee -a /etc/bash.bashrc'.format(ver=boost_ver_num),
      "cd $HOME/boost_{0} && ./bootstrap.sh".format(boost_ver_num),
      "cd $HOME/boost_{0} && ./b2 ".format(boost_ver_num),
      "sudo rm -rf $HOME/boost_{0}.tar.gz".format(boost_ver_num)
  ]
  vm.RemoteCommand(" && ".join(commands))


def _GetVmCpuinfo(vm):
  """Returns cpu info for the vm"""
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


def _InstallIntelPSXE(vm):
  """Installs the Intel Parallel Studio 2019 XE edition on the VM"""
  logging.info("Installing Intel Parallel Studio XE 2019")
  IPS_TGZ = 'ipsXE_2019.tgz'
  ips_path = posixpath.join(INSTALL_DIR, "IntelPSXE")
  vm.RemoteCommand(('cd {0} && '
                    'sed -i "s/decline/accept/g" silent.cfg && '
                    'sudo ./install.sh --silent ./silent.cfg')
                   .format(ips_path))
  e_path = posixpath.join('/opt', 'intel', 'bin')
  ld_path = posixpath.join('/opt', 'intel', 'lib', 'intel64')
  icc_path = posixpath.join('/opt', 'intel', 'compilers_and_libraries_2019', 'linux',
                            'bin', 'compilervars.sh')
  lib_path1 = posixpath.join('/opt', 'intel', 'compilers_and_libraries', 'linux',
                             'compiler', 'lib', 'intel64', 'libiomp5.so')
  lib_path2 = posixpath.join('/lib', 'libiomp5.so')
  env_path = posixpath.join('/etc', 'bash.bashrc')
  vm.RemoteCommand('echo "export PATH={path}:$PATH" | sudo tee -a {env} &&'
                   'echo "export LD_LIBRARY_PATH={ld}:$LD_LIBRARY_PATH" | sudo '
                   'tee -a {env} && '
                   'echo "source {icc} -arch intel64 -platform linux" | sudo '
                   'tee -a {env} && '
                   'sudo ln -s {lib1} {lib2} && sudo rm -rf {dir}/{ips}'.
                   format(env=env_path, icc=icc_path, lib1=lib_path1, lib2=lib_path2,
                          ld=ld_path, path=e_path, dir=INSTALL_DIR, ips=IPS_TGZ))


def YumInstall(vm):
  """Installs the required packages for MLPerf on the VM."""
  PREREQ_PKGS.extend(CENTOS_PKGS)
  vm.InstallPackages(' '.join(PREREQ_PKGS))
  vm.RemoteCommand("sudo yum -y install devtoolset-7-gcc* && "
                   "sudo yum -y install devtoolset-7 && "
                   "source scl_source enable devtoolset-7 && "
                   "sudo yum -y update")
  _Install(vm)


def AptInstall(vm):
  """Installs the pre-req packages on the Ubuntu VM."""
  vm.InstallPackages(' '.join(PREREQ_PKGS))
  _Install(vm)


def _Install(vm):
  """Installs the MLPerf Pytorch required packages on the VM."""
  logging.info("install cmake >=3.11")
  cmake_ver_num = "3.16.0-Linux-x86_64"
  cmake_release = "v3.16"
  vm.RemoteCommand(
      "curl -SL -O https://cmake.org/files/{rel}/cmake-{ver}.tar.gz && "
      "tar -xvzf cmake-{ver}.tar.gz && "
      "cd cmake-{ver}".format(rel=cmake_release, ver=cmake_ver_num))
  CMAKE_DIR = posixpath.join('$HOME', "cmake-{0}".format(cmake_ver_num))
  script = [
      "sudo cp -r {0}/bin /usr/".format(CMAKE_DIR),
      "sudo cp -r {0}/share /usr/".format(CMAKE_DIR),
      "sudo cp -r {0}/man /usr/share/".format(CMAKE_DIR),
      "sudo cp -r {0}/doc /usr/share/".format(CMAKE_DIR),
      'echo "\nexport PATH=/usr/local/bin:$PATH:$HOME/bin" | '
      'sudo tee -a /etc/bash.bashrc',
      "sudo rm -rf cmake-{0}.tar.gz".format(cmake_ver_num)
  ]
  vm.RemoteCommand(" && ".join(script))
  for pkg in PYTHON_PKGS:
    vm.RemoteHostCommand('sudo pip3 install {pkg}'.format(pkg=pkg))
  vm.Install('aws_credentials')
  vm.Install('awscli')
  vm.InstallPackages('gflags gflags-devel')
  config_data = _ReadMLPerfConfigYml()
  _DownloadDataset(vm, config_data)
  _DownloadInt8Models(vm, config_data)
  _DownLoadIntelParallelStudioXE(vm, config_data)
  _DownloadMKL(vm, config_data)
  _InstallBoost(vm)
  _InstallIntelPSXE(vm)
  _RunMLPerfPrepareScript(vm, config_data)


def Uninstall(vm):
  ''' This will only remove the folders from the VM and not uninstall
  all the packages installed during MLPerf prepare stage.
  '''
  mlperf_dir = "$HOME/mlperf_submit"
  vm.RemoteCommand('sudo rm -rf ' + mlperf_dir)
  vm.RemoteCommand('sudo rm -rf ' + INSTALL_DIR + '/git')
