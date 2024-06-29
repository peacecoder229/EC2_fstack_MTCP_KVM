"""Module containing Intel webtier-provisioning scripts installation"""

import os
import yaml
from six.moves.configparser import ConfigParser
from perfkitbenchmarker import data, vm_util, sample, os_types
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from absl import flags

FLAGS = flags.FLAGS

WORDPRESS_VERSIONS = ['v4.2', 'v5.2']
OSS_PERF_BASE_URL = 'https://gitlab.devtools.intel.com/DCSP/HHVM/oss-performance'

flags.DEFINE_string('intel_webtier_provisioning_mariadb_config', None,
                    'The configuration used by MariaDB. Can be either '
                    '1s-bkm or 2s-bkm. If nothing is specified, it will '
                    'be chosen automatically for optimal performance.')
flags.DEFINE_string('intel_webtier_provisioning_version', 'v1.1.1',
                    'The webtier-provisioning version to be used')
flags.DEFINE_string('intel_webtier_provisioning_url',
                    'https://gitlab.devtools.intel.com/DCSP/CWA/webtier-provisioning/',
                    'The web URL of the webtier-provisioning repo to be used, without the .git '
                    'and ending in /')
flags.DEFINE_string('intel_webtier_provisioning_hhvm_perf_version', 'v1.5.6',
                    'The hhvm-perf version to be used.')
flags.DEFINE_string('intel_webtier_provisioning_hhvm_perf_url',
                    'https://gitlab.devtools.intel.com/DCSP/HHVM/hhvm-perf/',
                    'The web URL of the hhvm-perf repo to be used, without the .git '
                    'and ending in /')
flags.DEFINE_string('intel_webtier_provisioning_oss_performance_version', 'v1.0.0.intel',
                    'The oss_performance version to be used')
flags.DEFINE_string('intel_webtier_provisioning_oss_performance_url',
                    '{0}-php/'.format(OSS_PERF_BASE_URL),
                    'The web URL of the oss-performance default v4.2 repo to be used, '
                    'without the .git and ending in /. Please use the appropriate URL '
                    'when intending to use the 5.2 version')
flags.DEFINE_enum('intel_wordpress_version', 'v4.2',
                  WORDPRESS_VERSIONS,
                  'The wordpress workload version to be used. Current '
                  'supported versions are v4.2 and v5.2, default being '
                  'v4.2.')
MARIADB_FLAG_LIST = [
    'query_cache_type',
    'query_cache_size',
    'query_cache_limit',
    'table_open_cache',
    'key_buffer_size',
    'thread_stack',
    'innodb_buffer_pool_instances',
    'innodb_thread_concurrency'
]
for mariadb_flag in MARIADB_FLAG_LIST:
  flags.DEFINE_integer(mariadb_flag, None,
                       'Self explanatory parameter related to mysql.')

PREREQ_PKGS = [
    "software-properties-common",
    "apt-transport-https",
    "iputils-ping",
    "python",
    "python3",
    "python3-pip",
    "ansible"
]

"""Prereq packages specific for CLR"""
PREREQ_PKGS_CLR = [
    "python-basic",
    "which",
    "clr-network-troubleshooter",
    "git",
    "ansible"
]

"""Mysql cnf files path on different distros"""
UBUNTU_MYSQL_PATH = '/etc/mysql/my.cnf'
CLR_MYSQL_PATH = '/etc/mariadb/my.cnf'
RHEL_MYSQL_PATH = '/etc/my.cnf'

WEBTIER_PROV_DIR_NAME = 'webtier-provisioning'
WEBTIER_PROV_DIR = os.path.join(INSTALL_DIR, WEBTIER_PROV_DIR_NAME)


def _OnPrem(vm):
  return FLAGS["http_proxy"].present or FLAGS["https_proxy"].present


def YumInstall(vm):
  """Installs the pre-req packages on the CentOS VM."""
  vm.InstallEpelRepo()
  PREREQ_PKGS.append("openssh-clients")
  vm.InstallPackages(' '.join(PREREQ_PKGS))


def AptInstall(vm):
  """Installs the pre-req packages on the Ubuntu VM."""
  vm.Install('ansible')
  vm.InstallPackages(' '.join(PREREQ_PKGS))


def SwupdInstall(vm):
  """Installs the pre-req packages on the ClearLinux VM."""
  vm.InstallPackages(' '.join(PREREQ_PKGS_CLR))


def ProvisionVMs(vm, group):
  WEBTIER_BASENAME = 'webtier-provisioning'
  WEBTIER_PROV_VERSION = FLAGS.intel_webtier_provisioning_version
  HHVM_PERF_VERSION = FLAGS.intel_webtier_provisioning_hhvm_perf_version

  WEBTIER_PROV_URL = '{0}-/archive/{1}/{2}-{1}.tar.gz'.format(
      FLAGS.intel_webtier_provisioning_url,
      WEBTIER_PROV_VERSION,
      WEBTIER_BASENAME)

  vm_util.IssueCommand(['mkdir',
                        vm_util.PrependTempDir(group)])

  # get webtier-provisioning locally and copy it to VM
  prov_path = os.path.join(vm_util.GetTempDir(), group,
                           '{0}.tar.gz'.format(WEBTIER_BASENAME))
  cmd = ['curl',
         '-SL',
         '--noproxy',
         'gitlab.devtools.intel.com',
         WEBTIER_PROV_URL,
         '-o',
         prov_path
         ]
  vm_util.IssueCommand(cmd)

  # extract tar and rename dir on VM
  vm.RemoteCopy(prov_path, INSTALL_DIR)
  webtier_prov_tagged_dir = '{0}-{1}'.format(WEBTIER_BASENAME,
                                             WEBTIER_PROV_VERSION)
  cmds = ['cd ' + INSTALL_DIR,
          'tar xvf {0}.tar.gz'.format(WEBTIER_BASENAME),
          'mv {0} {1}'.format(webtier_prov_tagged_dir, WEBTIER_PROV_DIR_NAME),
          'echo {0} > {1}'.format(WEBTIER_PROV_VERSION,
                                  os.path.join(WEBTIER_PROV_DIR_NAME, 'version_tag'))
          ]
  vm.RemoteCommand(' && '.join(cmds))

  # extract tar locally to modify config files
  vm_util.IssueCommand(['tar', '-C', os.path.join(vm_util.GetTempDir(), group),
                        '-xvf', prov_path])
  vm_util.IssueCommand(['mv',
                        os.path.join(vm_util.GetTempDir(), group, webtier_prov_tagged_dir),
                        os.path.join(vm_util.GetTempDir(), group, WEBTIER_PROV_DIR_NAME)])

  # webtier/hosts
  hosts_path = os.path.join(vm_util.GetTempDir(), group, WEBTIER_PROV_DIR_NAME,
                            'webtier', 'hosts')
  mariadb_vars = os.path.join('webtier', 'roles', 'mariadb', 'vars',
                              'main.yml')
  # webtier/roles/mariadb/vars/main.yml
  mariadb_vars_path = os.path.join(vm_util.GetTempDir(), group, WEBTIER_PROV_DIR_NAME,
                                   mariadb_vars)
  # override hhvm/hosts config
  cfg = ConfigParser(allow_no_value=True)
  cfg.read(hosts_path)
  cfg.set('target', 'localhost')
  cfg.set('target:vars', 'target_username', vm.user_name)
  cfg.set('target:vars', 'target_hostname', vm.hostname)
  cfg.set('target:vars', 'ansible_connection', 'local')
  cfg.set('target:vars', 'base_dir', INSTALL_DIR)
  cfg.set('target:vars', 'hhvm_perf_version', HHVM_PERF_VERSION)
  cfg.set('target:vars', 'webtier_prov_version', WEBTIER_PROV_VERSION)
  if FLAGS["http_proxy"].present:
    cfg.set('target:vars', 'http_proxy', FLAGS.http_proxy)
  if FLAGS["https_proxy"].present:
    cfg.set('target:vars', 'https_proxy', FLAGS.https_proxy)
  if not _OnPrem(vm):
    # tell webtier-provsioning not to use Intel proxies
    cfg.set('target:vars', 'set_internal_proxy', 'no')

  with open(hosts_path, 'w') as f:
    cfg.write(f)
  # copy hhvm/hosts
  vm.RemoteCopy(hosts_path, os.path.join(WEBTIER_PROV_DIR, 'webtier'))

  # set MariaDB configuration
  with open(mariadb_vars_path) as stream:
    config = yaml.load(stream, Loader=yaml.FullLoader)
  config['my_cnf'] = _GetMariaDBConfig(vm)
  with open(mariadb_vars_path, 'w') as stream:
    yaml.dump(config, stream)
  vm.RemoteCopy(mariadb_vars_path, os.path.join(WEBTIER_PROV_DIR, mariadb_vars))

  # clean up local
  vm_util.IssueCommand(['rm', '-rf', os.path.join(vm_util.GetTempDir(), group)])


def OssInstallOnServer(vm):
  HHVM_PERF_VERSION = FLAGS.intel_webtier_provisioning_hhvm_perf_version
  OSS_PERF_VERSION = FLAGS.intel_webtier_provisioning_oss_performance_version
  HHVM_PERF_URL = '{0}-/archive/{1}/hhvm-perf-{1}.tar.gz'.format(
      FLAGS.intel_webtier_provisioning_hhvm_perf_url,
      HHVM_PERF_VERSION)

  # webtier-provisioning also installs hhvm-perf if the repo is accessible,
  # but if the VM is not on the Intel network, we have to copy the hhvm-perf
  # tarball into webtier-provisioning's dir structure
  if not _OnPrem(vm):
    local_hhvm_perf_version_file = vm_util.PrependTempDir("hhvm_perf_version_tag")
    with open(local_hhvm_perf_version_file, "w") as f:
      f.write(HHVM_PERF_VERSION)
    # get hhvm-perf and copy to webtier-provisioning dir structure
    perf_path = vm_util.PrependTempDir('hhvm-perf.tar.gz')
    cmds = [['curl',
             '-SL', '--noproxy', 'gitlab.devtools.intel.com',
             HHVM_PERF_URL,
             '-o', perf_path],
            # extract tarball so we can rename root dir to 'hhvm-perf'
            ['tar', '-C', vm_util.GetTempDir(), '-xvf', perf_path],
            ['mv', vm_util.PrependTempDir('hhvm-perf-' + HHVM_PERF_VERSION),
             vm_util.PrependTempDir('hhvm-perf')],
            ['cp', local_hhvm_perf_version_file, vm_util.PrependTempDir('hhvm-perf/version_tag')],
            ['rm', '-r', perf_path]]
    for cmd in cmds:
      vm_util.IssueCommand(cmd)
    # set the cwd to 'tempdir' for this command so the tarball won't preserve
    # the entire dir structure
    vm_util.IssueCommand(['tar', '-czvf', perf_path, 'hhvm-perf'],
                         cwd=vm_util.GetTempDir())
    vm.RemoteCopy(perf_path,
                  os.path.join(WEBTIER_PROV_DIR, 'webtier', 'roles', 'hhvm-perf', 'files'))
    vm_util.IssueCommand(['rm', '-rf', perf_path])
    vm_util.IssueCommand(['rm', '-rf', os.path.join(vm_util.GetTempDir(), 'hhvm-perf')])


  # webtier-provisioning also installs oss-performance with php-harness if the repo is accessible,
  # but if the VM is not on the Intel network, we have to copy the oss-performance
  # tarball into webtier-provisioning's dir structure
  if not _OnPrem(vm):
    # Depending on the version specified, populate the oss-performance
    # URLs and variables accordingly
    oss_vars = _PopulateWorkloadURLs()
    local_oss_version_file = vm_util.PrependTempDir("oss_perf_version_tag")
    with open(local_oss_version_file, "w") as f:
      f.write(OSS_PERF_VERSION)
    # get oss-performance and copy to webtier-provisioning dir structure
    oss_path = vm_util.PrependTempDir('oss-performance.tar.gz')
    oss_repo_name = oss_vars['oss_repo_name']
    cmds = [['curl',
             '-SL', '--noproxy', 'gitlab.devtools.intel.com',
             oss_vars['php_oss_url'],
             '-o', oss_path],
            # extract tarball so we can rename root dir to 'hhvm-perf'
            ['tar', '-C', vm_util.GetTempDir(), '-xvf', oss_path],
            ['mv',
             vm_util.PrependTempDir(oss_repo_name),
             vm_util.PrependTempDir('oss-performance')],
            ['cp', local_oss_version_file, vm_util.PrependTempDir('oss-performance/version_tag')],
            ['rm', '-r', oss_path]]
    for cmd in cmds:
      vm_util.IssueCommand(cmd)
    # set the cwd to 'tempdir' for this command so the tarball won't preserve
    # the entire dir structure
    vm_util.IssueCommand(['tar', '-czvf', oss_path, 'oss-performance'],
                         cwd=vm_util.GetTempDir())
    vm.RemoteCopy(oss_path,
                  os.path.join(WEBTIER_PROV_DIR, oss_vars['oss_files_dir']))

    vm_util.IssueCommand(['rm', '-rf', oss_path])
    vm_util.IssueCommand(['rm', '-rf', os.path.join(vm_util.GetTempDir(), 'oss-performance')])


def _PopulateWorkloadURLs():
  wordpress_vars_dict = dict()
  oss_perf_version = FLAGS.intel_webtier_provisioning_oss_performance_version
  wordpress_version = FLAGS.intel_wordpress_version
  oss_perf_flavor = ''
  role_name = 'oss-performance'

  if wordpress_version == 'v5.2':
    # Use the WordPress 5.2 specific URLs
    oss_perf_flavor = 'wp5'
    role_name += '-wp5'
  else:
    # Default to WordPress v4.2 when no flag is specified for the workload version
    oss_perf_flavor = 'php'

  workload_url = '{0}-{1}/'.format(OSS_PERF_BASE_URL, oss_perf_flavor)
  wordpress_vars_dict['oss_repo_name'] = 'oss-performance-{0}-{1}'.format(
      oss_perf_flavor, oss_perf_version)
  wordpress_vars_dict['oss_url'] = workload_url
  wordpress_vars_dict['php_oss_url'] = '{0}-/archive/{1}/oss-performance-{2}-{1}.tar.gz'.format(
      workload_url, oss_perf_version, oss_perf_flavor)

  wordpress_vars_dict['oss_files_dir'] = os.path.join(
      'webtier', 'roles', role_name, 'files')
  return wordpress_vars_dict


def TuneMariaDB(vm):
  global MARIADB_FLAG_LIST

  command = ""

  for mariadb_flag in MARIADB_FLAG_LIST:
    if FLAGS[mariadb_flag].present:
      command += " " + mariadb_flag + " " + str(FLAGS[mariadb_flag].value)

  if not command == "":
    full_path_modify_mysql_my_cnf_sh = \
        data.ResourcePath('intel_wordpress_benchmark/modify_mysql_my_cnf.sh')

    vm.RemoteCopy(full_path_modify_mysql_my_cnf_sh, INSTALL_DIR)

    install_dir_modify_mysql_my_cnf_sh = INSTALL_DIR + '/modify_mysql_my_cnf.sh'

    vm.RobustRemoteCommand('chmod 755 ' + install_dir_modify_mysql_my_cnf_sh)

    if vm.BASE_OS_TYPE == os_types.RHEL:
      full_path_my_cnf = RHEL_MYSQL_PATH
    elif vm.BASE_OS_TYPE == os_types.DEBIAN:
      full_path_my_cnf = UBUNTU_MYSQL_PATH
    elif vm.BASE_OS_TYPE == os_types.CLEAR:
      full_path_my_cnf = CLR_MYSQL_PATH

    command = "sudo " + install_dir_modify_mysql_my_cnf_sh + ' ' + full_path_my_cnf + command

    vm.RobustRemoteCommand(command)

    vm.RemoteHostCommand('sudo systemctl restart mariadb')


def _GetMariaDBConfig(vm):
  mariadb_config = FLAGS.intel_webtier_provisioning_mariadb_config
  if mariadb_config is not None:
    return mariadb_config + '.j2'
  else:
    # Choose MadiaDB config based on the numa node count
    if vm.numa_node_count == 1:
      return '1s-bkm.j2'
    else:
      return '2s-bkm.j2'


def AptUninstall(vm):
  _, _, retcode = vm.RemoteCommandWithReturnCode('file -f "{0}"'.format(UBUNTU_MYSQL_PATH),
                                                 ignore_failure=True,
                                                 suppress_warning=True)
  if retcode == 0:
    vm.RemoteCommand('sudo rm "{0}"'.format(UBUNTU_MYSQL_PATH))
    vm.RemoteCommand('sudo apt remove -y mariadb-server')

  # clear out directories
  _Uninstall(vm)


def SwupdUninstall(vm):
  _, _, retcode = vm.RemoteCommandWithReturnCode('file -f "{0}"'.format(CLR_MYSQL_PATH),
                                                 ignore_failure=True,
                                                 suppress_warning=True)
  if retcode == 0:
    vm.RemoteCommand('sudo rm "{0}"'.format(CLR_MYSQL_PATH))
    vm.RemoteCommand('sudo swupd bundle-remove -y mariadb')

  # clear out directories
  _Uninstall(vm)


def YumUnistall(vm):
  _, _, retcode = vm.RemoteCommandWithReturnCode('file -f "{0}"'.format(RHEL_MYSQL_PATH),
                                                 ignore_failure=True,
                                                 suppress_warning=True)
  if retcode == 0:
    vm.RemoteCommand('sudo rm "{0}"'.format(RHEL_MYSQL_PATH))
    vm.RemoteCommand('sudo yum remove -y MariaDB-server MariaDB-client')


  # Clear out directories
  _Uninstall(vm)


def _Uninstall(vm):
  ''' This will just remove webtier-provisioning from the vm.
      It will NOT uninstall the packages installed by webtier-provisioning.
      It will NOT remove its downloaded artifacts, nor revert the system level
      configs it installed.
  '''
  vm.RemoteCommand('sudo rm -rf {0}'.format(WEBTIER_PROV_DIR))
  vm.RemoteCommand('sudo rm -rf {0}'.format(os.path.join(INSTALL_DIR, 'git')))
  vm.RemoteCommand('sudo rm -rf {0}'.format(os.path.join(INSTALL_DIR, 'src')))
