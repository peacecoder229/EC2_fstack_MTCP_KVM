# Copyright 2015 PerfKitBenchmarker Authors. All rights reserved.
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
"""Builds and install emon from source.
"""

import posixpath
import os
import logging

from perfkitbenchmarker.linux_packages import INSTALL_DIR
from absl import flags
from perfkitbenchmarker import errors
from perfkitbenchmarker import data
from perfkitbenchmarker import vm_util

flags.DEFINE_string('emon_tarball', None,
                    'Optional, path to emon package. eg --emon_tarball=/tmp/sep_private_5_19_linux_07062101c5153a9.tar.bz2')
flags.DEFINE_string('emon_event_list', None,
                    'Optional, path to emon event list. eg --emon_event_list=/tmp/cascadelake_server_events_nda.txt')
flags.DEFINE_boolean('emon_post_process_skip', False,
                     'Optional, no post processing will be done if supplied')
flags.DEFINE_enum('emon_edp_script_type', 'ruby',
                  ('ruby', 'python3'), 'Optional, default is ruby. eg --emon_edp_script_type=python3 if need to use python script')
flags.DEFINE_string('emon_edp_config', None,
                    'Optional, path to EDP config. eg --emon_edp_config=/tmp/emon_edp_config.txt')
flags.DEFINE_boolean('emon_debug', False,
                     'Optional, for debugging EMON driver, build, collection, and post processing. eg --emon_debug')
FLAGS = flags.FLAGS


UBUNTU_PKGS = ["linux-headers-`uname -r`", "build-essential"]
RHEL_PKGS = ["kernel-devel"]
EMON_SOURCE_TARBALL_DEFAULT = 'sep_private_linux_pkb.tar.bz2'
EMON_SOURCE_TARBALL_DEFAULT_LOCATION_URL_PATH = 'https://cumulus.s3.us-east-2.amazonaws.com/emon'
EMON_SOURCE_TARBALL_DEFAULT_LOCATION_S3_BUCKET = 's3://cumulus/emon'
EMON_INSTALL_DIR = '/opt/emon'
EMON_RESULT_TARBALL = 'emon_result.tar.gz'


EMON_SANITY_CHECK_SCRIPT = """#!/bin/bash
output_dir=$1
EMON_INSTALL_DIR=/opt/emon
$EMON_INSTALL_DIR/sepdk/src/rmmod-sep -s
$EMON_INSTALL_DIR/sepdk/src/insmod-sep
source $EMON_INSTALL_DIR/sep_vars.sh
echo "emon -v > $output_dir/emon-v.dat"
emon -v > $output_dir/emon-v.dat
echo "emon -M > $output_dir/emon-M.dat"
emon -M > $output_dir/emon-M.dat
"""


EMON_START_SCRIPT = """#!/bin/bash
output_dir=$1
emon_event=$2
EMON_INSTALL_DIR=/opt/emon
$EMON_INSTALL_DIR/sepdk/src/rmmod-sep -s
$EMON_INSTALL_DIR/sepdk/src/insmod-sep
source $EMON_INSTALL_DIR/sep_vars.sh
echo "emon -collect-edp $emon_event > $output_dir/emon.dat"
emon -collect-edp $emon_event > $output_dir/emon.dat
"""


EMON_STOP_SCRIPT = """
#!/bin/bash
EMON_INSTALL_DIR=/opt/emon
source $EMON_INSTALL_DIR/sep_vars.sh
$EMON_INSTALL_DIR/bin64/emon -stop
sleep 5
pkill emon
$EMON_INSTALL_DIR/sepdk/src/rmmod-sep -s
"""


EMON_POST_PROCESS_SCRIPT = """
#!/bin/bash
output_dir=$1
edp_script=$2
emon_edp_config=$3
EMON_INSTALL_DIR=/opt/emon
$EMON_INSTALL_DIR/sepdk/src/rmmod-sep -s
$EMON_INSTALL_DIR/sepdk/src/insmod-sep
source $EMON_INSTALL_DIR/sep_vars.sh
cd $output_dir
if ! [[ "$edp_script" == *"ruby"* ]]; then
  script_option="py"
else
  script_option=""
fi

if [ -z $emon_edp_config ]; then
  echo "emon -process-${script_option}edp $EMON_INSTALL_DIR/config/edp/${script_option}edp_config.txt"
  emon -process-${script_option}edp $EMON_INSTALL_DIR/config/edp/${script_option}edp_config.txt
else
  echo "emon -process-${script_option}edp $emon_edp_config"
  emon -process-${script_option}edp $emon_edp_config
fi
"""


def _GetAbsPath(path):
  absPath = os.path.abspath(os.path.expanduser(path))
  if not os.path.isfile(absPath):
    raise RuntimeError('File (%s) does not exist.' % path)

  return absPath


def _GetKernelDevelVerYum(vm):
  # Yum based only
  command = 'sudo yum info kernel-devel | grep {}'
  kernel_ver = []
  for i in ("Version", "Release", "Arch"):
    out, _, _ = vm.RemoteCommandWithReturnCode(command.format(i))
    kernel_ver.append(out[out.index(':') + 1:].strip())

  logging.info("kernel version({})-release({}).arch({})".format(kernel_ver[0], kernel_ver[1], kernel_ver[2]))
  kernel_info = '{}-{}.{}'.format(kernel_ver[0], kernel_ver[1], kernel_ver[2])
  return kernel_info


def _TransferFilesFromAWSWithS3API(vm, aws_source_bucket, target):
  logging.info("Fetching file from AWS S3 bucket using AWS S3 CLI")
  flags.FLAGS.aws_credentials_overwrite = True
  vm.Install('aws_credentials')

  try:
    vm.Install('awscli')
  except:
    logging.info("vm.Install(awscli) failed. See error msg from earlier logs")
    return False

  # will this package be automatically uninstalled? But this is not a workload,
  # and so there is no Cleanup or Teardown

  aws_s3_cmd = 'aws s3 cp {0} {1}'.format(aws_source_bucket, target)
  # ignore failure to avoid raise exception, so that we could handle in a more graceful way
  stdout, stderr, retcode = vm.RemoteCommandWithReturnCode(aws_s3_cmd, ignore_failure=True)

  # we are done with it, let's remove it right away for security reason,
  # especially considering on-prem SUTs which are shared
  vm.Uninstall('aws_credentials')
  vm.Uninstall('awscli')

  if retcode != 0:
    logging.info("Failed to fetch file from AWS S3 with aws_s3_cmd ({}), return stdout ({}), strerr ({})"
                 .format(aws_s3_cmd, stdout, stderr))
    return False
  else:
    return True


def _TransferFilesFromRepoWithCurl(vm, source_url, target):
  logging.info("Fetching file from a given URL using curl. \
               This will only work if target is behind firewall")
  # slower than S3 CLI
  vm.InstallPackages('curl')

  # check returned HTTP header first
  http_fetch_cmd_header = 'curl -I {}'.format(source_url)
  stdout, strerr, retcode = vm.RemoteCommandWithReturnCode(http_fetch_cmd_header, ignore_failure=True)
  if stdout.find('200 OK') < 0:
    logging.info("Failed to get HTTP 200 OK header from source ({}) running http_fetch_cmd_header ({}) with stdout ({})."
                 .format(source_url, http_fetch_cmd_header, stdout))
  else:
    http_fetch_cmd = 'curl -o {} {}'.format(target, source_url)
    stdout, stderr, retcode = vm.RemoteCommandWithReturnCode(http_fetch_cmd, ignore_failure=True)
    if retcode != 0:
      logging.info("Failed to fetch file running cmd ({}) with return stdout ({}) and strerr ({})"
                   .format(http_fetch_cmd, stdout, stderr))
      return False
    else:
      return True


def _TransferFilesFromAWS2Host2SUT(vm, source_url, target_file, target_folder):
  file_local = posixpath.join('/tmp', target_file)

  # if proxy is set in the local env, it needs to be taken by PKB. otherwise,
  # env is not automatically passed to the PKB python "shell"
  if FLAGS.http_proxy and FLAGS.http_proxy != '':
    http_proxy = FLAGS.http_proxy
  else:
    http_proxy = os.environ.get('http_proxy')

  if http_proxy is not None and http_proxy != '':
    http_fetch_cmd = ['curl', '-SL', '--proxy', http_proxy, '-o', file_local, source_url]
  else:
    http_fetch_cmd = ['curl', '-SL', '--noproxy', '*', '-o', file_local, source_url]

  logging.info("copying remote file to local host by running ({})".format(http_fetch_cmd))
  stdout, stderr, retcode = vm_util.IssueCommand(http_fetch_cmd, raise_on_failure=False)
  if retcode != 0:
    logging.info("Fetching command ({}) failed with stdout ({}) and stderr ({}). \
                 Is the proxy environmental variabile being set?"
                 .format(stdout, stderr, http_fetch_cmd))
    return False

  # use framework default exception handling which will spill out error details
  logging.info("copying local tarball ({}) to remote system under ({})".format(file_local, target_folder))
  vm.RemoteCopy(file_local, target_folder, True)
  # exception will be raised by the framework if the copy fails

  return True


def _TransferEMONTarball(vm):
  # default emon_tarball
  emon_tarball = EMON_SOURCE_TARBALL_DEFAULT

  if FLAGS.emon_tarball:
    logging.info("Copying local emon tarball ({}) to remote SUT location ({})"
                 .format(FLAGS.emon_tarball, INSTALL_DIR))
    tarFile_path = _GetAbsPath(FLAGS.emon_tarball)
    _, emon_tarball = os.path.split(FLAGS.emon_tarball)
    vm.RemoteCopy(tarFile_path, INSTALL_DIR, True)
  else:
    download_success = False
    logging.info("Fetching emon tarball from remote repo using AWS S3 CLI")
    s3_image_path = posixpath.join(EMON_SOURCE_TARBALL_DEFAULT_LOCATION_S3_BUCKET, emon_tarball)
    target = posixpath.join(INSTALL_DIR, emon_tarball)
    download_success = _TransferFilesFromAWSWithS3API(vm, s3_image_path, target)

    if not download_success:
      logging.info("As alternative, trying to fetch emon tarball from remote repo using curl to the remote SUT. \
                   This will only work if SUT is behind firewall")

      s3_image_path = posixpath.join(EMON_SOURCE_TARBALL_DEFAULT_LOCATION_URL_PATH, emon_tarball)
      target = posixpath.join(INSTALL_DIR, EMON_SOURCE_TARBALL_DEFAULT)
      download_success = _TransferFilesFromRepoWithCurl(vm, s3_image_path, target)

    # use case: users do not have AWS account or SUT has no Internet connection when direct transfer is not possible
    # download to local PKB host before pushing to the remote SUT
    if not download_success:
      logging.info("Download to local PKB host before pushing to the remote SUT")
      s3_image_path = posixpath.join(EMON_SOURCE_TARBALL_DEFAULT_LOCATION_URL_PATH, emon_tarball)
      download_success = _TransferFilesFromAWS2Host2SUT(vm, s3_image_path, EMON_SOURCE_TARBALL_DEFAULT, INSTALL_DIR)

      if not download_success:
        raise RuntimeError('Failed to download EMON tarball ({}). Quit!' % (emon_tarball))

  return emon_tarball


def _DoSanityCheck(vm):
  """do a sanity check first"""
  logging.info("Start with a simple sanity check on emon")

  # clean up previously collected data
  emon_all_files = posixpath.join(INSTALL_DIR, '*emon*')
  vm.RemoteCommand('sudo rm -f {}'.format(emon_all_files), ignore_failure=True)
  emon_edp_csv = posixpath.join(INSTALL_DIR, '*edp*.csv')
  vm.RemoteCommand('sudo rm -f {}'.format(emon_edp_csv), ignore_failure=True)

  logging.info("emon_sanity_check.sh: {}".format(EMON_SANITY_CHECK_SCRIPT))
  vm.RemoteCommand("echo '{}' > {}/emon_sanity_check.sh".format(EMON_SANITY_CHECK_SCRIPT, INSTALL_DIR))

  cmd_sanity_check = posixpath.join(INSTALL_DIR, 'start_emon_sanity_check.sh')
  vm.RemoteCommand("echo -e '#!/bin/bash\nsudo bash {install_dir}/emon_sanity_check.sh {install_dir}' > {cmd}"
                   .format(install_dir=INSTALL_DIR, cmd=cmd_sanity_check))
  vm.RemoteCommand('chmod +x {}'.format(cmd_sanity_check))

  # let the framework handle exceptions, which will report details as approproate
  vm.RemoteCommand('bash {} > /dev/null'.format(cmd_sanity_check), ignore_failure=False)

  emon_v_dat = posixpath.join(INSTALL_DIR, 'emon-v.dat')
  emon_M_dat = posixpath.join(INSTALL_DIR, 'emon-M.dat')
  logging.info("checking the contents in sanity checking output files ({}) and ({})".format(emon_M_dat, emon_v_dat))
  wc_M, stderr_M, ret_M = vm.RemoteCommandWithReturnCode('wc -c {}'.format(emon_M_dat), ignore_failure=False)
  wc_v, stderr_v, ret_v = vm.RemoteCommandWithReturnCode('wc -c {}'.format(emon_v_dat), ignore_failure=False)
  if ret_M != 0 or ret_v != 0:
    logging.info("Failed to collect emon sanity checking data ({}) and data ({}) with stderr ({}) and ({})"
                 .format(emon_M_dat, emon_v_dat, stderr_M, stderr_v))
    raise RuntimeError('EMON sanity checking script (%s) failed, quit!' % (cmd_sanity_check))
  else:
    # check the str return with num > 0 from wc_M and wc_v
    # "wc -c /opt/pkb/emon-M.dat" ==> "4255 /opt/pkb/emon-M.dat"
    # sample output: wc_M = '4255 /opt/pkb/emon-M.dat'
    # split into an array with multiple strings separated by space,
    # and get the first string, which is 4255 before converting it to int
    # if that int is zero, we didn't get any output
    if int(wc_M.split()[0]) <= 0 or int(wc_v.split()[0]) <= 0:
      err_str = ('EMON sanity checking script ({}) failed with invalid output '
                 ' in ({}) and/or ({}), quit!').format(cmd_sanity_check, emon_M_dat, emon_v_dat)
      raise RuntimeError(err_str)


def _CreateCollectionScripts(vm):
  # create start/stop scripts
  logging.info("emon_start.sh: {}".format(EMON_START_SCRIPT))
  vm.RemoteCommand("echo '{}' > {}/emon_start.sh".format(EMON_START_SCRIPT, INSTALL_DIR))
  logging.info("emon_stop.sh: {}".format(EMON_STOP_SCRIPT))
  vm.RemoteCommand("echo '{}' > {}/emon_stop.sh".format(EMON_STOP_SCRIPT, INSTALL_DIR))

  emon_event_list_name = ''
  if FLAGS.emon_event_list:
    eventFile_path = _GetAbsPath(FLAGS.emon_event_list)
    _, emon_event_list_name = os.path.split(FLAGS.emon_event_list)
    vm.RemoteCopy(eventFile_path, INSTALL_DIR, True)

  # emon_event_list_name is optional. Empty value indicates not being supplied by user
  cmd_start_emon = posixpath.join(INSTALL_DIR, 'start_emon.sh')
  vm.RemoteCommand("echo -e '#!/bin/bash\nsudo bash {install_dir}/emon_start.sh {install_dir} {emon_event}' > {cmd}"
                   .format(install_dir=INSTALL_DIR, emon_event=emon_event_list_name, cmd=cmd_start_emon))
  vm.RemoteCommand('chmod +x {}'.format(cmd_start_emon))
  stdout, stderr, ret = vm.RemoteCommandWithReturnCode('cat {}'.format(cmd_start_emon), ignore_failure=True)
  logging.info("{}: {}".format(cmd_start_emon, stdout))

  cmd_stop_emon = posixpath.join(INSTALL_DIR, 'stop_emon.sh')
  vm.RemoteCommand("echo -e '#!/bin/bash\nsudo bash {install_dir}/emon_stop.sh' > {cmd}"
                   .format(install_dir=INSTALL_DIR, cmd=cmd_stop_emon))
  vm.RemoteCommand('chmod +x {}'.format(cmd_stop_emon))
  stdout, _, _ = vm.RemoteCommandWithReturnCode('cat {}'.format(cmd_stop_emon), ignore_failure=True)
  logging.info("{}: {}".format(cmd_stop_emon, stdout))

  if not FLAGS.emon_post_process_skip:
    emon_edp_script_type_name = FLAGS.emon_edp_script_type
    emon_edp_config_file_name = ''
    if FLAGS.emon_edp_config is not None:
      emon_edp_config_file_full_path = _GetAbsPath(FLAGS.emon_edp_config)
      _, emon_edp_config_file_name = os.path.split(FLAGS.emon_edp_config)
      vm.RemoteCopy(emon_edp_config_file_full_path, INSTALL_DIR, True)

    cmd = "echo '{post_process_script}' > {install_dir}/post_process_emon.sh".format(
        post_process_script=EMON_POST_PROCESS_SCRIPT, install_dir=INSTALL_DIR)
    vm.RemoteCommand(cmd)

    logging.info("post_process_emon.sh: {}".format(EMON_POST_PROCESS_SCRIPT))
    cmd_start_post_process_emon = posixpath.join(INSTALL_DIR, 'start_post_process_emon.sh')
    vm.RemoteCommand("echo -e '#!/bin/bash\nsudo bash {install_dir}/post_process_emon.sh {install_dir} {emon_edp_script_type} {emon_edp_config}' > {cmd}"
                     .format(install_dir=INSTALL_DIR,
                             emon_edp_script_type=emon_edp_script_type_name,
                             emon_edp_config=emon_edp_config_file_name,
                             cmd=cmd_start_post_process_emon))
    vm.RemoteCommand('chmod +x {}'.format(cmd_start_post_process_emon))
    stdout, _, _ = vm.RemoteCommandWithReturnCode('cat {}'.format(cmd_start_post_process_emon), ignore_failure=True)
    logging.info("{}: {}".format(cmd_start_post_process_emon, stdout))


def _Install(vm, kernel_src_dir=''):
  # check input file exists asap, if supplied from command line as an optional flag
  # error out if file does not exist
  if FLAGS.emon_tarball:
    _GetAbsPath(FLAGS.emon_tarball)

  if FLAGS.emon_event_list is not None:
    _GetAbsPath(FLAGS.emon_event_list)

  if FLAGS.emon_edp_config is not None:
    _GetAbsPath(FLAGS.emon_edp_config)

  """Installs emon on vm."""
  logging.info("Installing emon")
  logging.info("kernel_src_dir is ({})".format(kernel_src_dir))

  # transfer tarball to the SUT
  emon_tarball = _TransferEMONTarball(vm)

  # install emon
  vm.RemoteCommand('sudo mkdir -p {}'.format(EMON_INSTALL_DIR))
  isIntel, _ = vm.RemoteCommand('lscpu | grep -c Xeon', ignore_failure=True)
  cpufamily, _ = vm.RemoteCommand('lscpu | grep "CPU family:" | cut -f2 -d:')

  if int(isIntel) > 0 or int(cpufamily) == 6:
    """Intel"""
    vm.RemoteCommand('sudo tar -xf {}/{} -C {} --strip-components=1'
                     .format(INSTALL_DIR, emon_tarball, EMON_INSTALL_DIR))
    vm.RemoteCommand('sudo tar -xf {}/*.tar.* -C {}'
                     .format(EMON_INSTALL_DIR, EMON_INSTALL_DIR))
  elif int(cpufamily) == 23:
    """AMD"""
    vm.RemoteCommand('sudo tar -xf {}/{} -C {} --strip-components=1'
                     .format(INSTALL_DIR, emon_tarball, EMON_INSTALL_DIR))

  emon_original_tarfile = 'sep*linux*.tar.bz2'
  cmd = 'ls -l {}/{}'.format(EMON_INSTALL_DIR, emon_original_tarfile)
  stdout, _, retcode = vm.RemoteCommandWithReturnCode('{}'.format(cmd), ignore_failure=True)
  if retcode == 0:
    logging.info("EMON tarball file size and version info: {}".format(stdout))

  cmd = 'cd {}/sepdk/src; sudo ./build-driver -ni {}'.format(EMON_INSTALL_DIR, kernel_src_dir)
  vm.RemoteCommand(cmd)
  vm.RemoteCommand('sudo {}/sepdk/src/rmmod-sep -s'.format(EMON_INSTALL_DIR))
  # TODO: insmod-sep will fail if kernel header does not match uname -r
  vm.RemoteCommand('sudo {}/sepdk/src/insmod-sep -g root'.format(EMON_INSTALL_DIR))

  # once the install is successfully, remove the downloaded tarball from SUT
  logging.info("rm -f {}/{}".format(INSTALL_DIR, emon_tarball))
  vm.RemoteCommand('rm -f {}/{}'.format(INSTALL_DIR, emon_tarball))

  # quick sanity check
  _DoSanityCheck(vm)

  # create bash scripts for collection, and also for easy debugging
  _CreateCollectionScripts(vm)


def Uninstall(vm):
  if not FLAGS.emon_debug:
    if not FLAGS.emon_post_process_skip:
      emon_edp_csv = posixpath.join(INSTALL_DIR, '*edp*.csv')
      vm.RemoteCommand('sudo rm -f {}'.format(emon_edp_csv), ignore_failure=False)

    # rm emon shell scripts and output emon*.dat files
    emon_all_files = posixpath.join(INSTALL_DIR, '*emon*')
    vm.RemoteCommand('sudo rm -f {}'.format(emon_all_files), ignore_failure=False)

    # rm entire emon install folder
    vm.RemoteCommand('sudo rm -fr {}'.format(EMON_INSTALL_DIR))


def Start(vm):
  """Starts emon collection on vm"""
  script_start_emon = posixpath.join(INSTALL_DIR, 'start_emon.sh')
  logging.info("Starting emon collection script_start_emon ({})".format(script_start_emon))

  # TODO: does not capture error, such as when script_start_emon does not exist,
  # possibly due to putting job into background?
  cmd = 'cd {}; bash {} > /dev/null 2>&1 &'.format(INSTALL_DIR, script_start_emon)
  vm.RemoteCommand(cmd)
  logging.info("EMON collection cmd ({}) started as a background job".format(cmd))


def Stop(vm):
  """Stops emon collection on vm"""
  script_stop_emon = posixpath.join(INSTALL_DIR, 'stop_emon.sh')
  logging.info("Stopping emon with bash script_stop_emon ({}) ...".format(script_stop_emon))
  _, _, retcode = vm.RemoteCommandWithReturnCode("bash {}".format(script_stop_emon), ignore_failure=False)

  if not FLAGS.emon_post_process_skip:
    if FLAGS.emon_edp_script_type == 'ruby':
      logging.info("Installing ruby ...")

      # InstallPackages will be in dead loop if fails, appearing as PKB bug,
      # not returning error, or code, or raise exception?
      jruby_install_succeed = False
      os_file = '/etc/os-release'
      cmd = "[ -f {} ] && echo 'File is present'".format(os_file)
      _, _, retcode = vm.RemoteCommandWithReturnCode('{}'.format(cmd), ignore_failure=True)
      if retcode == 0:
        # ok, the file exists, let's check if containing validated os strings
        jruby_validated_os_list = ['ubuntu 18.04']
        for os_str in jruby_validated_os_list:
          cmd = "cat {} | grep -i '{}' | wc -l".format(os_file, os_str)
          stdout, stderr, retcode = vm.RemoteCommandWithReturnCode('{}'.format(cmd), ignore_failure=True)
          if int(stdout) >= 1:
            logging.info("Identified OS dist ({}). Attempt to install jruby replacing ruby \
                          for multithreaded post processing"
                         .format(os_str))
            vm.InstallPackages('jruby')

            edp_config_file_location = 'config/edp/edp_config.txt'
            # once the install is successfully, revise the edp_config file for multi-threading (default still using ruby)
            cmd = "sudo sed -i 's/RUBY_PATH=\"ruby\"/RUBY_PATH=\"jruby\"/g' {}/{}".format(
                EMON_INSTALL_DIR,
                edp_config_file_location)
            stdout, stderr, ret_path = vm.RemoteCommandWithReturnCode('{}'.format(cmd), ignore_failure=True)
            # following is not working due to a known bug with post processing. EMON team working on fix, 8/20/2020
            # cmd = "sudo sed -i 's/^#RUBY_OPTIONS/RUBY_OPTIONS/g' {}/{}".format(EMON_INSTALL_DIR, edp_config_file_location)
            # stdout, stderr, ret_opti = vm.RemoteCommandWithReturnCode('{}'.format(cmd), ignore_failure=True)
            # if ret_path == 0 and ret_opti == 0:
            #   jruby_install_succeed = True
            if ret_path == 0:
              jruby_install_succeed = True

            break

      if not jruby_install_succeed:
        logging.info("Attempt to install ruby")
        vm.InstallPackages('ruby')

    script_start_post_process_emon = posixpath.join(INSTALL_DIR, 'start_post_process_emon.sh')
    logging.info("Running EMON post processing script_start_post_process_emon ({}) ..."
                 .format(script_start_post_process_emon))
    stdout, stderr, retcode = vm.RemoteCommandWithReturnCode("bash {}"
                                                             .format(script_start_post_process_emon), ignore_failure=False)
    if FLAGS.emon_debug:
      if stdout != '' or stderr != '':
        logging.info("Running script ({}) generated stdout ({}) and stderr ({})"
                     .format(script_start_post_process_emon, stdout, stderr))


def FetchResults(vm):
  """Copies emon data to PKB host."""
  logging.info('Fetching emon results')

  # TODO: tag vm with machine catogory, such as server, client, single_machine
  # if vm.tag is not None and vm.tag is not '':
  #  local_dir = os.path.join(vm_util.GetTempDir(), vm.name + '-' + vm.tag + '-emon')
  #  e.g.: pkb-5c37bc7a-0-client-emon
  #  e.g.: pkb-5c37bc7a-1-server-emon
  # else:
  local_dir = os.path.join(vm_util.GetTempDir(), vm.name + '-emon')
  # e.g.: pkb-5c37bc7a-0-emon
  cmd = ['mkdir', '-p', local_dir]
  vm_util.IssueCommand(cmd)

  remote_emon_output_files = '*emon*'
  if not FLAGS.emon_post_process_skip:
    remote_edp_output_files = '*edp*.csv'
    # tar command below will cause an exception if edp fails to generate the output files as expected,
    # and PKB process will be shutdown by the framework
    # this is desired if edp post process fails, which could be due to multiple reasons,
    # such as EMON data corruption, and we should quit
  else:
    remote_edp_output_files = ''

  remote_output_tarfile = os.path.join("/tmp", EMON_RESULT_TARBALL)
  vm.RemoteCommand('cd {} && sudo -E tar cvzf {} {} {}'
                   .format(INSTALL_DIR, remote_output_tarfile, remote_emon_output_files, remote_edp_output_files))
  vm.PullFile(local_dir, remote_output_tarfile)
  cmd = ['tar',
         '-xzvf',
         posixpath.join(local_dir, EMON_RESULT_TARBALL),
         '-C',
         local_dir]
  vm_util.IssueCommand(cmd)


def YumInstall(vm):
  kernel_ver = _GetKernelDevelVerYum(vm)
  kernel_src_dir = "--kernel-src-dir=/usr/src/kernels/%s" % kernel_ver
  vm.InstallPackageGroup('Development Tools')
  vm.InstallPackages(' '.join(RHEL_PKGS))
  _Install(vm, kernel_src_dir)


def AptInstall(vm):
  vm.InstallPackages(' '.join(UBUNTU_PKGS))
  # since we always install the exact matching kernel headers by UBUNTU_PKGS
  # there is no need to search for it like in YUM based kernel
  _Install(vm)
