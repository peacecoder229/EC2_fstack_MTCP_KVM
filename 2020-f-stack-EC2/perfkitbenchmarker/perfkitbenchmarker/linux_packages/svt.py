from perfkitbenchmarker.linux_packages import INSTALL_DIR
from absl import flags

ENCODERS_DIR = INSTALL_DIR + '/encoders'

FLAGS = flags.FLAGS


def _Install(vm):
  vm.RemoteCommand('mkdir -p {}'.format(ENCODERS_DIR))
  svt_hevc_build_cmds = [
      'cd {}'.format(ENCODERS_DIR),
      'git clone https://github.com/OpenVisualCloud/SVT-HEVC',
      'cd SVT-HEVC',
      'git fetch --all --tags --prune',
      'git checkout v1.3.0',
      'cd Build/linux',
      './build.sh release',
      'cd release',
      'sudo make install',
      'cp ./SvtHevcEnc.pc ~/ffmpeg_build/lib/pkgconfig',
      'cd {}/SVT-HEVC/Bin/Release'.format(ENCODERS_DIR),
      'cp -r ./* ~/ffmpeg_build/lib'
  ]
  vm.RemoteCommand(' && '.join(svt_hevc_build_cmds))


def YumInstall(vm):
  vm.InstallEpelRepo()
  required_packages = (
      'autoconf automake bzip2 bzip2-devel cmake freetype-devel '
      'gcc gcc-c++ git git libtool make mercurial pkgconfig zlib-devel '
      'sysstat libass libass-devel libvpx-devel bzip2-devel dstat nasm yasm'
  )
  vm.InstallPackages(required_packages)
  _Install(vm)


def AptInstall(vm):
  required_packages = (
      'curl yasm cmake numactl nasm yasm make libnuma-dev '
      'linux-tools-common linux-tools-aws sysstat dstat '
      'autoconf automake  build-essential cmake git-core libass-dev '
      'libfreetype6-dev libsdl2-dev libtool libva-dev libvdpau-dev '
      'libvorbis-dev libxcb1-dev libxcb-shm0-dev libxcb-xfixes0-dev '
      'pkg-config texinfo zlib1g-dev libvpx-dev'
  )
  vm.InstallPackages(required_packages)
  _Install(vm)


def Uninstall(vm):
  vm.RemoteCommand('sudo rm -rf {}/SVT-HEVC'.format(ENCODERS_DIR))
