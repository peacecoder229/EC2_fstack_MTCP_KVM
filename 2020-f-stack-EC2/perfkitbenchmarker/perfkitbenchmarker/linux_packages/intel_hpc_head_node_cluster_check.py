from perfkitbenchmarker import vm_util
from absl import flags

FLAGS = flags.FLAGS
flags.DEFINE_integer('intel_hpc_CC_version', 2019, 'Cluster Checker Version')
flags.DEFINE_float('intel_hpc_CC_update_number', 8, 'Cluster Checker update number')
flags.DEFINE_string('intel_hpc_CC_build_number', '048', 'Cluster Checker build number')


def YumInstall(head_node):
  vm = head_node
  cc_full_version = (str(FLAGS.intel_hpc_CC_version) + '.' + str(int(FLAGS.intel_hpc_CC_update_number))
                     + '-' + FLAGS.intel_hpc_CC_build_number)
  vm.RemoteCommand('sudo yum-config-manager --enable '
                   'rhui-REGION-rhel-server-extras '
                   'rhui-REGION-rhel-server-optional')
  vm.InstallPackages('compat-libstdc++-33 gcc libstdc++-devel')

  cmds = [
      'sudo rpm --import https://yum.repos.intel.com/intel-gpg-keys/'
      'GPG-PUB-KEY-INTEL-SW-PRODUCTS-{0}.PUB'.format(FLAGS.intel_hpc_CC_version),
      'sudo yum-config-manager --add-repo https://yum.repos.intel.com/clck/{0}/setup/intel-clck-{0}.repo'
      .format(FLAGS.intel_hpc_CC_version),
      'sudo yum-config-manager --add-repo https://yum.repos.intel.com/clck-ext/{0}/setup/'
      'intel-clck-ext-{0}.repo'.format(FLAGS.intel_hpc_CC_version)
  ]
  vm.RemoteCommand(" && ".join(cmds))
  vm.InstallPackages("intel-clck-{0} intel-clck-hpc-platform".format(cc_full_version))
  cmds = [
      'sudo yum-config-manager --add-repo http://yum.repos.intel.com/hpc-platform/el7/setup/intel-hpc-platform.repo',
      'sudo rpm --import http://yum.repos.intel.com/hpc-platform/el7/setup/PUBLIC_KEY.PUB'
  ]
  vm.RemoteCommand(" && ".join(cmds))
  vm.InstallPackages("intel-hpc-platform-*")
  cmds = [
      'sudo yum-config-manager --add-repo https://yum.repos.intel.com/intelpython/setup/intelpython.repo'
  ]
  vm.RemoteCommand(" && ".join(cmds))
  vm.InstallPackages("intelpython2 intelpython3")
  vm.InstallPackages("infiniband-diags libfabric")

  if FLAGS.aws_efa:
    vm.RemoteCommand('sudo yum -y remove rdma')
    vm.InstallPackages('cmake gcc libnl3-devel libudev-devel make pkgconfig valgrind-devel cmake3 '
                       'ninja-build pandoc')
    cmds = ['git clone --depth 1 -b v27.0 https://github.com/linux-rdma/rdma-core.git',
            'cd rdma-core',
            'bash build.sh',
            'cd -']
    vm.RemoteCommand(" && ".join(cmds))

    cmds = ["echo -e '\nexport RDMA_CORE_PATH=\"$PWD/rdma-core/build\"' |  tee -a ~/.bashrc",
            "echo -e '\nexport LD_LIBRARY_PATH=\"$RDMA_CORE_PATH/lib:$LD_LIBRARY_PATH\"'"
            "| tee -a ~/.bashrc"]
    vm.RemoteCommand(" && ".join(cmds))


def AptInstall(head_node):
  raise Exception("APT base installer not available for Cluster Checker")
