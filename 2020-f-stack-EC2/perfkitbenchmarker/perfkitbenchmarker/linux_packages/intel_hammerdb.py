import logging
import os
import posixpath
import time

from perfkitbenchmarker import data
from perfkitbenchmarker import errors
from absl import flags
from perfkitbenchmarker import os_types
from perfkitbenchmarker import vm_util
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import flag_util


FLAGS = flags.FLAGS

flags.DEFINE_string('intel_hammerdb_postgres_url',
                    'None',
                    'Custom Postgres Tar')
flags.DEFINE_string('intel_hammerdb_postgres_version',
                    'None',
                    'Custom Postgres Version')
flags.DEFINE_string('intel_hammerdb_mysql_url',
                    'None',
                    'Custom Ubuntu MySQL Tar')
flags.DEFINE_string('intel_hammerdb_mysql_deb_lib_url',
                    'None',
                    'Ubuntu 1804 MySQL Debian Libs for HammerDB3.2')
flags.DEFINE_string('intel_hammerdb_package_url',
                    'None',
                    'Hammerdb package source')
flags.DEFINE_string('intel_hammerdb_mysql_version',
                    'None',
                    'Custom MySQL Version')
flags.DEFINE_enum('intel_hammerdb_version',
                  '4.0', ['3.2', '4.0'],
                  'Custom HammerDB Version')
flags.DEFINE_string('intel_hammerdb_mysql_centos_community_common_url',
                    'None',
                    'MySQL community common to support HammerDB')
flags.DEFINE_string('intel_hammerdb_mysql_centos_lib_url',
                    'None',
                    'Custom MySQL community libs to support HammerDB')
flags.DEFINE_string('intel_hammerdb_mysql_password',
                    'Mysql@123',
                    'MySQL Password')
flags.DEFINE_string('intel_hammerdb_arm_compile_flags',
                    '--march=armv8.2-a+crc -O2',
                    'Compile Flags For ARM')

HAMMERDB_PACKAGE_NAME = 'intel_hammerdb'

POSTGRES_URL = 'https://ftp.postgresql.org/pub/source/v13.0/{0}'
MYSQL_URL = 'https://dev.mysql.com/get/Downloads/MySQL-8.0/{0}'
MYSQL_LIB_URL = 'https://downloads.mysql.com/archives/get/p/23/file/{0}'

HAMMERDB_3_2_URL = 'https://github.com/TPC-Council/HammerDB/releases/download/v3.2/{0}'
HAMMERDB_4_0_URL = 'https://github.com/TPC-Council/HammerDB/releases/download/v4.0/{0}'

POSTGRES_FILE_NAME = 'postgresql-13.0.tar.gz'
MYSQL_U2004_FILE_NAME = 'mysql-server_8.0.22-1ubuntu20.04_amd64.deb-bundle.tar'
MYSQL_U1804_FILE_NAME = 'mysql-server_8.0.22-1ubuntu18.04_amd64.deb-bundle.tar'
MYSQL_DEB_LIB_FILE_NAME = 'libmysqlclient20_5.7.28-1ubuntu18.04_amd64.deb'
MYSQL_CENTOS7_FILE_NAME = 'mysql-8.0.22-1.el7.x86_64.rpm-bundle.tar'
MYSQL_CENTOS7_LIB_FILE_NAME = 'mysql-community-libs-5.7.28-1.el7.x86_64.rpm'
MYSQL_CENTOS7_COMMUNITY_COMMON_FILE_NAME = 'mysql-community-common-5.7.29-1.el7.x86_64.rpm'
HAMMERDB_FILE_NAME_3_2 = 'HammerDB-3.2-Linux.tar.gz'
HAMMERDB_FILE_NAME_4_0 = 'HammerDB-4.0-Linux.tar.gz'

PREPROVISIONED_DATA = {MYSQL_U1804_FILE_NAME:
                       '0f66fc552e3852426e530cb7111cb247f8ce5fc5e426f74d53c0c38716edfb77',
                       MYSQL_U2004_FILE_NAME:
                       '6c245ca738d738845411f7ef1bd57decb4e031a322aa1008fb50a3b860080d55',
                       MYSQL_CENTOS7_FILE_NAME:
                       '988f6a575c3e51b451ee384e26558425b534ed62a2098f4b641f9aeb40ec96d0',
                       MYSQL_DEB_LIB_FILE_NAME:
                       '4a83ca93b656c7a0f200db104714fad322c6332cbd9ab151d3b0c8c9713a196c',
                       MYSQL_CENTOS7_COMMUNITY_COMMON_FILE_NAME:
                       '3a17d273cbb9f9e3d65e133bffb615c09cc3dc61b1c0973544a6c3c61ba82ddb',
                       MYSQL_CENTOS7_LIB_FILE_NAME:
                       'af9d5b279d4eb3701f9bc2de51722a4770b752c96b0513f636c889154095065b',
                       POSTGRES_FILE_NAME:
                       '67b09fca40a35360aef82fee43546271e6a04c33276e0093c5fb48653b2f5afa',
                       HAMMERDB_FILE_NAME_3_2:
                       '010d691725a6fd6158f12716afe6e8e0a3fb0c0ffbe5124a76bd598fef84c3d2',
                       HAMMERDB_FILE_NAME_4_0:
                       '9274d8158ba0830e5aafa9263fd865cf61163a0b2c190dfad4d4bf1b61bd6c90'}

PACKAGE_DATA_URL = {MYSQL_U1804_FILE_NAME: MYSQL_URL.format(MYSQL_U1804_FILE_NAME),
                    MYSQL_U2004_FILE_NAME: MYSQL_URL.format(MYSQL_U2004_FILE_NAME),
                    MYSQL_CENTOS7_FILE_NAME: MYSQL_URL.format(MYSQL_CENTOS7_FILE_NAME),
                    MYSQL_DEB_LIB_FILE_NAME: MYSQL_LIB_URL.format(MYSQL_DEB_LIB_FILE_NAME),
                    MYSQL_CENTOS7_COMMUNITY_COMMON_FILE_NAME:
                    MYSQL_LIB_URL.format(MYSQL_CENTOS7_COMMUNITY_COMMON_FILE_NAME),
                    MYSQL_CENTOS7_LIB_FILE_NAME: MYSQL_LIB_URL.format(MYSQL_CENTOS7_LIB_FILE_NAME),
                    POSTGRES_FILE_NAME: POSTGRES_URL.format(POSTGRES_FILE_NAME),
                    HAMMERDB_FILE_NAME_3_2: HAMMERDB_3_2_URL.format(HAMMERDB_FILE_NAME_3_2),
                    HAMMERDB_FILE_NAME_4_0: HAMMERDB_4_0_URL.format(HAMMERDB_FILE_NAME_4_0)}


POSTGRES_INSTALL_DIR = "~/Postgres_pkb"
MYSQL_INSTALL_DIR = "~/MySQL_pkb"
HAMMERDB_INSTALL_DIR = "~/HammerDB_pkb"


def GetHammerDBPackage(vm):
  hammerdb_tar = HAMMERDB_FILE_NAME_4_0
  if FLAGS.intel_hammerdb_version == "3.2":
    hammerdb_tar = HAMMERDB_FILE_NAME_3_2

  hammerdb_url = ''
  if "intel_hammerdb_package_url" in flag_util.GetProvidedCommandLineFlags():
    hammerdb_url = FLAGS.intel_hammerdb_package_url
    hammerdb_tar = hammerdb_url.split('/')[-1]
  return hammerdb_url, hammerdb_tar


def _Install(vm):
  hammerdb_url, hammerdb_tar = GetHammerDBPackage(vm)

  vm.RemoteCommand("mkdir -p {0}".format(HAMMERDB_INSTALL_DIR))
  if hammerdb_tar not in PREPROVISIONED_DATA:
       PREPROVISIONED_DATA[hammerdb_tar] = ''
       PACKAGE_DATA_URL[hammerdb_tar] = hammerdb_url
  vm.InstallPreprovisionedPackageData(HAMMERDB_PACKAGE_NAME,
                                      [hammerdb_tar],
                                      HAMMERDB_INSTALL_DIR)
  vm.RemoteCommand('cd {0} && tar -xzvf {1} --strip-components=1'.format(HAMMERDB_INSTALL_DIR,
                   hammerdb_tar))


def _GetMySQLCentosLibs(vm):
  mysql_centos_community_common_rpm = MYSQL_CENTOS7_COMMUNITY_COMMON_FILE_NAME
  mysql_centos_community_common_url = ''
  if ("intel_hammerdb_mysql_centos_community_common_url" in
      flag_util.GetProvidedCommandLineFlags()):
    mysql_centos_community_common_url = FLAGS.intel_hammerdb_mysql_centos_community_common_url
    mysql_centos_community_common_rpm = mysql_centos_community_common_url.split('/')[-1]

  if mysql_centos_community_common_rpm not in PREPROVISIONED_DATA:
    PREPROVISIONED_DATA[mysql_centos_community_common_rpm] = ''
    PACKAGE_DATA_URL[mysql_centos_community_common_rpm] = mysql_centos_community_common_url

  vm.InstallPreprovisionedPackageData(HAMMERDB_PACKAGE_NAME,
                                      [mysql_centos_community_common_rpm],
                                      HAMMERDB_INSTALL_DIR)

  mysql_centos_lib = MYSQL_CENTOS7_LIB_FILE_NAME
  mysql_centos_lib_url = ''
  if "intel_hammerdb_mysql_centos_lib_url" in flag_util.GetProvidedCommandLineFlags():
    mysql_centos_lib_url = FLAGS.intel_hammerdb_mysql_centos_lib_url
    mysql_centos_lib = mysql_centos_lib_url.split('/')[-1]

  if mysql_centos_lib not in PREPROVISIONED_DATA:
    PREPROVISIONED_DATA[mysql_centos_lib] = ''
    PACKAGE_DATA_URL[mysql_centos_lib] = mysql_centos_lib_url

  vm.InstallPreprovisionedPackageData(HAMMERDB_PACKAGE_NAME,
                                      [mysql_centos_lib],
                                      HAMMERDB_INSTALL_DIR)
  return mysql_centos_community_common_rpm, mysql_centos_lib


def _GetPostgresPackages(vm):
  vm.RemoteCommand('mkdir -p {0}'.format(POSTGRES_INSTALL_DIR))
  postgres_url = ''
  postgres_tar = POSTGRES_FILE_NAME

  if "intel_hammerdb_postgres_url" in flag_util.GetProvidedCommandLineFlags():
    postgres_url = FLAGS.intel_hammerdb_postgres_url
    postgres_tar = postgres_url.split('/')[-1]

  if postgres_tar not in PREPROVISIONED_DATA:
    PREPROVISIONED_DATA[postgres_tar] = ''
    PACKAGE_DATA_URL[postgres_tar] = postgres_url
  vm.InstallPreprovisionedPackageData(HAMMERDB_PACKAGE_NAME,
                                      [postgres_tar],
                                      POSTGRES_INSTALL_DIR)

  cmds = ['cd {0}'.format(POSTGRES_INSTALL_DIR),
          'tar -xvf {0} -C . --strip-components=1'.format(postgres_tar)]
  vm.RemoteCommand(" && ".join(cmds))
  configure_cflags = './configure '
  if FLAGS.intel_hammerdb_platform == 'ARM':
    configure_cflags += ("CFLAGS=" + FLAGS.intel_hammerdb_arm_compile_flags + " || ./configure")
  vm.RemoteCommand('cd {0} && {1}'.format(POSTGRES_INSTALL_DIR, configure_cflags))

  vm.RobustRemoteCommand('cd {0} && make && sudo make install'.format(POSTGRES_INSTALL_DIR))


def YumInstall(vm):
  vm.RemoteCommand('sudo yum -y update && sudo yum -y install gcc')
  _Install(vm)

  if FLAGS.intel_hammerdb_db_type == 'pg':
    vm.RemoteCommand('sudo yum -y install make readline-devel zlib-devel')
    _GetPostgresPackages(vm)
    vm.RemoteCommand('echo -e "\nexport LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/pgsql/lib/"'
                     ' | tee -a ~/.bashrc')
  elif FLAGS.intel_hammerdb_db_type == 'mysql':
    mysql_centos_community_common_rpm, mysql_centos_lib = _GetMySQLCentosLibs(vm)

    # Some of the CSPs seems to have maridb-libs installed which is creating a conflict while
    # installing mysql libs. So removing mariadb packages before the run.
    # If these don't exist, then the failure can be ignored.
    vm.RemoteCommand('rpm -qa | grep mariadb | xargs sudo yum remove -y', ignore_failure=True)

    cmds = ['cd {0} && sudo rpm -i {1}'.format(HAMMERDB_INSTALL_DIR,
                                               mysql_centos_community_common_rpm),
            'cd {0} && sudo rpm -i {1}'.format(HAMMERDB_INSTALL_DIR, mysql_centos_lib),
            'sudo cp /usr/lib64/mysql/libmysqlclient.so.20 {0}'.format(HAMMERDB_INSTALL_DIR)]
    vm.RemoteCommand(" && ".join(cmds))
    _GetMySQLPackages(vm)
    cmds = ['cd {0} && rpm -qpl mysql*.rpm'.format(MYSQL_INSTALL_DIR),
            'sudo yum -y install mysql-community-{server,client,common,libs}-* '
            'sudo service mysqld start',
            'sudo rm -rf /var/lib/mysql',
            'sudo rm -f /var/log/mysqld.log']
    vm.RemoteCommand(" && ".join(cmds))
    vm.RemoteCommand('sudo yum -y install policycoreutils-python')
    vm.RemoteCommand('echo -e "\nexport LD_LIBRARY_PATH={0}:$LD_LIBRARY_PATH" | tee -a ~/.bashrc'
                     .format(HAMMERDB_INSTALL_DIR))


def _GetMySQLPackages(vm):
  mysql_url, mysql_tar = GetMySQLPackageVersions(vm)

  vm.RemoteCommand('mkdir -p {0}'.format(MYSQL_INSTALL_DIR))
  if mysql_tar not in PREPROVISIONED_DATA:
    PREPROVISIONED_DATA[mysql_tar] = ''
    PACKAGE_DATA_URL[mysql_tar] = mysql_url
  vm.InstallPreprovisionedPackageData(HAMMERDB_PACKAGE_NAME,
                                      [mysql_tar],
                                      MYSQL_INSTALL_DIR)
  cmds = ['cd {0}'.format(MYSQL_INSTALL_DIR),
          'tar -xvf {0} -C .'.format(mysql_tar)]
  vm.RemoteCommand(" && ".join(cmds))


def GetMySQLPackageVersions(vm):
  mysql_url = ''
  if "intel_hammerdb_mysql_url" in flag_util.GetProvidedCommandLineFlags():
    mysql_url = FLAGS.intel_hammerdb_mysql_url
    mysql_tar = mysql_url.split('/')[-1]
  elif FLAGS.os_type == 'ubuntu1804':
    mysql_tar = MYSQL_U1804_FILE_NAME
  elif FLAGS.os_type == 'ubuntu2004':
    mysql_tar = MYSQL_U2004_FILE_NAME
  elif FLAGS.os_type == 'centos7':
    mysql_tar = MYSQL_CENTOS7_FILE_NAME
  else:
    raise Exception("Please check if the MySQL package is valid")

  return mysql_url, mysql_tar


def PostgresVersion():
  postgres_default_version = "13"
  if "intel_hammerdb_postgres_version" in flag_util.GetProvidedCommandLineFlags():
    return FLAGS.intel_hammerdb_postgres_version
  return postgres_default_version


def MySQLVersion():
  mysql_default_version = "8.0.22"
  if "intel_hammerdb_mysql_version" in flag_util.GetProvidedCommandLineFlags():
    return FLAGS.intel_hammerdb_mysql_version
  return mysql_default_version


def HammerDBVersion():
  hammerdb_default_version = "3.2"
  if "intel_hammerdb_version" in flag_util.GetProvidedCommandLineFlags():
    return FLAGS.intel_hammerdb_version
  return hammerdb_default_version


def InstallMySQLOnArmUbuntu(vm):
  mysql_arm_package_name = "mysql-8.0.22"
  cmds = ['wget https://dev.mysql.com/get/Downloads/MySQL-8.0/{0}.tar.gz'
          .format(mysql_arm_package_name),
          'sudo tar zxvf ~/{0}.tar.gz -C /scratch'.format(mysql_arm_package_name),
          'cd /scratch/{0}'.format(mysql_arm_package_name),
          'sudo mkdir build',
          'cd build',
          'sudo apt-get install -y g++ libssl-dev libncurses5-dev pkg-config cmake bison ',
          'export CC=/usr/local/bin/gcc',
          'export CXX=/usr/local/bin/g++',
          'sudo cmake  .. -DDOWNLOAD_BOOST=1 -DWITH_BOOST=..',
          'sudo make -j100',
          'sudo make install ']
  vm.RemoteCommand(" && ".join(cmds))


def AptInstall(vm):
  vm.RemoteCommand('sudo apt-get -y update && sudo apt-get install -y gcc')
  _Install(vm)

  if FLAGS.intel_hammerdb_db_type == 'pg':
    vm.RemoteCommand("sudo apt-get -y install libreadline-dev zlib1g-dev make")
    _GetPostgresPackages(vm)
    # Stop the Postgres server running with default settings
    vm.RemoteCommand('sudo systemctl stop postgresql', ignore_failure=True)
  elif FLAGS.intel_hammerdb_db_type == 'mysql':
    password = FLAGS.intel_hammerdb_mysql_password
    debconf_cmds = ["echo 'debconf debconf/frontend select Noninteractive' | "
                    "sudo debconf-set-selections",
                    "sudo apt-get install -y -q",
                    "sudo debconf-set-selections <<< 'mysql-community-server "
                    " mysql-community-server/root-pass {0}'".format(password),
                    "sudo debconf-set-selections <<< 'mysql-community-server "
                    " mysql-community-server/re-root-pass {0}'".format(password),
                    "sudo debconf-set-selections <<< 'mysql-community-server "
                    " mysql-server/default-auth-override  select "
                    " Use Legacy Authentication Method (Retain MySQL 5.x Compatibility)'"]
    debconf_cmds = " && ".join(debconf_cmds)

    vm.RemoteCommand('mkdir -p {0}'.format(MYSQL_INSTALL_DIR))
    _GetMySQLPackages(vm)
    vm.RobustRemoteCommand("cd {0} && sudo dpkg -i *.deb".format(MYSQL_INSTALL_DIR),
                           ignore_failure=True)
    vm.RemoteCommand("{0} && sudo apt-get -y install -f".format(debconf_cmds), ignore_failure=True)
    vm.RemoteCommand("sudo apt --fix-broken install -y", ignore_failure=True)
    # In some systems mysql package starts automatically. This is needed in such
    # scenriaos. This can be ignored if the mysql process is not running.
    vm.RemoteCommand('sudo systemctl stop mysql', ignore_failure=True)

    mysql_deb_lib = MYSQL_DEB_LIB_FILE_NAME
    mysql_deb_lib_url = ''
    if "intel_hammerdb_mysql_deb_lib_url" in flag_util.GetProvidedCommandLineFlags():
      mysql_deb_lib_url = FLAGS.intel_hammerdb_mysql_deb_lib_url
      mysql_deb_lib = mysql_deb_lib_url.split('/')[-1]

    if mysql_deb_lib not in PREPROVISIONED_DATA:
      PREPROVISIONED_DATA[mysql_deb_lib] = ''
      PACKAGE_DATA_URL[mysql_deb_lib] = mysql_deb_lib_url
    vm.InstallPreprovisionedPackageData(HAMMERDB_PACKAGE_NAME,
                                        [mysql_deb_lib],
                                        MYSQL_INSTALL_DIR)
    vm.RemoteCommand('cd {0} && sudo dpkg -i {1}'.format(MYSQL_INSTALL_DIR, mysql_deb_lib))
    vm.RemoteCommand('echo -e "\nexport LD_LIBRARY_PATH={0}:$LD_LIBRARY_PATH" | tee -a ~/.bashrc'
                     .format(MYSQL_INSTALL_DIR))


def _Uninstall(vm):
  vm.RemoteHostCommand('rm -rf {0}'.format(HAMMERDB_INSTALL_DIR))
  if FLAGS.intel_hammerdb_db_type == 'pg':
    vm.RemoteCommand('sudo systemctl stop postgresql')
    vm.RemoteCommand('cd {0} && sudo make uninstall && make clean'.format(POSTGRES_INSTALL_DIR))


def YumUninstall(vm):
  _Uninstall(vm)
  if FLAGS.intel_hammerdb_db_type == 'pg':
    vm.RemoteCommand("rm -rf {0}".format(POSTGRES_INSTALL_DIR))
  elif FLAGS.intel_hammerdb_db_type == 'mysql':
    vm.RemoteCommand('rpm -qa | grep mysql | xargs sudo yum remove -y')
    vm.RemoteCommand("rm -rf {0}".format(MYSQL_INSTALL_DIR))


def AptUninstall(vm):
  _Uninstall(vm)
  if FLAGS.intel_hammerdb_db_type == 'pg':
    vm.RemoteCommand("rm -rf {0}".format(POSTGRES_INSTALL_DIR))
  elif FLAGS.intel_hammerdb_db_type == 'mysql':
    cmds = ["sudo debconf-set-selections <<< 'mysql-community-server "
            " mysql-community-server/remove-data-dir  boolean true'",
            "sudo apt-get -y remove --purge mysql* "]
    vm.RemoteCommand(" && ".join(cmds))
    vm.RemoteCommand("rm -rf {0}".format(MYSQL_INSTALL_DIR))
