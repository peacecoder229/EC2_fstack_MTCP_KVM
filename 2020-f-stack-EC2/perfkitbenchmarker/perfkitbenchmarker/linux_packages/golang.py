"""
Installs golang
"""
import posixpath

from perfkitbenchmarker.linux_packages import INSTALL_DIR
from absl import flags

GO_VERSION = '1.14.3'
GO_DOWNLOAD_URL_FMT = 'https://dl.google.com/go/go{version}.linux-{arch}.tar.gz'
GO_INSTALL_DIR = posixpath.join(INSTALL_DIR, 'go')
GO_BIN_DIR = posixpath.join(GO_INSTALL_DIR, 'bin')
GO_PATH_DIR = posixpath.join(INSTALL_DIR, 'gopath')
GO_PATH_BIN_DIR = posixpath.join(GO_PATH_DIR, 'bin')
GO_BIN = posixpath.join(GO_BIN_DIR, 'go')

FLAGS = flags.FLAGS
flags.DEFINE_string('golang_version', GO_VERSION,
                    'Go version.')


def Install(vm):
  uname = vm.RemoteCommand('uname -m')[0].strip()
  if uname == 'x86_64':
    architecture = 'amd64'
  elif uname == 'aarch64':
    architecture = 'arm64'
  else:
    raise NotImplementedError("unsupported architecture: {}".format(uname))
  download_url = GO_DOWNLOAD_URL_FMT.format(version=FLAGS.golang_version, arch=architecture)
  vm.Install('curl')
  vm.RemoteCommand('cd {} && curl -L {} | tar -xzf -'.format(INSTALL_DIR, download_url))


def Uninstall(vm):
  # INSTALL_DIR will be removed by framework
  pass
