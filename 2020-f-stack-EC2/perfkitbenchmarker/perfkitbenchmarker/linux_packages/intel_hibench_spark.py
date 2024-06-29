import logging
import posixpath
from perfkitbenchmarker import data
from absl import flags
from perfkitbenchmarker import vm_util
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker.linux_packages import hadoop

FLAGS = flags.FLAGS

COMMON_PACKAGES = ('openjdk', 'wget')
SCALA_URL = 'https://downloads.lightbend.com/scala/{0}/scala-{0}.'
SPARK_URL = 'https://archive.apache.org/dist/spark/spark-{0}/spark-{0}-bin-hadoop2.7.tgz'
SPARK_PATH = '/usr/local/spark/'
SPARK_ENV_TEMPLATE = """
export SPARK_MASTER_HOST='{spark_master_host}'
export JAVA_HOME={java_home}
"""
FILES_TO_SAVE = {
    "system_files": [
        "/etc/hosts",
        "/etc/bash.bashrc"
    ],
    "user_files": [
        "~/.ssh/authorized_keys"
    ]
}

PACKAGE_NAME = 'intel_hibench_spark'
PREPROVISIONED_DATA = {
    'scala-{0}.deb'.format('2.11.0'):
        'f0c7e7524eddd88bde56b485e4cb049ca4c8c059c01a8345e5dee3ec425bc73d',
    'scala-{0}.rpm'.format('2.11.0'):
        'ac69d92044380b3479b06bc17c67101d5abcda9d3bbe5868c670eaa8d6396b55',
    'spark-{0}-bin-hadoop2.7.tgz'.format('2.2.2'):
        '70e0a42d0174836a3a9cedfe3669d628b884e0c6d9df555ee9bd825d3dac0c74'
}
PACKAGE_DATA_URL = {
    'scala-{0}.deb'.format('2.11.0'): SCALA_URL.format('2.11.0') + 'deb',
    'scala-{0}.rpm'.format('2.11.0'): SCALA_URL.format('2.11.0') + 'rpm',
    'spark-{0}-bin-hadoop2.7.tgz'.format('2.2.2'): SPARK_URL.format('2.2.2')
}


def _InstallScala(vm, scala_url):
  scala_file = scala_url[scala_url.rindex('/') + 1:]
  if scala_file not in PREPROVISIONED_DATA:
    PREPROVISIONED_DATA[scala_file] = ''  # will only work with preprovision_ignore_checksum
    PACKAGE_DATA_URL[scala_file] = scala_url
  vm.InstallPreprovisionedPackageData(
      PACKAGE_NAME,
      [scala_file],
      INSTALL_DIR
  )


def AptInstall(vm):
  scala_url = SCALA_URL.format(FLAGS.intel_hibench_scala_version)
  scala_url += 'deb'
  _InstallScala(vm, scala_url)
  scala_deb_file = scala_url[scala_url.rindex('/') + 1:]
  scala_install_cmd = 'sudo dpkg -i {0}'.format(scala_deb_file)
  _Install(vm, scala_install_cmd)


def YumInstall(vm):
  vm.InstallPackages('which')
  scala_url = SCALA_URL.format(FLAGS.intel_hibench_scala_version)
  scala_url += 'rpm'
  _InstallScala(vm, scala_url)
  scala_rpm_file = scala_url[scala_url.rindex('/') + 1:]
  scala_install_cmd = 'sudo yum install -y {0}'.format(scala_rpm_file)
  _Install(vm, scala_install_cmd)


def _Install(vm, scala_install_cmd):
  vm.BackupFiles(FILES_TO_SAVE)
  for package in COMMON_PACKAGES:
    vm.Install(package)
  spark_url = SPARK_URL.format(FLAGS.intel_hibench_spark_version)
  spark_tar = spark_url[spark_url.rindex('/') + 1:]
  if spark_tar not in PREPROVISIONED_DATA:
    PREPROVISIONED_DATA[spark_tar] = ''  # will only work with preprovision_ignore_checksum
    PACKAGE_DATA_URL[spark_tar] = spark_url
  vm.InstallPreprovisionedPackageData(
      PACKAGE_NAME,
      [spark_tar],
      INSTALL_DIR
  )
  cmds = [
      'cd {0}'.format(INSTALL_DIR),
      scala_install_cmd,
      'tar xf {0}'.format(spark_tar),
      'sudo mv {0} {1}'.format(spark_tar[:spark_tar.rindex('.')], SPARK_PATH),
      "echo 'export PATH=$PATH:{0}' | sudo tee -a /etc/bash.bashrc".format(SPARK_PATH + "bin"),
  ]
  vm.RemoteCommand(' && '.join(cmds))


def ConfigureAndStart(master, slaves, deploy_mode="standalone", extra_config={}):
  logging.info("Configuring spark")
  vms = [master] + slaves
  _EnablePasswordlessSsh(master)
  hosts_content = '{0} master\n'.format(master.internal_ip)
  slaves_content = ''
  for idx, slave in enumerate(slaves):
    slave_idx = str(idx).zfill(2)
    hosts_content += '{0} slave{1}\n'.format(slave.internal_ip, slave_idx)
    slaves_content += 'slave{0}\n'.format(slave_idx)
  cmd = 'echo "{0}" | sudo tee -a /etc/hosts'.format(hosts_content)
  vm_util.RunThreaded(lambda vm: vm.RemoteCommand(cmd), vms)

  out, _ = master.RemoteCommand('readlink -f `which java`')
  out = out.strip()
  java_home = out[:out.index('/jre')]
  spark_env_content = SPARK_ENV_TEMPLATE.format(spark_master_host=master.internal_ip,
                                                java_home=java_home)
  cmds = [
      'sudo cp {0}conf/spark-env.sh.template {0}conf/spark-env.sh'.format(SPARK_PATH),
      'echo "{0}" | sudo tee -a {1}conf/spark-env.sh'.format(spark_env_content, SPARK_PATH),
      'echo "{0}" | sudo tee -a {1}conf/slaves'.format(slaves_content, SPARK_PATH),
  ]
  master.RemoteCommand(' && '.join(cmds))
  if deploy_mode == "yarn-client":
    cmds = [
        'echo "export HADOOP_CONF_DIR={0}" | sudo tee -a /etc/bash.bashrc'.format(
            hadoop.HADOOP_CONF_DIR),
        'source /etc/bash.bashrc',
    ]
    master.RemoteCommand(' && '.join(cmds))
  else:
    cmds = [
        'source /etc/bash.bashrc',
        '{0}sbin/start-all.sh'.format(SPARK_PATH)
    ]
    master.RemoteCommand(' && '.join(cmds))


def _EnablePasswordlessSsh(master):
  vms = [master] + master.slaves

  # Create the SSH keys
  for vm in vms:
    _, _, retcode = vm.RemoteCommandWithReturnCode('file -f  ~/.ssh/id_rsa', ignore_failure=True,
                                                   suppress_warning=True)
    if retcode != 0:
      vm.RemoteCommand('ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa')

  # Enable full-mesh SSH
  for vm in vms:
    ssh_key, _ = vm.RemoteCommand("cat ~/.ssh/id_rsa.pub")
    vm_util.RunThreaded(
        lambda wm: wm.RemoteCommand("echo '{0}' >> ~/.ssh/authorized_keys".format(ssh_key)), vms)

  # Add entries to /etc/hosts
  cmds = []
  for i, vm in enumerate(vms):
    cmds.append("echo '{0} node{1}' | sudo tee -a /etc/hosts".format(vm.internal_ip, str(i + 1)))
  cmd = " ; ".join(cmds)
  vm_util.RunThreaded(lambda vm: vm.RemoteCommand(cmd), vms)


def Stop(master):
  master.RemoteCommand(posixpath.join(SPARK_PATH, 'sbin', 'stop-all.sh'), ignore_failure=True)


def YumUninstall(vm):
  vm.RemoteCommand("sudo yum -y remove scala")
  _Uninstall(vm)


def AptUninstall(vm):
  vm.RemoteCommand("sudo apt -y remove scala")
  _Uninstall(vm)


def _Uninstall(vm):
  vm.RemoteCommand("sudo rm -rf {0}".format(SPARK_PATH), ignore_failure=True)
  vm.RestoreFiles(FILES_TO_SAVE)
  for package in COMMON_PACKAGES:
    vm.Uninstall(package)
