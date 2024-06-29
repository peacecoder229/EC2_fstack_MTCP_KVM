# Intel parallel studio runtime
import logging
import time


def _RetriedPackageInstaller(vm, cmd):
  """
  The observed issue with the servers that host the Intel Parallel Studio Runtime is
  that from time to time, for unknown reasons, they fail to supply the required files
  for installation. In the hope that it will recover by itself, we try to issue the
  install commands for a number of times. If still no luck, we raise and Exception
  and let PKB framework handle the gracefully teardown of the benchmark.
  """
  RETRY_COUNT = 5
  SLEEP_TIME_SECONDS = 0.5  # we sleep a bit for every request to not flood
  # the destination server with requests and give
  # it time to (hopefully) recover and work
  for i in range(RETRY_COUNT):
    logging.info("Round %d/%d of %s" % (i + 1, RETRY_COUNT, cmd))
    _, _, return_value = vm.RemoteCommandWithReturnCode(cmd, ignore_failure=True)
    if return_value == 0:
      return
    time.sleep(SLEEP_TIME_SECONDS)
  raise Exception('The command "%s" failed to execute %d times in a row. Aborting benchmark run.' % (cmd, RETRY_COUNT))


def YumInstall(vm):
  cmds = [
      'sudo rpm --import https://yum.repos.intel.com/2020/setup/RPM-GPG-KEY-intel-psxe-runtime-2020',
      'sudo rpm -Uhv https://yum.repos.intel.com/2020/setup/intel-psxe-runtime-2020-reposetup-1-0.noarch.rpm',
      'sudo yum install intel-psxe-runtime -y',
      'echo "source /opt/intel/psxe_runtime/linux/bin/psxevars.sh" | sudo tee -a /etc/bash.bashrc'
  ]
  for cmd in cmds:
    _RetriedPackageInstaller(vm, cmd)


def AptInstall(vm):
  cmds = [
      'sudo wget https://apt.repos.intel.com/2020/GPG-PUB-KEY-INTEL-PSXE-RUNTIME-2020 -P /tmp',
      'sudo apt-key add /tmp/GPG-PUB-KEY-INTEL-PSXE-RUNTIME-2020',
      'sudo touch /etc/apt/sources.list.d/intel-psxe-runtime-2020.list',
      'echo "deb https://apt.repos.intel.com/2020 intel-psxe-runtime main" | sudo tee -a /etc/apt/sources.list.d/intel-psxe-runtime-2020.list',
      'sudo apt-get update',
      'sudo apt-get install -y intel-psxe-runtime'
  ]
  for cmd in cmds:
    _RetriedPackageInstaller(vm, cmd)
