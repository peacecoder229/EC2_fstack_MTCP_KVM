from perfkitbenchmarker.linux_packages import INSTALL_DIR
from absl import flags

ENCODERS_DIR = INSTALL_DIR + '/encoders'
X265_GIT_BRANCH = 'Release_3.1'

FLAGS = flags.FLAGS


def _Install(vm):
  vm.RemoteCommand('mkdir -p {}'.format(ENCODERS_DIR))
  x265_cmds = [
      'cd {}'.format(ENCODERS_DIR),
      'git clone https://github.com/videolan/x265.git',
      'cd x265',
      'git checkout {}'.format(X265_GIT_BRANCH),
      'cd ./build/linux',
      'mkdir -p 8bit 10bit 12bit',
      'cd 12bit && PATH="~/bin:$PATH" cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="~/ffmpeg_build" -DHIGH_BIT_DEPTH=ON -DEXPORT_C_API=OFF -DENABLE_SHARED=OFF -DENABLE_CLI=OFF -DMAIN12=ON ../../../source',
      'PATH="~/bin:$PATH" make -j',
      'cd ../10bit && PATH="~/bin:$PATH" cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="~/ffmpeg_build" -DHIGH_BIT_DEPTH=ON -DEXPORT_C_API=OFF -DENABLE_SHARED=OFF -DENABLE_CLI=OFF ../../../source',
      'PATH="~/bin:$PATH" make -j',
      'cd ../8bit && ln -sf ../10bit/libx265.a libx265_main10.a && ln -sf ../12bit/libx265.a libx265_main12.a',
      'PATH="~/bin:$PATH" cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="~/ffmpeg_build" -DEXTRA_LIB="x265_main10.a;x265_main12.a" -DEXTRA_LINK_FLAGS=-L. -DLINKED_10BIT=ON -DLINKED_12BIT=ON ../../../source',
      'PATH="~/bin:$PATH" make -j',
      'mv libx265.a libx265_main.a',
      'echo -e "ar -M <<EOF\nCREATE libx265.a\nADDLIB libx265_main.a\nADDLIB libx265_main10.a\nADDLIB libx265_main12.a\nSAVE\nEND\nEOF" > script.sh',
      'sudo chmod +x script.sh',
      './script.sh',
      'make install'
  ]
  vm.RemoteCommand(' && '.join(x265_cmds))


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
  vm.RemoteCommand('sudo rm -rf {}/x265'.format(ENCODERS_DIR))
