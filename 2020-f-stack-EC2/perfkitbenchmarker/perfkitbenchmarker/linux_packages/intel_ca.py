import posixpath

CERTIFICATE_URL = 'http://certificates.intel.com/repository/certificates/IntelSHA256RootCA-Base64.crt'
CERTIFICATE_FILE = 'IntelSHA256RootCA-Base64.crt'

RHEL_CA_DIR = '/etc/pki/ca-trust/source/anchors'
RHEL_CA_UPDATE_CMD = 'sudo update-ca-trust'

DEBIAN_CA_DIR = '/usr/local/share/ca-certificates'
DEBIAN_CA_UPDATE_CMD = 'sudo /usr/sbin/update-ca-certificates'


def _Uninstall(vm, certificate_dir, update_cmd):
  cert_file = posixpath.join(certificate_dir, CERTIFICATE_FILE)
  vm.RemoteCommand('sudo rm -f {0}'.format(cert_file))
  vm.RemoteCommand(update_cmd)


def _Install(vm, certificate_dir, update_cmd):
  vm.InstallPackages('wget')
  vm.RemoteCommand('sudo wget -P {0} {1}'.format(certificate_dir, CERTIFICATE_URL))
  vm.RemoteCommand(update_cmd)


def YumInstall(vm):
  """YumInstall invoked for RHEL based distros."""
  _Install(vm, RHEL_CA_DIR, RHEL_CA_UPDATE_CMD)


def YumUninstall(vm):
  """YumUninstall invoked for RHEL based distros."""
  _Uninstall(vm, RHEL_CA_DIR, RHEL_CA_UPDATE_CMD)


def AptInstall(vm):
  """AptInstall invoked for Debian based distros."""
  _Install(vm, DEBIAN_CA_DIR, DEBIAN_CA_UPDATE_CMD)


def AptUninstall(vm):
  """AptUninstall invoked for RHEL based distros."""
  _Uninstall(vm, DEBIAN_CA_DIR, DEBIAN_CA_UPDATE_CMD)
