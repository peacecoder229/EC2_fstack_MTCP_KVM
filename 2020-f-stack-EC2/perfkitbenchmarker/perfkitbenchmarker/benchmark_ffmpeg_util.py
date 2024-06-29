# Copyright 2020 PerfKitBenchmarker Authors. All rights reserved.
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

"""Implementation of the FFMPEG benchmark"""

import datetime
import logging
import os
import posixpath
import re
import time
import yaml

from perfkitbenchmarker import configs
from perfkitbenchmarker import data
from perfkitbenchmarker import errors
from perfkitbenchmarker import events
from absl import flags
from perfkitbenchmarker import sample
from perfkitbenchmarker import vm_util

from perfkitbenchmarker.traces import IsAnyTraceEnabled
from perfkitbenchmarker.traces import emon
from perfkitbenchmarker.linux_packages import INSTALL_DIR

FLAGS = flags.FLAGS

VIDEO_CODEC_DELIMITER = "//_"
VIDEO_RESULT_SUB_DIR = 'video_output_dir'


class SystemUnderTest:
  def __init__(self, vm):

    self.vm = vm
    self.ramdisk_root = "/mnt/ramdisk"

    cmd_output, _ = vm.RemoteCommand("uname -m")
    self.machine_name = cmd_output.rstrip(os.linesep)

    cmd_output, _ = vm.RemoteCommand("uname -r")
    self.kernel_version = cmd_output.rstrip(os.linesep)

    self.cpu_model = vm.CheckLsCpu().data.get('Model name', None)
    self.numa_node_count = vm.CheckLsCpu().numa_node_count

  def IsArm64Target(self):
    return self.machine_name == 'aarch64'

  def GetNumaNodeCount(self):
    return self.numa_node_count

  def GetRamDiskPath(self):
    return self.ramdisk_root

  def MountRamDisk(self):
    mount_flag, _ = self.vm.RemoteCommand('mount|grep -q "{}" && echo "True" || echo "False"'.format(self.ramdisk_root))
    if mount_flag.startswith('True'):
      self.vm.RemoteCommand("sudo rm -rf {}/*".format(self.ramdisk_root))
      self.vm.RemoteCommand("sudo umount -l {}".format(self.ramdisk_root))
    self.vm.RemoteCommand("sudo mkdir {}".format(self.ramdisk_root))
    self.vm.RemoteCommand("sudo mount -t tmpfs -o size=15G tmpfs {}".format(self.ramdisk_root))

  def UnmountRamDisk(self):
    mount_flag, _ = self.vm.RemoteCommand('mount|grep -q "{}" && echo "True" || echo "False"'.format(self.ramdisk_root))
    if mount_flag.startswith('True'):
      self.vm.RemoteCommand("sudo rm -rf {}/*".format(self.ramdisk_root))
      self.vm.RemoteCommand("sudo umount -l {}".format(self.ramdisk_root))
    self.vm.RemoteCommand("sudo rmdir {}".format(self.ramdisk_root))

  def CopyFileToRamDisk(self, filename):
    self.vm.RemoteCommand('sudo cp {} {}/'.format(filename, self.ramdisk_root))

  def DeleteFileFromRamDisk(self, filename):
    self.vm.RemoteCommand('sudo rm {}/{}'.format(self.ramdisk_root, filename))


class PerformanceData:
  def __init__(self, sut, vm):
    self.sut = sut
    self.vm = vm

    # Regular expressions for retrieving metrics from output log files
    self.regex_sar_pct_mem_used = re.compile(r'\d{2}:\d{2}:\d{2}\s+[AP]M\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+.\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+.\d+)\s+(\d+)\s+(\d+)\s+(\d+)')
    self.regex_sar_avg_cpu = re.compile(r'Average:\s+[a-z]+\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)')
    self.regex_sar_avg_cpu_mhz = re.compile(r'Average:\s+[a-z]+\s+(\d+\.\d+)')
    self.regex_dstat_disk_metrics = re.compile(r'^[\d\.]+,[\d\.]')

  def GetMemoryUtilization(self, sar_output):
    """Get the memory used counter value from SAR output"""
    max_pct_mem_used = 0.0
    lines = []
    console_output = self.sut.vm.RemoteCommand("cat {}".format(sar_output), ignore_failure=True)

    for line in console_output:
      lines.extend(line.splitlines())

    for line in lines:
      result = self.regex_sar_pct_mem_used.search(line)
      if result:
        mem_used = float(result.group(3))
        if mem_used > max_pct_mem_used:
          max_pct_mem_used = mem_used

    logging.info("max_pct_mem_used = {}".format(max_pct_mem_used))
    return max_pct_mem_used

  def GetAverageCpuUtilization(self, sar_cpu_output):
    """Get the average CPU usage counter value from SAR output"""
    cpu_usage = 0.0
    lines = []
    console_output = self.vm.RemoteCommand("cat {} | grep Average".format(sar_cpu_output), ignore_failure=True)

    for line in console_output:
      lines.extend(line.splitlines())

    for line in lines:
      result = self.regex_sar_avg_cpu.search(line)
      if result:
        user_cpu = float(result.group(1))
        nice_cpu = float(result.group(2))
        cpu_usage = user_cpu + nice_cpu

    logging.info("CPU Usage = {:.2f}".format(cpu_usage))
    return round(cpu_usage, 2)

  def GetAverageCpuFrequency(self, sar_cpu_mhz_output):
    """Get the average CPU frequency counter value from SAR output"""
    cpu_mhz = 0.0

    # On ARM64 platforms, the sar utility (sar -m CPU) does not work correctly
    # when getting cpu frequency. In some cases there is no output at all and
    # in other cases there is incorrect output and no summary
    if not self.sut.IsArm64Target():
      lines = []
      console_output = self.vm.RemoteCommand("cat {} | grep Average".format(sar_cpu_mhz_output), ignore_failure=True)

      for line in console_output:
        lines.extend(line.splitlines())

      for line in lines:
        result = self.regex_sar_avg_cpu_mhz.search(line)
        if result:
          cpu_mhz = float(result.group(1))

    logging.info("CPU MHz = {:.2f}".format(cpu_mhz))
    return cpu_mhz

  def GetDiskMetrics(self, dstat_output):
    """Get disk metrics from dstat output"""
    sum_active_read_bytes = 0
    sum_active_write_bytes = 0
    active_read_count = 0
    active_write_count = 0
    lines = []
    console_output = self.vm.RemoteCommand("cat {}".format(dstat_output))

    for line in console_output:
      lines.extend(line.splitlines())

    for line in lines:
      result = self.regex_dstat_disk_metrics.search(line)
      if result:
        active_read = float((line.split(','))[6])
        active_write = float((line.split(','))[7])

        if active_read > 0:
          sum_active_read_bytes += active_read
          active_read_count += 1

        if active_write > 0:
          sum_active_write_bytes += active_write
          active_write_count += 1

    if active_read_count > 0:
      avg_active_read_bytes = sum_active_read_bytes / active_read_count
    else:
      avg_active_read_bytes = 0

    if active_write_count > 0:
      avg_active_write_bytes = sum_active_write_bytes / active_write_count
    else:
      avg_active_write_bytes = 0

    logging.info("avg_active_read_bytes = {}".format(avg_active_read_bytes))
    logging.info("avg_active_write_bytes = {}".format(avg_active_write_bytes))

    return (avg_active_read_bytes, avg_active_write_bytes)


class FfmpegWorkload:

  @staticmethod
  def GetConfig(user_config, benchmark_name, benchmark_config):
    return configs.LoadConfig(benchmark_config, user_config, benchmark_name)

  @staticmethod
  def GetUsage():
    config_file = data.ResourcePath("ffmpeg/" + FLAGS.ffmpeg_config_file)

    with open(config_file) as file:
      config = yaml.load(file, Loader=yaml.SafeLoader)

      # Get this module's name (search using the basename of the current file)
      regex_module_name = re.compile(os.path.splitext(os.path.basename(__file__))[0])

      # Display the module's flags
      modules = FLAGS.flags_by_module_dict()
      for module_name in modules:
        if regex_module_name.search(module_name):
          logging.info("FFMPEG benchmark flags:")
          flaghelp = FLAGS.module_help(module_name)

          # Skip the first line of the flags description, which is the fully-qualified
          # benchmark name, and just show the flags
          strs = flaghelp[flaghelp.find(':') + 2:].split('\n')
          for str in strs:
            logging.info(str)

          # There will only be one match for this module name, so break the for loop
          break

      logging.info("FFMPEG benchmark description file:")
      logging.info("  \'{}\'".format(config_file))

      logging.info("Available FFMPEG benchmark tests:")
      for test in sorted(config.keys()):
        logging.info("  {:<35} # {}".format(test, config[test]['description']))

  def __init__(self, benchmark_spec):

    # Save off the benchmark_spec and vm to use
    self.benchmark_spec = benchmark_spec
    self.vm = benchmark_spec.vms[0]

    self.encoders = set()

    # Directory on the SUT where the video files will be downloaded and prepared
    self.work_directory = INSTALL_DIR
    self.video_files_dir = posixpath.join(self.work_directory, 'videos')

    # Directory on the host where there are cached video files (already prepared)
    self.video_cache_dir = FLAGS.ffmpeg_videos_dir
    self.use_cached_videos = self.video_cache_dir != ''

    # Keep track of the success rate for this run
    self.num_tests_run = 0
    self.num_tests_passed = 0

    # The default threshold used when running LIVE mode
    self.default_fps_threshold = 60

    # By default we are doing autoscaling. The initial instance count is initialized
    # here, but is set later when we read the YAML file to determine if the user is
    # overriding the autoscaling by specifying a specific number of instances.
    self.auto_scaling = True
    self.initial_instance_count = 0

    # The directories in which results are stored. After Provision and Prepare,
    # there is an output directory all_results_dir that holds the results for
    # each run. There can be multiple, separate, runs here, each of which has
    # its own directory, which includes the current date/time in the name
    self.all_results_dir = posixpath.join(self.work_directory, 'results')
    self.run_date_time = time.strftime("%F_%T")
    self.run_results_dir = "{}/{}_{}".format(self.all_results_dir, 'results', self.run_date_time)
    self.run_csv_filename = self.run_results_dir + "/results.csv"

    # Read the list of available input videos
    self.available_videos = []
    self.input_videos_file = data.ResourcePath("ffmpeg/input_videos.yaml")
    self.ReadInputVideoFile()

    # Read the YAML configuration file into the self.config dictionary. ReadConfig also
    # populates a list of video files, referenced_videos, that are actually referenced
    # by the tests requested by the user. Later, we'll download and transcode only the
    # files that we actually need
    self.referenced_videos = []
    self.config = {}
    self.config_file = data.ResourcePath("ffmpeg/" + FLAGS.ffmpeg_config_file)
    self.ReadConfigFile()

    # Some generic functionality is factored out into the SystemUnderTest class
    self.sut = SystemUnderTest(self.vm)

    # Some performance data collection during the run(s)
    self.perf_data = PerformanceData(self.sut, self.vm)

    # Whether NUMA control has been enabled
    self.numactl_flag = FLAGS.ffmpeg_enable_numactl

    # Whether we're directly accessing the encoder binaries (or going through ffmpeg)
    self.direct = False

    # Allow the FFMPEG benchmark to control the trace collectors. This is so we
    # can enable trace collection for only the last run. Once we find the right
    # number of iterations to use, the iteration is run again will the trace
    # collectors enabled
    self.benchmark_spec.control_traces = True

  def ReadConfigFile(self):
    """Populate the config dictionary from the YAML configuration file
       and build a list of available input videos"""

    # Parse the YAML file into the self.config dictionary
    with open(self.config_file) as file:
      self.config = yaml.load(file, Loader=yaml.SafeLoader)

    # Create a list of the videos that are referenced by the requested tests.
    # These videos will be processed to specific video formats later, during
    # the Prepare phase.
    for test in self.GetTargets(FLAGS.ffmpeg_run_tests.split(',')):
      if 'input_files' in self.config[test].keys():
        for video in (self.config[test]['input_files']).split():
          try:
            # Each entry in the input video files list is a string that has both the input video
            # filename and the code name, separated by the VIDEO_CODEC_DELIMITER. We should change
            # this to use a more legit data structure
            encoded_name = video + VIDEO_CODEC_DELIMITER + self.config[test]['video_codec']['codec']
            self.encoders.add(self.config[test]['video_codec']['codec'])
            if encoded_name not in self.referenced_videos:
              self.referenced_videos.append(encoded_name)
          except KeyError:
            logging.error('The \'{}\' entry in {} is invalid'.format(test, self.config_file))

  def ReadInputVideoFile(self):
    with open(self.input_videos_file) as file:
      config = yaml.load(file, Loader=yaml.SafeLoader)
      self.available_videos = config['input_videos']

  def CreateResultsDirectoryForRun(self):
    self.vm.RemoteCommand('mkdir -p {}'.format(self.run_results_dir))

  def RemoveAllResults(self):
    self.vm.RemoteCommand('sudo rm -rf {}/*'.format(self.all_results_dir))

  def Prepare(self):
    """Prepares the system for ffmpeg benchmark"""
    self.benchmark_spec.always_call_cleanup = True
    self.sut.MountRamDisk()
    self.PrepareEncoder()

    # If we're using cached videos, they will be copied to the SUT during the Run
    # phase. Only the files actually used will be copied
    if not self.use_cached_videos:
      self.PrepareVideos()

  def _Uninstall(self):
    cleanup_cmds = [
        'sudo rm -rf ~/ffmpeg_sources',
        'sudo rm -rf ~/bin',
        'sudo rm -rf ~/ffmpeg_build',
        'sudo rm -rf ~/*.mp4',
    ]
    self.vm.RemoteCommand(' && '.join(cleanup_cmds))
    for encoder in self.encoders:
      self.vm.Uninstall(self.CodecToPackage(encoder))

  def Cleanup(self):
    """Perform cleanup operation for the run"""
    self._Uninstall()
    self.sut.UnmountRamDisk()
    self.RemoveAllResults()

  def InitializeOutputCSVFile(self):
    cmd_output, _ = self.vm.RemoteCommand('LD_LIBRARY_PATH=/usr/local/lib:$HOME/ffmpeg_build/lib $HOME/bin/ffmpeg -version | grep "ffmpeg version"')
    ffmpeg_version = cmd_output.split(' ')[2]
    file_header = 'FFMPEG Benchmark Results\n'
    file_header += 'Run date/time,{}\n\n'.format(self.run_date_time)
    file_header += '{:14s},="{}"\n'.format('FFMPEG version', ffmpeg_version)
    file_header += '{:14s},="{}"\n'.format('Kernel version', self.sut.kernel_version)
    file_header += '{:14s},="{}"\n'.format('OS version', self.vm.GetOsInfo())
    file_header += '{:14s},="{}"\n'.format('CPU model', self.sut.cpu_model)
    file_header += '{:14s},="{}"\n'.format('Config file', self.config_file)
    file_header += '{:14s},="{}"\n'.format('Results dir', self.run_results_dir)
    file_header += '{:14s},="{}"\n'.format('Video dir', self.video_files_dir)
    file_header += '\ncodec,input_format,output_mode,n,preset,video_file,#transcodes,lowest_fps,'
    file_header += 'list_of_fps,average_cpu,average_bzy_mhz,max_pct_memused,active_read_(bytes),'
    file_header += 'active_write_(bytes),ffmpeg_args'
    self.vm.RemoteCommand('echo '"'{}'"' > {}'.format(file_header, self.run_csv_filename))

  def Run(self):
    """Runs the ffmpeg benchmark"""

    # It is possible to invoke Run multiple times (--run_state=Run). Each run will have
    # a different timestamp, so the results will automatically be in a different results
    # directory. Let's create this output directory and initialize the output CSV file.
    self.CreateResultsDirectoryForRun()
    self.InitializeOutputCSVFile()

    # Get the list of targets (tests to be invoked) that the user has specified
    targets = self.GetTargets(FLAGS.ffmpeg_run_tests.split(','))
    logging.info('targets: {}'.format(str(targets)))

    # Initialize an empty list of samples. This list will be populated by each test in the
    # run. In addition, a couple summary samples will be appended after the run.
    samples = []

    # Keep track of how long the overall run takes
    start_time = datetime.datetime.now()

    # For each test in the target list, get the parameters of the test from the
    # YAML-derived configuration and execute the test
    for test in sorted(targets):
      try:
        # These values are required for every test target
        codec = self.config[test]['video_codec']['codec']
        input_format = self.config[test]['input_format']
        video_files = self.config[test]['input_files'].split()

        full_output_mode = self.config[test]['output_mode']['type']
        output_mode, test_mode = full_output_mode.split('/', 2)

        # The user can specify a number of instances to use, which disables autoscaling. When
        # this value is is specified, the workload makes only one pass. The use of this option
        # in the YAML file applies to both LIVE and VOD modes
        if 'num_instances' in self.config[test].keys():
          self.auto_scaling = False
          self.initial_instance_count = self.config[test]['num_instances']
        else:
          if test_mode == 'VOD':
            # For VOD mode, the instance count starts at 1 and increments by 1 each time
            self.initial_instance_count = 1
          elif test_mode == 'LIVE':
            # For LIVE mode, the instance count starts at 8 and the next instance count
            # is computed based on the results of the previous run
            self.initial_instance_count = 2
          else:
            logging.error("Invalid test_mode specified")

        # The FPS threshold is optional. If not provided, the default will be used
        if 'fps_threshold' in self.config[test]['output_mode'].keys():
          fps_threshold = self.config[test]['output_mode']['fps_threshold']
        else:
          fps_threshold = self.default_fps_threshold

        # Optional variable that specifies whether to run the encoder/decoder directly
        if 'direct' in self.config[test]['video_codec']:
          self.direct = self.config[test]['video_codec']['direct']

        # There are no presets for VP9 or when using direct mode
        preset = ''
        if 'preset' in self.config[test]['video_codec']:
          preset = self.config[test]['video_codec']['preset']

        # The codec preset tuning parameter is also optional and not used in direct mode
        tune = ''
        if 'tune' in self.config[test]['video_codec']:
          tune = self.TuneToOption(self.config[test]['video_codec']['tune'])

        # Normal FFMPEG invocation includes the codec and any presets and preset tuning parameters,
        # while direct invocation only uses the rest of the command line ('args') from the YAML file. So,
        # if we're not in direct mode create the command-line parameters for the codec/preset/tune options
        # However, there is an exception: If in 1:n output mode, these options go with the command lines
        # for the separate output sections so we don't need to do anything here
        args = ''
        if not self.direct:
          # However, if we're using 1:n mode then the codec and preset options are provided later
          # with each of the outputs instead of here, which is at the beginning of the command line
          if output_mode != '1:n':
            # Convert the specifiec codec to a command-line option
            args = "{} ".format(self.CodecToOption(codec))

            if preset:
              # Convert the specified preset to a command-line option
              args += "{} ".format(self.PresetToOption(codec, preset))
              if tune:
                args += "{} ".format(tune)

        # Add the rest of the command line from 'args' section in the YAML file
        if output_mode == '1:n':
          ffmpeg_args = self.config[test]['video_codec']['args']
          ffmpeg_args = ffmpeg_args.replace("${codec}", self.CodecToOption(codec))
          ffmpeg_args = ffmpeg_args.replace("${preset}", self.PresetToOption(codec, preset))
          args = ffmpeg_args
        else:
          args += self.config[test]['video_codec']['args']

      except KeyError:
        logging.error('The \'{}\' entry in {} is invalid'.format(test, self.config_file))

      for video_file in video_files:
        # If we're accessing the codec binaries directly rather than through the ffmpeg front-end,
        # then we use the raw (y4m) video files rather than the prepared versions (mp4)
        video_file_basename = video_file.split('.')[0]
        if self.direct:
          video_filename = video_file_basename + '.y4m'
        else:
          video_filename = video_file_basename + '_' + codec + '.mp4'

        ramdisk_path = self.sut.GetRamDiskPath()

        # The video files will either be cached on the host, or in the video_files_dir on the SUT.
        # For either case, the required input file will be copied to the RAM disk
        if self.use_cached_videos:
          source_filename = "{}/{}".format(self.video_cache_dir, video_filename)
          dest_filename = "{}/{}".format(ramdisk_path, video_filename)
          already_copied, _ = self.vm.RemoteCommand('cd {} && test -f  {} && echo "True" || echo "False"'.format(ramdisk_path, video_filename))
          if already_copied.startswith('False'):
            self.vm.PushFile(source_filename, dest_filename)
        else:
          self.sut.CopyFileToRamDisk("{}/{}".format(self.video_files_dir, video_filename))

        self.RunMulti(test, args, ramdisk_path, video_filename, codec, input_format, full_output_mode, preset, fps_threshold, samples)
        self.sut.DeleteFileFromRamDisk(video_filename)

    # Add a summary sample that provides the overall success rate (% tests meeting SLA)
    summary_metadata = {}
    summary_metadata['num_tests_run'] = self.num_tests_run
    summary_metadata['num_tests_passed'] = self.num_tests_passed
    success_percentage = int((self.num_tests_passed / self.num_tests_run) * 100)
    samples.append(sample.Sample('% of tests meeting SLA', success_percentage, '%', metadata=summary_metadata))

    # Add the total run-time for this iteration to the CSV file and transfer it from the SUT to the host
    end_time = datetime.datetime.now()
    diff_datetime = end_time - start_time
    self.vm.RemoteCommand('echo '"'\nTotal Runtime: {}'"' >> {}'.format(diff_datetime, self.run_csv_filename))

    # Add the run_uri to the results file as we pull it to the host so that we don't overwrite previous runs
    host_results_file_name = "{}/results_{}.csv".format(os.getcwd(), FLAGS.run_uri)
    self.vm.PullFile(host_results_file_name, self.run_csv_filename)

    # Download all of the output from the run from the SUT to the host
    self.DownloadResults()

    # Return the samples generated by the tests
    return samples

  def PrepareVideos(self):
    """Download and extract video files"""

    def DownloadAndExtract(video):
      logging.info("start value is {}".format(video))
      substrs = video.split(VIDEO_CODEC_DELIMITER)
      video_name = substrs[0].split('.')[0]
      codec_name = substrs[1]

      for video_info in self.available_videos:
        if 'filename' in video_info:
          if video_name.lower() == video_info['filename'].lower():
            logging.info("video filename is {}.y4m".format(video_name.lower()))
            video_exists, _ = self.vm.RemoteCommand(
                'cd {} && test -f  {}.y4m && echo "True" || echo "False"'.format
                (self.video_files_dir, video_name))
            logging.info("video_exists is {}".format(video_exists))
            if video_exists.startswith('False'):
              retries = 3
              while True:
                try:
                  self.vm.RemoteCommand("cd {} && wget -q --no-check-certificate {}"
                                        .format(self.video_files_dir, video_info['url']))
                  break
                except errors.VirtualMachine.RemoteCommandError as e:
                  retries -= 1
                  if retries == 0:
                    raise e
                  logging.warning("failed to download video from {}, retrying...".format(video_info['url']))

            # 'veryslow' isn't a preset option for SVT-HEVC
            if codec_name == 'SVT-HEVC':
              preset = '3'
            else:
              preset = 'veryslow'

            ffmpeg_cmd = "export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:~/ffmpeg_build/lib && "
            ffmpeg_cmd += "~/bin/ffmpeg -stream_loop 6 -i "
            ffmpeg_cmd += "{}/{}.y4m ".format(self.video_files_dir, video_info['filename'])
            ffmpeg_cmd += "{} {} ".format(self.CodecToOption(codec_name), self.PresetToOption(codec_name, preset))
            ffmpeg_cmd += "-b:v {} {}/".format(video_info['bitrate'], self.video_files_dir)
            ffmpeg_cmd += "/{}_{}.mp4".format(video_info['filename'], codec_name)

            self.vm.RemoteCommand(ffmpeg_cmd)

    # Before downloading or copying the input videos, clear out the destination directory
    self.vm.RemoteCommand('rm -rf {} && mkdir {}'.format(self.video_files_dir, self.video_files_dir))

    # Make sure we have the utilities that we need to download and extract
    self.vm.Install('wget')
    self.vm.Install('7zip')

    vm_util.RunThreaded(DownloadAndExtract, self.referenced_videos)

  def PrepareEncoder(self):
    self._Uninstall()
    self.vm.RemoteCommand('mkdir -p ~/ffmpeg_sources ~/ffmpeg_build/include ~/ffmpeg_build/lib/pkgconfig ~/bin')

    ffmpeg_download_cmds = [
        'cd ~/ffmpeg_sources',
        'git clone https://github.com/spawlows/FFmpeg.git -b task-filter-mt-prototype ffmpeg',
        'cd ffmpeg', 'sed -i \'2416s/return;/return NULL;/\' fftools/ffmpeg.c'
    ]

    ffmpeg_build_cmds = [
        'export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib',
        'export PKG_CONFIG_PATH=$PKG_CONFIG_PATH:~/ffmpeg_build/lib/pkgconfig:/usr/local/lib',
        'cd ~/ffmpeg_sources/ffmpeg'
    ]

    ffmpeg_configure_cmd = [
        'PATH="$HOME/bin:$PATH"',
        'PKG_CONFIG_PATH="$HOME/ffmpeg_build/lib/pkgconfig"',
        './configure',
        '--prefix="$HOME/ffmpeg_build"',
        '--pkg-config-flags="--static" --extra-cflags="-I$HOME/ffmpeg_build/include"',
        '--extra-ldflags="-L$HOME/ffmpeg_build/lib"',
        '--extra-libs="-lpthread -lm"',
        '--bindir="$HOME/bin"',
        '--enable-gpl',
        '--enable-libass',
    ]

    if 'x264' in self.encoders:
      logging.info('Installing x264')
      self.vm.Install('x264')
      ffmpeg_configure_cmd.append('--enable-libx264')

    if 'x265' in self.encoders:
      logging.info('Installing x265')
      self.vm.Install('x265')
      ffmpeg_configure_cmd.append('--enable-libx265')

    if 'vpx-vp9' in self.encoders:
      logging.info('Installing vp9')
      self.vm.Install('vp9')
      ffmpeg_configure_cmd.append('--enable-libvpx')

    # The SVT-HEVC codec will not compile on ARM since it has Intel-specific intrinsics
    if not self.sut.IsArm64Target() and 'SVT-HEVC' in self.encoders:
      logging.info('Installing svt')
      self.vm.Install('svt')
      ffmpeg_configure_cmd.append('--enable-libsvthevc')
      ffmpeg_download_cmds.extend(['cd ~/ffmpeg_sources/ffmpeg', 'git apply {}/encoders/SVT-HEVC/ffmpeg_plugin/*.patch'.format(INSTALL_DIR)])


    logging.info('Downloading and patching ffmpeg')
    self.vm.RemoteCommand(' && '.join(ffmpeg_download_cmds))

    logging.info('Configuring and building ffmpeg')
    ffmpeg_configure_cmd = ' '.join(ffmpeg_configure_cmd)
    ffmpeg_cmds = ffmpeg_build_cmds + [ffmpeg_configure_cmd] + ['PATH="$HOME/bin:$PATH" make -j', 'make install']

    self.vm.RemoteCommand(' && '.join(ffmpeg_cmds))


  def DownloadResults(self):
    """Archive and download the result directory"""
    archive = 'results_dir.tar.gz'
    self.vm.RemoteCommand('tar -czf {} {}/'.format(archive, self.run_results_dir))
    self.vm.PullFile(vm_util.GetTempDir(), archive)

  def CodecToPackage(self, codec):
    switcher = {
        "SVT-HEVC": "svt",
        "x265": "x265",
        "x264": "x264",
        "vpx-vp9": "vp9",
    }
    return switcher.get(codec, "nothing")

  def CodecToOption(self, codec):
    switcher = {
        "SVT-HEVC": "-c:v libsvt_hevc",
        "x265": "-c:v libx265",
        "x264": "-c:v libx264",
        "vpx-vp9": "-c:v libvpx-vp9",
    }
    return switcher.get(codec, "nothing")

  def CodecToExecutableName(self, codec):
    switcher = {
        'SVT-HEVC': '$HOME/ffmpeg_build/lib/SvtHevcEncApp',
        'x265': '$HOME/ffmpeg_build/bin/x265',
        'x264': '$HOME/bin/x264',
        'vpx-vp9': '$HOME/ffmpeg_build/bin/vpxenc'
    }
    if self.direct:
      return switcher.get(codec, "nothing")
    return '$HOME/bin/ffmpeg'

  def PresetToOption(self, codec, preset):
    # The vp9 codec doesn't have any presets
    if codec == 'vpx-vp9':
      return ''
    return '-preset ' + str(preset)

  def TuneToOption(self, tune):
    return '-tune ' + str(tune)

  # Recursively gather all of the targets to run, avoiding any duplicates
  def GetTargets(self, initial_target_list):
    full_target_list = []

    for target in initial_target_list:
      if target not in self.config.keys():
        raise Exception('ERROR: The test \"{}\" is not present in the test configuration file'.format(target))
      elif 'group' in self.config[target].keys():
        for t1 in self.config[target]['group'].split():
          for sub_target in self.GetTargets([t1]):
            if sub_target not in full_target_list:
              full_target_list.append(sub_target)
      else:
        if target not in full_target_list:
          full_target_list.append(target)

    return full_target_list

  def GetNumberOfOutputFiles(self, ffmpeg_args):
    """Get the number of output files"""
    return ffmpeg_args.count('-c:v')

  def RunMulti(self, sub_test_name, ffmpeg_args, video_path, video_file, codec, input_format, full_output_mode, preset, fps_threshold, samples):
    """Create and run the ffmpeg workload bash script on the SUT"""
    logging.info('Running test: \"{}\" with video file: \"{}\"'.format(sub_test_name, video_file))

    # Create the output directory on the SUT for the results
    test_results_dir = posixpath.join(self.run_results_dir, codec, input_format, full_output_mode, str(preset), video_file)
    logging.info('result dir {}'.format(test_results_dir))
    a_output = 'ffmpeg.out_'
    self.vm.RemoteCommand('mkdir -p {}'.format(test_results_dir))

    # Initialize some key counters
    total_fps = prev_total_fps = avg_cpu_utilization = lowest_fps = 0

    # Split the output mode and test mode from the combined output/test mode
    output_mode, test_mode = full_output_mode.split('/', 2)

    # Build the command line
    arg_array = [self.CodecToExecutableName(codec)]
    if self.direct:
      arg_array.extend([ffmpeg_args, posixpath.join(video_path, video_file)])
    else:
      arg_array.extend(['-y', '-i', posixpath.join(video_path, video_file), ffmpeg_args])
    ffmpeg_cmd_line = ' '.join(arg_array)

    def CreateRunScript(num_inst, with_traces=False):
      script = '#!/bin/bash\n'

      # Create the output directory for this iteration
      suffix = "_w_traces" if with_traces else ""
      script += 'cd {} && mkdir -p {}_instance{}\n'.format(test_results_dir, num_inst, suffix)
      script += 'declare -A ffmpeg_wait_pids\n'
      script += 'export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$HOME/ffmpeg_build/lib\n'

      # Launch perf monitoring commands only if we're not doing the run with trace collectors enabled
      if not with_traces:
        script += 'pkill sar\npkill dstat\n'
        script += 'declare -A perf_wait_pids\n'
        script += 'sar -r 1 > {} 2>/dev/null &\n'.format(sar_output)
        script += 'perf_wait_pids[0]=$!\n'
        if test_mode == 'VOD':
          script += '(sleep 10; sar -u 2 30 > {}) 2>/dev/null &\n'.format(sar_cpu_output)
          script += '(sleep 10; sar -m CPU 2 30 > {}) 2>/dev/null &\n'.format(sar_cpu_mhz_output)
        else:
          script += '(sleep 10; sar -u 2 30 > {}) 2>/dev/null &\n'.format(sar_cpu_output)
          script += '(sleep 10; sar -m CPU 2 30 > {}) 2>/dev/null &\n'.format(sar_cpu_mhz_output)
        script += 'dstat --output {} >/dev/null 2>/dev/null &\n'.format(dstat_output)
        script += 'perf_wait_pids[1]=$!\n'

      # Launch the ffmpeg processes
      for i in range(num_inst):
        # cd to per instance dir, so it's guaranteed that there won't be
        # an existing output file. When an output file exists, ffmpeg
        # will prompt you to overwrite or not in interactive session.
        # but fails when ffmpeg is run via subprocess, bash combination.
        # Directory for output file is created so that it can be torn down later.
        save_results_dir = '{}/{}_instance{}'.format(test_results_dir, num_inst, suffix)
        video_output_dir = '{}/{}'.format(save_results_dir, VIDEO_RESULT_SUB_DIR)
        script += 'mkdir -p {}\n'.format(video_output_dir)
        script += 'cd {}\n'.format(video_output_dir)
        if self.numactl_flag:
          numa_node = i % self.sut.GetNumaNodeCount()
          script += 'numactl --membind={:d} --cpunodebind={:d} -- {} > {}/{}{:d} 2>&1 &\n' \
              .format(numa_node, numa_node, ffmpeg_cmd_line, save_results_dir, a_output, i + 1)
        script += '{} > {}/{}{} 2>&1 &\n'.format(ffmpeg_cmd_line, save_results_dir, a_output, i + 1)
        script += 'ffmpeg_wait_pids[{}]=$!\n'.format(i)

      # Wait for ffmpeg processes to complete
      script += 'sleep .5\n'
      script += 'ffmpeg_wait_pids[{:d}]=$!\n'.format(num_inst + 1)
      script += 'for pid in ${ffmpeg_wait_pids[*]}; do wait $pid; done\n'

      # Kill the monitoring processes
      if not with_traces:
        script += 'for pid in ${perf_wait_pids[*]}; do sudo kill -9 $pid; done\n'
        script += 'killall -s SIGINT sar || true\n'

      # Output the whole script to the log so that we have it available for potential debugging
      logging.debug('script commands:\n{}'.format(script))
      return (script, save_results_dir)

    # Initialize some tracking variables
    successful_samples = []
    instance_list = []

    if self.auto_scaling:
      # If we're autoscaling, the number of instances will be determined by doing successive runs. It is initialized
      # depending on whether we're doing LIVE or VOD mode
      num_inst = self.initial_instance_count if test_mode == 'LIVE' else 1
      max_instances_achieved = 0
    else:
      # If we're not autoscaling, we already know the optimum number of instances and so we can initialize
      # num_inst and the instance_list accordingly.
      # that we've already tried
      num_inst = self.initial_instance_count
      max_instances_achieved = num_inst

    # The main control loop to iteratively find the correct number of simultaneous instances
    while True:
      logging.info('Running {} instance(s) of ffmpeg with {},{},{},{},{}'
                   .format(num_inst, codec, input_format, output_mode, preset, video_file))

      # Compose the filenames for the various performance-related files
      instance_dir = posixpath.join(test_results_dir, "{}_instance".format(num_inst))
      dstat_output = posixpath.join(instance_dir, 'dstat.txt')
      sar_output = posixpath.join(instance_dir, 'sar-r.txt')
      sar_cpu_output = posixpath.join(instance_dir, 'sar-cpu.txt')
      sar_cpu_mhz_output = posixpath.join(instance_dir, 'sar-cpu-mhz.txt')

      # Create and execute the script
      (script, save_results_dir) = CreateRunScript(num_inst)
      self.vm.RemoteCommand('echo \'{}\' > ~/run_multi_ffmpeg1.sh'.format(script))
      if(self.vm.OS_TYPE == 'centos8' or self.vm.OS_TYPE == 'centos7'):
          self.vm.RemoteCommand('chmod +x ~/run_multi_ffmpeg1.sh && sudo HOME=$HOME ~/run_multi_ffmpeg1.sh')
      else:
          self.vm.RemoteCommand('chmod +x ~/run_multi_ffmpeg1.sh && sudo -E ~/run_multi_ffmpeg1.sh')

      # Clean up output video directory
      self.vm.RemoteCommand('sudo rm -r {}/{}'.format(save_results_dir, VIDEO_RESULT_SUB_DIR))

      # Check for errors in the output
      ffmpeg_output_file = '{}/{}'.format(save_results_dir, a_output)
      self.ScanLogfilesForErrors(codec, num_inst, ffmpeg_output_file)

      # Process performance stats
      avg_cpu_frequency = self.perf_data.GetAverageCpuFrequency(sar_cpu_mhz_output)
      avg_cpu_utilization = self.perf_data.GetAverageCpuUtilization(sar_cpu_output)
      max_pct_mem_used = self.perf_data.GetMemoryUtilization(sar_output)
      (avg_active_read_bytes, avg_active_write_bytes) = self.perf_data.GetDiskMetrics(dstat_output)

      # Get the FPS information from the output file
      (lowest_fps, all_last_fps, total_fps) = self.GetFpsInfoFromLogFile(codec, num_inst, ffmpeg_output_file)

      # Append the output data to the CSV file on the SUT
      num_output_files = self.GetNumberOfOutputFiles(ffmpeg_args) if output_mode == '1:n' else 1
      row = ('{},{},="{}",{},{},{},{},{},="{}",{:.2f},{:.2f},{},{:.2f},{:.2f},"-i {} {}"'
             .format(codec.strip(), input_format, output_mode, str(num_output_files),
                     preset, video_file, str(num_inst), str(lowest_fps), all_last_fps,
                     round(avg_cpu_utilization, 2), avg_cpu_frequency, str(max_pct_mem_used),
                     avg_active_read_bytes, avg_active_write_bytes, video_file, ffmpeg_args))
      self.vm.RemoteCommand('echo '"'{}'"' >> {}'.format(row, self.run_csv_filename))

      # Keep track of the instance numbers that we've used. This will be used to determine when
      # we're finished looping
      instance_list.append(num_inst)

      logging.debug("num_inst: {}".format(num_inst))
      logging.debug("lowest_fps: {}".format(lowest_fps))
      logging.debug("total_fps: {}".format(total_fps))
      logging.debug("fps_threshold: {}".format(fps_threshold))
      logging.debug("avg_cpu_utilization: {}".format(avg_cpu_utilization))
      logging.debug("all_last_fps: {}".format(all_last_fps))

      # Recalculate the number of instances based on the results of the previous run
      if test_mode == 'LIVE':
        # If we were successful, note the # of instances and save the sample
        if float(lowest_fps) >= float(fps_threshold):
          max_instances_achieved = num_inst
          logging.debug("Run succeeded, updated max_instances_achieved: {}".format(max_instances_achieved))
          self.GenerateSampleForRun(sub_test_name, num_inst, output_mode, test_mode, video_file, codec,
                                    avg_cpu_utilization, lowest_fps, fps_threshold, preset, total_fps, successful_samples)

        # Calculate the new number of instances based on the total FPS across all instances, divided by the FPS threshold to achieve
        if self.auto_scaling:
          new_num_inst = max(int(total_fps / float(fps_threshold)), 1)
          logging.debug("new_num_inst: {}".format(new_num_inst))

          # It may happen that we calculate the same number of instances as that which we just ran
          if num_inst == new_num_inst:
            # If so, if the run was successful, try one more instance (expecting to fail)
            if float(lowest_fps) >= float(fps_threshold):
              num_inst = num_inst + 1
            # Otherwise, if we failed this run, let's try one less (hoping to succeed)
            else:
              if num_inst > 1:
                num_inst = num_inst - 1
          else:
            num_inst = new_num_inst
      elif test_mode == 'VOD':
        # Continue as long as we're getting improvement in the total FPS
        logging.debug("total_fps: {}".format(total_fps))
        logging.debug("prev_total_fps: {}".format(prev_total_fps))
        if total_fps > prev_total_fps:
          max_instances_achieved = num_inst
          logging.debug("Run succeeded, updated max_instances_achieved: {}".format(max_instances_achieved))
          self.GenerateSampleForRun(sub_test_name, num_inst, output_mode, test_mode, video_file, codec,
                                    avg_cpu_utilization, lowest_fps, fps_threshold, preset, total_fps, successful_samples)

          if self.auto_scaling:
            num_inst = num_inst + 1
            prev_total_fps = total_fps

      logging.debug("num_inst after recalc: {}".format(num_inst))
      logging.debug("max_instances_achieved: {}".format(max_instances_achieved))

      if num_inst in instance_list:
        # If we had a successful run, append the sample for most recent successful pass. Otherwise, append the
        # sample for this run, which failed. If the user has specified a particular number of instances, it is
        # possible that this fails this time. So, make sure also that we indeed have some successful samples.
        if (max_instances_achieved != 0) and (len(successful_samples) > 0):
          # The samples list has the samples for all of the successful runs. Return only the most recent by appending
          # to the samples list that was provided to this method
          logging.debug("Appending the sample for the most recent successful run: max_instances_achieved: {}".format(max_instances_achieved))
          samples.append(successful_samples[-1])
        else:
          logging.debug("Appending the sample for this last (failed) run")
          logging.debug("max_instances_achieved: {}, num_inst: {}".format(max_instances_achieved, num_inst))
          self.GenerateSampleForRun(sub_test_name, num_inst, output_mode, test_mode, video_file, codec,
                                    avg_cpu_utilization, lowest_fps, fps_threshold, preset, total_fps, samples)

        logging.info('Breaking while, num_inst {:d}'.format(int(num_inst)))
        break

    # If we need to run any trace collectors, such as EMON, run with the max # of instances achieved.
    if max_instances_achieved != 0:

      if FLAGS.trace_allow_benchmark_control and IsAnyTraceEnabled():
        logging.info('Running {} instances again with trace collectors enabled'.format(int(max_instances_achieved)))

        # Create and enable the run script
        (script, _) = CreateRunScript(max_instances_achieved, with_traces=True)
        script_filename = 'run_with_collectors.sh'
        self.vm.RemoteCommand('echo \'{}\' > ~/{}'.format(script, script_filename))
        self.vm.RemoteCommand('chmod +x ~/{}'.format(script_filename))

        # Run the script with trace collection enabled
        events.start_trace.send(events.RUN_PHASE, benchmark_spec=self.benchmark_spec)
        self.vm.RemoteCommand('sudo -E ~/{}'.format(script_filename))
        events.stop_trace.send(events.RUN_PHASE, benchmark_spec=self.benchmark_spec)
        if emon.IsEnabled():
          self.PostProcessEmon(test_results_dir, max_instances_achieved)

  def GetFpsInfoFromLogFile(self, codec, num_inst, log_filename):
    last_fps_list = []

    for i in range(num_inst):
      instance_log_filename = "{}{:d}".format(log_filename, i + 1)
      logging.info("instance_log_filename: {}".format(instance_log_filename))

      # Grab the codec output log and scan it for the frame rate
      codec_output = self.vm.RemoteCommand("cat {}".format(instance_log_filename))
      fps = self.GetFps(codec, codec_output)
      last_fps_list.append(float(fps))

    lowest_fps = (sorted(last_fps_list))[0]
    all_last_fps = '/'.join([str(i) for i in last_fps_list])
    fps_sum = round(sum(last_fps_list), 4)

    logging.info("lowest_fps: {}".format(lowest_fps))
    logging.info("all_last_fps: {} ".format(all_last_fps))
    logging.info("fps_sum: {}".format(fps_sum))

    return (lowest_fps, all_last_fps, fps_sum)

  def GetFps(self, codec, codec_output):
    """Get the FPS value from the output log file for the run
       If there is only one entry, return it when we find it.
       Otherwise, return the last entry"""
    lines = []
    for line in codec_output:
      lines.extend(line.splitlines())

    fps = 0.0

    # If the codec is invoked directly, the output has a different format than
    # if the ffmpeg front-end is used. So, different regular expressions are required
    if self.direct:
      # Scan the x264 binary output (the only supported direct mode so far)
      re_fps = re.compile('encoded \d+ frames, ([0-9]+\.[0-9]+) fps')

      for line in lines:
        result = re_fps.search(line)
        if result:
          fps = float(result.group(1))
          break
    else:
      # Scan the FFMPEG front-end output
      re_speed = re.compile(r'speed=\s*([0-9]+\.[0-9]+)x')
      re_playback_fps = re.compile(r'Stream #0.*?(\d+)\sfps,.*?([0-9]+) tbn', re.DOTALL)

      speed = 0.0
      playback_fps = 0.0

      for line in lines:
        speed_result = re.search(re_speed, line)
        if speed_result:
          speed = float(speed_result.group(1))

      # There is only one occurance of the playback FPS, so the first one is taken
      playback_fps_result = re.search(re_playback_fps, str(codec_output))
      if playback_fps_result:
        playback_fps = float(playback_fps_result.group(1))

      fps = round(speed * playback_fps, 4)

      logging.debug("GetFps: speed: {}".format(speed))
      logging.debug("GetFps: playback_fps: {}".format(playback_fps))
      logging.debug("GetFps: fps: {}".format(fps))

    return fps

  def GetErrorRegexesForCodec(self, codec):
    if self.direct:
      # The x264 case
      regex_fatal_error = re.compile("TODO: Some x264 regex")
      regex_nonfatal_error = re.compile("TODO: Some x264 regex", re.IGNORECASE)
    else:
      # The FFMPEG case
      regex_fatal_error = re.compile("Invalid argument")
      regex_nonfatal_error = re.compile("error|invalid", re.IGNORECASE)

    return (regex_fatal_error, regex_nonfatal_error)

  def ScanLogfilesForErrors(self, codec, num_inst, codec_output_file):
    """Report error/invalid count"""
    (regex_fatal_error, regex_nonfatal_error) = self.GetErrorRegexesForCodec(codec)

    # Each instance has an output log to scan
    for i in range(num_inst):
      error_count = 0
      instance_output_filename = "{}{:d}".format(codec_output_file, i + 1)

      # Get the output log contents for this instance
      log_output = self.vm.RemoteCommand("cat {}".format(instance_output_filename))

      # Process each line to search for whether there were any invalid arguments
      # or any other errors
      for line in log_output:
        if regex_fatal_error.search(line):
          raise Exception("ERROR: Invalid argument found in logfile: {}".format(instance_output_filename))

        result = regex_nonfatal_error.search(line)
        if result:
          error_count += 1

      if error_count > 0:
        log_ref = logging.error
      else:
        log_ref = logging.info

      log_ref("ffmpeg.out_{:d}: error_count={:d}".format((i + 1), error_count))

  def GenerateSampleForRun(self, sub_test_name, num_inst, output_mode, test_mode, video_file, codec,
                           avg_cpu_utilization, lowest_fps, fps_threshold, preset, total_fps, samples):
    metadata = {}
    metadata['sub_test_name'] = sub_test_name
    metadata['codec'] = codec
    metadata['output_mode'] = output_mode
    metadata['test_mode'] = test_mode
    metadata['video_file'] = video_file
    metadata['preset'] = preset
    metadata['cpu_utilization'] = "{:.2f}".format(avg_cpu_utilization)
    metadata['lowest_fps'] = lowest_fps

    self.num_tests_run += 1

    if test_mode == 'VOD':
      self.num_tests_passed += 1
      metadata['transcodes'] = num_inst
      samples.append(sample.Sample("total frames per second", total_fps, 'fps', metadata=metadata))

    if test_mode == 'LIVE':
      metadata['fps_threshold'] = fps_threshold

      if float(lowest_fps) >= float(fps_threshold):
        self.num_tests_passed += 1
        metadata['threshold_met'] = True
      else:
        metadata['threshold_met'] = False

      metadata['total_fps'] = total_fps

      num_transcodes = "{:.2f}".format(float(total_fps) / float(fps_threshold))
      samples.append(sample.Sample("number of transcodes", num_transcodes, 'transcodes', metadata=metadata))

  def PostProcessEmon(self, dirname, num_inst):
    """Moves EMON data to a run-specific sub-directory so that it isn't overwritten in subsequent runs"""
    target_dir = os.path.join(dirname, str(num_inst) + "_instance_w_traces", "emon")
    logging.debug("Fetching EMON results, target EMON output directory is {}".format(target_dir))

    self.vm.RemoteCommand("cd %s && sudo mkdir -p %s" % (dirname, target_dir))
    self.vm.RemoteCommand("cd %s && tar -czf %s %s" % (INSTALL_DIR, "emon_out.tar.gz", "emon*.dat"))
    self.vm.RemoteCommand("cd %s && sudo mv emon_out.tar.gz %s/" % (INSTALL_DIR, target_dir))
