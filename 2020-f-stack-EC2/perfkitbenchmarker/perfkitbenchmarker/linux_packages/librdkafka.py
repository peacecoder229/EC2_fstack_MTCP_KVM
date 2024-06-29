from perfkitbenchmarker import errors


def _Install(vm):
  """Configure and install librdkafka on the VM"""
  vm.RemoteCommand('curl -L https://github.com/edenhill/librdkafka/archive/v0.11.6.tar.gz -o /tmp/librdkafka.tar.gz')
  vm.RemoteCommand('mkdir -p /tmp/librdkafka')
  vm.RemoteCommand('tar -xf /tmp/librdkafka.tar.gz -C /tmp/librdkafka --strip 1')
  vm.RemoteCommand('sudo chmod 777 -R /tmp/librdkafka')
  vm.RemoteCommand('cd /tmp/librdkafka && ./configure --prefix=/usr/local')
  vm.RemoteCommand('cd /tmp/librdkafka && make -j `cat /proc/cpuinfo | grep processor | wc -l`')
  vm.RemoteCommand('cd /tmp/librdkafka && sudo make install')
  vm.RemoteCommand('sudo ldconfig')
  vm.RemoteCommand('sudo mkdir -p /usr/lib64')
  vm.RemoteCommand('if [[ ! -f /usr/lib64/librdkafka.so.1 ]]; then sudo ln -s /usr/local/lib/librdkafka.so.1 /usr/lib64/librdkafka.so.1;fi')
  vm.RemoteCommand('if [[ ! -f /usr/lib64/librdkafka++.so.1 ]]; then sudo ln -s /usr/local/lib/librdkafka++.so.1 /usr/lib64/librdkafka++.so.1;fi')
  vm.RemoteCommand('sudo rm -rf /tmp/librdkafka')


def YumInstall(vm):
  """Installs Kafka dependencies on the VM."""
  vm.InstallPackages('libtool-ltdl-devel python-devel python-pip openssl openssl-devel zlib-devel')
  vm.InstallPackageGroup('Development Tools')
  _Install(vm)


def AptInstall(vm):
  """Installs Kafka dependencies on the VM."""
  try:
    # some distributions/versions will have gcc-8 in their default repository
    # vm.InstallPackages('gcc-8')
    # don't use InstallPackages() because it will retry "many" times
    vm.AptUpdate()
    vm.RemoteCommand('sudo DEBIAN_FRONTEND=\'noninteractive\' /usr/bin/apt-get -y install gcc-8')
  except errors.VirtualMachine.RemoteCommandError:
    # some distributions/version will NOT have gcc-8 in their default repository
    vm.RemoteCommand('sudo add-apt-repository ppa:ubuntu-toolchain-r/test -y && '
                     'sudo apt-get update')
    vm.RemoteCommand('sudo apt-get remove gcc -y', ignore_failure=True)
    vm.InstallPackages('gcc-8')
  vm.InstallPackages('libstdc++-8-dev autoconf bison flex libtool pkg-config build-essential python python-dev openssl libssl-dev zlib1g-dev')
  _Install(vm)


def SwupdInstall(vm):
  vm.InstallPackages('openssl os-testsuite-phoronix-server devpkg-zlib')
  _Install(vm)
