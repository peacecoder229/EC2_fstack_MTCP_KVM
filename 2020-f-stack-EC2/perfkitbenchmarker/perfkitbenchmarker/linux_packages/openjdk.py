# Copyright 2014 PerfKitBenchmarker Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Module containing OpenJDK installation and cleanup functions."""
import logging
import posixpath
import re
from typing import Optional

from perfkitbenchmarker.linux_packages import INSTALL_DIR
from absl import flags
from perfkitbenchmarker import vm_util

PACKAGE_NAME = 'openjdk'

OPENJDK_TAR = 'openjdk-{0}_linux-{1}_bin.tar.gz'
ARCH_X86 = "x64"
ARCH_ARM = "aarch64"
URL_VERSIONS = {
    9: '9.0.4',
    11: '11.0.2',
    13: '13.0.2',
    14: '14.0.1',
    15: '15'
}

PREPROVISIONED_DATA = {
    OPENJDK_TAR.format(URL_VERSIONS[9], ARCH_X86): '39362fb9bfb341fcc802e55e8ea59f4664ca58fd821ce956d48e1aa4fb3d2dec',
    OPENJDK_TAR.format(URL_VERSIONS[11], ARCH_X86): '99be79935354f5c0df1ad293620ea36d13f48ec3ea870c838f20c504c9668b57',
    OPENJDK_TAR.format(URL_VERSIONS[13], ARCH_X86): 'acc7a6aabced44e62ec3b83e3b5959df2b1aa6b3d610d58ee45f0c21a7821a71',
    OPENJDK_TAR.format(URL_VERSIONS[14], ARCH_X86): '22ce248e0bd69f23028625bede9d1b3080935b68d011eaaf9e241f84d6b9c4cc',
    OPENJDK_TAR.format(URL_VERSIONS[15], ARCH_X86): 'bb67cadee687d7b486583d03c9850342afea4593be4f436044d785fba9508fb7',
    OPENJDK_TAR.format(URL_VERSIONS[15], ARCH_ARM): '01e7e07dd8a67a65b32fdcaff75ba3f21cd9cfc749287e7c9b1c6037f96a3537'
}

PACKAGE_DATA_URL = {
    OPENJDK_TAR.format(URL_VERSIONS[9], ARCH_X86): 'https://download.java.net/java/GA/jdk9/9.0.4/binaries/'
                                                   'openjdk-9.0.4_linux-x64_bin.tar.gz',
    OPENJDK_TAR.format(URL_VERSIONS[11], ARCH_X86): 'https://download.java.net/java/GA/jdk11/9/GPL/'
                                                    'openjdk-11.0.2_linux-x64_bin.tar.gz',
    OPENJDK_TAR.format(URL_VERSIONS[13], ARCH_X86): 'https://download.java.net/java/GA/jdk13.0.2/d4173c8532314'
                                                    '32d94f001e99d882ca7/8/GPL/openjdk-13.0.2_linux-x64_bin.tar.gz',
    OPENJDK_TAR.format(URL_VERSIONS[14], ARCH_X86): 'https://download.java.net/java/GA/jdk14.0.1/664493ef4a694'
                                                    '6b186ff29eb326336a2/7/GPL/openjdk-14.0.1_linux-x64_bin.tar.gz',
    OPENJDK_TAR.format(URL_VERSIONS[15], ARCH_X86): 'https://download.java.net/java/GA/jdk15/779bf45e88a44cbd9'
                                                    'ea6621d33e33db1/36/GPL/openjdk-15_linux-x64_bin.tar.gz',
    OPENJDK_TAR.format(URL_VERSIONS[15], ARCH_ARM): 'https://download.java.net/java/GA/jdk15/779bf45e88a44cbd9'
                                                    'ea6621d33e33db1/36/GPL/openjdk-15_linux-aarch64_bin.tar.gz'
}

FLAGS = flags.FLAGS
JAVA_DIR = posixpath.join(INSTALL_DIR, 'openjdk')
JAVA_EXE = posixpath.join(JAVA_DIR, 'bin', 'java')
JAVA_HOME = '/usr'

flags.DEFINE_string('openjdk_url', None, 'URL of custom openjdk that will be download and installed. '
                                         'Tarball may be supplied with URL and --data_search_paths '
                                         'to use preprovisioned data. List of predefined URLs: '
                                         '{}'.format(list(PACKAGE_DATA_URL.values())))

flags.DEFINE_integer('openjdk_version', 8, 'Version of openjdk to use when installing from the system. It will be '
                                           'ignored if openjdk_url is specified.')


def _InstallJdkFromTar(vm):
  vm.RemoteCommand('mkdir -p {0}'.format(JAVA_DIR))
  filename = posixpath.basename(FLAGS.openjdk_url)
  if filename not in PREPROVISIONED_DATA:
    PREPROVISIONED_DATA[filename] = ''
    PACKAGE_DATA_URL[filename] = FLAGS.openjdk_url
  vm.InstallPreprovisionedPackageData(PACKAGE_NAME, [filename], JAVA_DIR)
  vm.RemoteCommand('tar -C {0} --strip-components=1 -xzf {0}/{1}'.format(JAVA_DIR, filename))


def _InstallJdkFromSystem(vm, pkg_names):
  pkg_name = None
  for pkg in pkg_names:
    if vm.HasPackage(pkg):
      pkg_name = pkg
      break

  if pkg_name:
    vm.InstallPackages(pkg_name)
  else:
    raise ValueError("openjdk {} not found in system packages, tried the following package names: {}. "
                     "Consider installing via openjdk_url flag.".format(FLAGS.openjdk_version, pkg_names))


def YumInstall(vm):
  if FLAGS.openjdk_url:
    _InstallJdkFromTar(vm)
    vm.RemoteCommand('sudo alternatives --install /usr/bin/java java {0} 1 '
                     '&& sudo alternatives --set java {0}'.format(JAVA_EXE))
  else:
    vm.Install('epel_release')
    pkg_names = (
        'java-1.{}.0-openjdk-devel'.format(FLAGS.openjdk_version),
        'java-{}-openjdk-devel'.format(FLAGS.openjdk_version),
        # 'latest' packages need to use full version to match, not just major - so we're using a '*' here
        'java-latest-openjdk-{}*'.format(FLAGS.openjdk_version)
    )
    _InstallJdkFromSystem(vm, pkg_names)


def AptInstall(vm):
  if FLAGS.openjdk_url:
    _InstallJdkFromTar(vm)
    vm.RemoteCommand('sudo update-alternatives --install /usr/bin/java java {0} 1 '
                     '&& sudo update-alternatives --set java {0}'.format(JAVA_EXE))
  else:
    # Ubuntu only has one package naming convention
    pkg_name = 'openjdk-{0}-jdk'.format(FLAGS.openjdk_version)

    @vm_util.Retry()
    def _AddRepository(vm):
      """Install could fail when Ubuntu keyservers are overloaded."""
      vm.RemoteCommand('sudo add-apt-repository -y ppa:openjdk-r/ppa && sudo apt-get update')

    if not vm.HasPackage(pkg_name):
      _AddRepository(vm)
    _InstallJdkFromSystem(vm, [pkg_name])

    # Populate the ca-certificates-java's trustAnchors parameter.
    vm.RemoteCommand('sudo /var/lib/dpkg/info/ca-certificates-java.postinst configure')


def AptUninstall(vm):
  if FLAGS.openjdk_url:
    # Remove Java from alternatives if not a system package, otherwise allow VM package cleanup to remove
    vm.RemoteCommand('sudo update-alternatives --remove java {0}'.format(JAVA_EXE))


def YumUninstall(vm):
  if FLAGS.openjdk_url:
    # Remove Java from alternatives if not a system package, otherwise allow VM package cleanup to remove
    vm.RemoteCommand('sudo alternatives --remove java {0}'.format(JAVA_EXE))


def CheckJavaMajorVersion(vm) -> int:
  """Checks JRE major version installed on VM.

  This function assumes that Java is installed and will throw exceptions
  in case of any fail to determine it's version.
  There are actually 2 ways of describing Java version:
  * 1.X.yy - which basically describes major version X
  * X.yy - new format for describing major version X

  Returns:
    Major version of installed JRE, or None if not installed.

  Raises:
    RuntimeError, when Java is not installed or version cannot be determined.
  """
  java_output_regex = re.compile(r'openjdk version "(\d+\.\d+\..*?)".*?')
  java_version_old_format_regex = re.compile(r'1\.(\d+)\..*')
  java_version_new_format_regex = re.compile(r'(\d+)\.\d+\..*')

  no_java_msg = "Command 'java' not found"

  _, output = vm.RemoteCommand("java -version")  # why output goes to stderr, not stdout?
  full_version_match = java_output_regex.match(output)

  if full_version_match:
    full_version_str = full_version_match.group(1)

    old_format_match = java_version_old_format_regex.match(full_version_str)
    if old_format_match:
      version = int(old_format_match.group(1))
      logging.info(f"Detected Java version {version}")
      return version

    new_version_match = java_version_new_format_regex.match(full_version_str)
    if new_version_match:
      version = int(new_version_match.group(1))
      logging.info(f"Detected Java version {version}")
      return version

    raise RuntimeError(f"Cannot determine Java major version from:\n{full_version_str}")
  elif no_java_msg in output:
    raise RuntimeError(f"Java is not installed on this machine")
  else:
    raise RuntimeError(f"Cannot determine Java version from output:\n{output}")
