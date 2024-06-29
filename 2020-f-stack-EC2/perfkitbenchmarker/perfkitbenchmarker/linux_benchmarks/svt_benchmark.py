import posixpath
import functools
import logging
import re

from perfkitbenchmarker import configs
from absl import flags
from perfkitbenchmarker import sample
from perfkitbenchmarker import vm_util
from perfkitbenchmarker.linux_packages import INSTALL_DIR

ENCODERS = {
    "AV1": {
        "ENCODER_URL": "https://github.com/OpenVisualCloud/SVT-AV1/archive/master.tar.gz",
        "ENCODER_DIR": posixpath.join(INSTALL_DIR, "SVT-AV1-master"),
        "ENCODER_BIN": "SvtAv1EncApp"
    },
    "HEVC": {
        "ENCODER_URL": "https://github.com/OpenVisualCloud/SVT-HEVC/archive/master.tar.gz",
        "ENCODER_DIR": posixpath.join(INSTALL_DIR, "SVT-HEVC-master"),
        "ENCODER_BIN": "SvtHevcEncApp"
    },
    "VP9": {
        "ENCODER_URL": "https://github.com/OpenVisualCloud/SVT-VP9/archive/master.tar.gz",
        "ENCODER_DIR": posixpath.join(INSTALL_DIR, "SVT-VP9-master"),
        "ENCODER_BIN": "SvtVp9EncApp"
    }
}

ALL_BENCHMARKS = ['AV1', 'HEVC', 'VP9']
flags.DEFINE_list('svt_encoders', ALL_BENCHMARKS,
                  'The encoder benchmark(s) to run.')
flags.register_validator(
    'svt_encoders',
    lambda benchmarks: benchmarks and set(benchmarks).issubset(ALL_BENCHMARKS))
flags.DEFINE_bool('svt_numa', True,
                  'Bind encoders to NUMA nodes sequentially.')
FLAGS = flags.FLAGS

BENCHMARK_NAME = 'svt'
BENCHMARK_CONFIG = """
svt:
  description: >
    Scalable Video Technology encoder benchmark.
  vm_groups:
    default:
      os_type: ubuntu1804
      vm_spec:
        GCP:
          machine_type: n1-standard-96
          zone: us-west1-a
          boot_disk_size: 200
        AWS:
          machine_type: m5.24xlarge
          zone: us-west-2
          boot_disk_size: 200
        Azure:
          machine_type: Standard_F72s_v2
          zone: westus
  flags:
"""
SVT_VIDEOS = [
    {
        'url': 'http://ultravideo.cs.tut.fi/video/Beauty_1920x1080_120fps_420_8bit_YUV_RAW.7z',
        'archive': 'Beauty_1920x1080_120fps_420_8bit_YUV_RAW.7z',
        'filename': 'Beauty_1920x1080_120fps_420_8bit_YUV.yuv',
        'w': 1920,
        'h': 1080,
        'fps': 120,
        'seconds': 5,
    },
    {
        'url': 'http://ultravideo.cs.tut.fi/video/Bosphorus_1920x1080_120fps_420_8bit_YUV_RAW.7z',
        'archive': 'Bosphorus_1920x1080_120fps_420_8bit_YUV_RAW.7z',
        'filename': 'Bosphorus_1920x1080_120fps_420_8bit_YUV.yuv',
        'w': 1920,
        'h': 1080,
        'fps': 120,
        'seconds': 5,
    },
    {
        'url': 'http://ultravideo.cs.tut.fi/video/HoneyBee_1920x1080_120fps_420_8bit_YUV_RAW.7z',
        'archive': 'HoneyBee_1920x1080_120fps_420_8bit_YUV_RAW.7z',
        'filename': 'HoneyBee_1920x1080_120fps_420_8bit_YUV.yuv',
        'w': 1920,
        'h': 1080,
        'fps': 120,
        'seconds': 5,
    },
    {
        'url': 'http://ultravideo.cs.tut.fi/video/Jockey_1920x1080_120fps_420_8bit_YUV_RAW.7z',
        'archive': 'Jockey_1920x1080_120fps_420_8bit_YUV_RAW.7z',
        'filename': 'Jockey_1920x1080_120fps_420_8bit_YUV.yuv',
        'w': 1920,
        'h': 1080,
        'fps': 120,
        'seconds': 5,
    },
    {
        'url': 'http://ultravideo.cs.tut.fi/video/ShakeNDry_1920x1080_120fps_420_8bit_YUV_RAW.7z',
        'archive': 'ShakeNDry_1920x1080_120fps_420_8bit_YUV_RAW.7z',
        'filename': 'ShakeNDry_1920x1080_120fps_420_8bit_YUV.yuv',
        'w': 1920,
        'h': 1080,
        'fps': 120,
        'seconds': 5,  # actually 2.5s, leaving this at 5 will cause the encoder to process it twice
    },
    {
        'url': 'http://ultravideo.cs.tut.fi/video/YachtRide_1920x1080_120fps_420_8bit_YUV_RAW.7z',
        'archive': 'YachtRide_1920x1080_120fps_420_8bit_YUV_RAW.7z',
        'filename': 'YachtRide_1920x1080_120fps_420_8bit_YUV.yuv',
        'w': 1920,
        'h': 1080,
        'fps': 120,
        'seconds': 5,
    },
]


def GetConfig(user_config):
  return configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)


def _PrepareVideos(vm):
  """Download and extract video files"""
  def _DownloadAndExtract(video):
    vm.RemoteCommand('cd {} && wget {}'.format(INSTALL_DIR, video['url']))
    vm.RemoteCommand('cd {} && 7za x {} && rm {}'.format(
        INSTALL_DIR, video['archive'], video['archive']))

  vm_util.RunThreaded(_DownloadAndExtract, SVT_VIDEOS)


def _PrepareEncoders(vm):
  """Download and build encoders"""
  def _DownloadAndBuild(encoder):
    encoder_url = ENCODERS[encoder]['ENCODER_URL']
    encoder_dir = ENCODERS[encoder]['ENCODER_DIR']
    vm.RemoteCommand('cd {} && curl -L {} | tar -xzf -'.format(INSTALL_DIR, encoder_url))
    vm.RemoteCommand('cd {} && chmod +x ./build.sh && ./build.sh release'.format(
        posixpath.join(encoder_dir, 'Build', 'linux')))

  vm_util.RunThreaded(_DownloadAndBuild, FLAGS.svt_encoders)


def Prepare(benchmark_spec):
  vm = benchmark_spec.vms[0]
  vm.Install('wget')
  vm.Install('build_tools')
  vm.Install('curl')
  vm.InstallPackages('yasm cmake numactl p7zip-full')
  encoder_partials = [functools.partial(_PrepareEncoders, vm)]
  videos_partials = [functools.partial(_PrepareVideos, vm)]
  vm_util.RunThreaded((lambda f: f()), encoder_partials + videos_partials)


def ParseResults(results, metadata):
  """
  args:
    results: a list of tuple (video, stdout)
  return:
    a list of Sample objects
  """
  samples = []
  """
-------------------------------------------
SVT-AV1 Encoder
SVT [version]:  SVT-AV1 Encoder Lib v0.4.0
SVT [build]  :  GCC 7.3.0        64 bit
LIB Build date: Apr  9 2019 12:44:11
-------------------------------------------
Number of logical cores available: 4
Number of PPCS 41
-------------------------------------------
SVT [config]: Main Profile      Tier (auto)     Level (auto)
SVT [config]: EncoderMode                                                       : 7
SVT [config]: EncoderBitDepth / CompressedTenBitFormat                          : 8 / 0
SVT [config]: SourceWidth / SourceHeight                                        : 1920 / 1080
SVT [config]: FrameRate / Gop Size                                              : 30 / 32
SVT [config]: HierarchicalLevels / BaseLayerSwitchMode / PredStructure          : 4 / 0 / 2
SVT [config]: BRC Mode / QP  / LookaheadDistance / SceneChange                  : CQP / 50 / 33 /
-------------------------------------------
Encoding       200
SUMMARY --------------------------------- Channel 1  --------------------------------
Total Frames            Frame Rate              Byte Count              Bitrate
        200            30.00 fps                   816799              980.16 kbps


Channel 1
Average Speed:          3.354 fps
Total Encoding Time:    59628 ms
Total Execution Time:   60305 ms
Average Latency:        20487 ms
Max Latency:            27647 ms
Encoder finished
"""
  def _GetMetric(regex, stdout):
      match = re.search(regex, stdout)
      return match.group(1), float(match.group(2)), match.group(3)

  sum_average_speed = 0.0
  for video, stdout in results:
      md = metadata.copy()
      md['file_name'] = video['filename']

      metric, average_speed, units = _GetMetric(r'(Average Speed):\s*(\d+.\d+)\s*(\w*)', stdout)
      sum_average_speed += average_speed
      samples.append(sample.Sample(metric, average_speed, units, metadata=md))
      samples.append(sample.Sample(
          *_GetMetric(r'(Total Encoding Time):\s*(\d+)\s*(\w*)', stdout), metadata=md))
      samples.append(sample.Sample(
          *_GetMetric(r'(Total Execution Time):\s*(\d+)\s*(\w*)', stdout), metadata=md))
      samples.append(sample.Sample(
          *_GetMetric(r'(Average Latency):\s*(\d+)\s*(\w*)', stdout), metadata=md))
      samples.append(sample.Sample(
          *_GetMetric(r'(Max Latency):\s*(\d+)\s*(\w*)', stdout), metadata=md))
  samples.append(sample.Sample('Aggregate Speed', sum_average_speed,
                               'fps', metadata=metadata))
  return samples, sum_average_speed


def Run(benchmark_spec):
  vm = benchmark_spec.vms[0]
  samples = []

  def _Run(args):
    index = args['index']
    video = args['video']
    encoder_bin = args['encoder_bin']
    # an approximation of the total number of frames in the file
    num_frames = video['fps'] * video['seconds']
    encode_command = '{} -i {} -w {} -h {} -n {}'.format(
        encoder_bin, video['filename'], video['w'], video['h'], num_frames)
    if FLAGS.svt_numa:
      numa_node = index % vm.numa_node_count
      encode_command = "numactl --membind={} --cpunodebind={} -- {}".format(
          numa_node, numa_node, encode_command)
    # Stdout and stderr are merged as results from binaries are returned in stderr
    stdout, _ = vm.RobustRemoteCommand("cd {} && sudo {} 2>&1".format(INSTALL_DIR, encode_command))
    run_results.append((video, stdout))

  videos = SVT_VIDEOS * 10  # make sure we have enough videos
  for encoder in FLAGS.svt_encoders:
    best_speed = 0
    encoder_bin = posixpath.join(ENCODERS[encoder]['ENCODER_DIR'],
                                 'Bin', 'Release', ENCODERS[encoder]['ENCODER_BIN'])
    for video_count in range(1, len(videos)):
      run_results = []
      vm_util.RunThreaded(_Run, [{'index': index, 'video': video, 'encoder_bin': encoder_bin}
                                 for index, video in enumerate(videos[:video_count])])
      run_samples, speed = ParseResults(run_results, {'file_count': len(run_results),
                                                      'encoder': encoder,
                                                      'numa_bind': str(FLAGS.svt_numa)})
      samples.extend(run_samples)
      logging.info('Aggregate speed when encoding {} file(s) is {} fps.'.format(
          video_count, speed))
      if speed < best_speed:
          samples.append(sample.Sample('Best Aggregate Speed', best_speed,
                                       'fps', metadata={'file_count': video_count - 1,
                                                        'encoder': encoder,
                                                        'numa_bind': str(FLAGS.svt_numa)}))
          break
      best_speed = speed
  return samples


def Cleanup(benchmark_spec):
  pass
