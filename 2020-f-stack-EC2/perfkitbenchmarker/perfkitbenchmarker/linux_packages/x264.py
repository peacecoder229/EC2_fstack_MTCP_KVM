from perfkitbenchmarker.linux_packages import INSTALL_DIR
from absl import flags

FLAGS = flags.FLAGS

ENCODERS_DIR = INSTALL_DIR + '/encoders'


def _Install(vm):
  vm.RemoteCommand('mkdir -p {}'.format(ENCODERS_DIR))
  x264_cmds = [
      'cd {}'.format(ENCODERS_DIR),
      'git -C x264 pull 2> /dev/null || git clone --depth 1 https://code.videolan.org/videolan/x264.git',
      'cd x264',
      'PATH="$HOME/bin:$PATH" PKG_CONFIG_PATH="$HOME/ffmpeg_build/lib/pkgconfig" ./configure --prefix="$HOME/ffmpeg_build" --bindir="$HOME/bin" --enable-static --enable-pic',
      'PATH="$HOME/bin:$PATH" make -j',
      'sudo make install'
  ]
  vm.RemoteCommand(' && '.join(x264_cmds))


def YumInstall(vm):
  vm.InstallEpelRepo()
  required_packages = (
      'autoconf automake bzip2 bzip2-devel cmake freetype-devel '
      'gcc gcc-c++ git git libtool make pkgconfig zlib-devel '
      'sysstat libass libass-devel libvpx-devel bzip2-devel dstat nasm yasm'
  )
  vm.InstallPackages(required_packages)
  _Install(vm)


def AptInstall(vm):
  # TODO: Consider using sudo apt-get install x264
  required_packages = (
      'curl yasm cmake numactl nasm yasm make mercurial libnuma-dev '
      'linux-tools-common linux-tools-aws sysstat dstat '
      'autoconf automake  build-essential cmake git-core libass-dev '
      'libfreetype6-dev libsdl2-dev libtool libva-dev libvdpau-dev '
      'libvorbis-dev libxcb1-dev libxcb-shm0-dev libxcb-xfixes0-dev '
      'pkg-config texinfo zlib1g-dev libvpx-dev'
  )
  vm.InstallPackages(required_packages)
  _Install(vm)


def Uninstall(vm):
  vm.RemoteCommand('sudo rm -rf {}/x264'.format(ENCODERS_DIR))
