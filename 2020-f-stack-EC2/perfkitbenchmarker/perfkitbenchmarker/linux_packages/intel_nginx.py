"""
Installs oss nginx from source with the Brotli and LUAJit modules
    Brotli (compression)
    SSL (encryption)
    LUAJit (scripting)
"""
import posixpath
import os

from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import data
from perfkitbenchmarker import vm_util

LUAJIT_VERSION = '2.1-20200102'
NGINX_DEVEL_KIT_VERSION = '0.3.1'
NGINX_LUA_VERSION = '0.10.15'

NGINX_STRANG_NAME = "nginx_rsamb_with_ecdhmb"
NGINX_STRANG_ARCHIVE = "{}.tar.gz".format(NGINX_STRANG_NAME)
NGINX_STRANG_URL = 'ssh://git@gitlab.devtools.intel.com:29418/jestrang/{}.git'.format(NGINX_STRANG_NAME)
NGINX_STRANG_DIR = posixpath.join(INSTALL_DIR, NGINX_STRANG_NAME)

LUAJIT_SRC_URL = 'https://github.com/openresty/luajit2/archive/v{}.tar.gz'.format(LUAJIT_VERSION)
NGINX_DEVEL_KIT_URL = 'https://github.com/simpl/ngx_devel_kit/archive/v{}.tar.gz'.format(NGINX_DEVEL_KIT_VERSION)
NGINX_LUA_URL = 'https://github.com/openresty/lua-nginx-module/archive/v{}.tar.gz'.format(NGINX_LUA_VERSION)
NGINX_BROTLI_GIT = 'https://github.com/google/ngx_brotli.git'

NGINX_SRC_DIR = posixpath.join(NGINX_STRANG_DIR, 'nginx')
LUAJIT_SRC_DIR = posixpath.join(INSTALL_DIR, 'luajit2-{}'.format(LUAJIT_VERSION))
NGINX_DEVEL_KIT_DIR = posixpath.join(INSTALL_DIR, 'ngx_devel_kit-{}'.format(NGINX_DEVEL_KIT_VERSION))
NGINX_LUA_DIR = posixpath.join(INSTALL_DIR, 'lua-nginx-module-{}'.format(NGINX_LUA_VERSION))
NGINX_BROTLI_DIR = posixpath.join(INSTALL_DIR, 'ngx_brotli')

NGINX_INSTALL_DIR = os.path.join(NGINX_STRANG_DIR, "nginx_install")
NGINX_BIN_DIR = posixpath.join(NGINX_INSTALL_DIR, 'sbin')
NGINX_CONF_DIR = posixpath.join(NGINX_INSTALL_DIR, 'conf')
NGINX_HTML_DIR = posixpath.join(NGINX_INSTALL_DIR, 'html')
LUAJIT_LIB_DIR = posixpath.join('/', 'usr', 'local', 'lib')

OPENSSL_LIB_DIR = posixpath.join(NGINX_SRC_DIR, "openssl_install")

NGINX_BIN = 'LD_LIBRARY_PATH={} {}'.format(LUAJIT_LIB_DIR, posixpath.join(NGINX_BIN_DIR, 'nginx'))
NGINX_CONF_FILENAME = 'nginx.conf'


def Start(vm):
  vm.RemoteCommand('ulimit -n 65536; sudo {}'.format(NGINX_BIN))


def TestConfig(vm):
  vm.RemoteCommand('ulimit -n 65536; sudo {} -T'.format(NGINX_BIN))


def Stop(vm):
  vm.RemoteCommand('sudo {} -s quit'.format(NGINX_BIN))


def _Install(vm):
  vm.Install('build_tools')
  vm.Install('curl')
  vm.Install('python2')
  # vm.Install('openssl')
  vm.InstallPackages('wget unzip gcc make')
  # install gcc and g++ v9
  vm.RemoteCommand('sudo add-apt-repository ppa:ubuntu-toolchain-r/test -y && '
                   'sudo apt-get update')
  vm.RemoteCommand('sudo DEBIAN_FRONTEND=\'noninteractive\' /usr/bin/apt-get -y install gcc-9 g++-9')
  if vm.RemoteCommandWithReturnCode('test -L /usr/bin/gcc')[2] == 0:
    vm.RemoteCommand('sudo rm -f /usr/bin/gcc')
  vm.RemoteCommand('sudo ln -s /usr/bin/gcc-9 /usr/bin/gcc')
  if vm.RemoteCommandWithReturnCode('test -L /usr/bin/g++')[2] == 0:
    vm.RemoteCommand('sudo rm -f /usr/bin/g++')
  vm.RemoteCommand('sudo ln -s /usr/bin/g++-9 /usr/bin/g++')

  # URL is Intel internal only, so retrieve archive then push it to the VM
  vm_util.IssueCommand(['rm', '-rf', NGINX_STRANG_NAME], raise_on_failure=False)
  vm_util.IssueCommand(['rm', '-rf', NGINX_STRANG_ARCHIVE], raise_on_failure=False)
  vm_util.IssueCommand(['git', 'clone', NGINX_STRANG_URL])
  vm_util.IssueCommand(['rm', '-rf', os.path.join(NGINX_STRANG_NAME, '.git')])
  archive = ['tar',
             '-czf',
             NGINX_STRANG_ARCHIVE,
             NGINX_STRANG_NAME,
             ]
  vm_util.IssueCommand(archive)
  vm.PushFile(NGINX_STRANG_ARCHIVE, INSTALL_DIR)
  vm.RemoteCommand('cd {} && tar -xzf {}'.format(INSTALL_DIR, NGINX_STRANG_ARCHIVE))

  vm.RemoteCommand('cd {} && curl -L {} | tar -xzf -'.format(INSTALL_DIR, LUAJIT_SRC_URL))
  vm.RemoteCommand('cd {} && curl -L {} | tar -xzf -'.format(INSTALL_DIR, NGINX_DEVEL_KIT_URL))
  vm.RemoteCommand('cd {} && curl -L {} | tar -xzf -'.format(INSTALL_DIR, NGINX_LUA_URL))
  vm.RemoteCommand('cd {} && git clone --recursive {}'.format(INSTALL_DIR, NGINX_BROTLI_GIT))

  # build LuaJIT
  vm.RemoteCommand('cd {} && make && sudo make install'.format(LUAJIT_SRC_DIR))

  # build openssl
  openssl_dir = posixpath.join(NGINX_STRANG_DIR, "openssl")
  openssl_install_dir = posixpath.join(NGINX_STRANG_DIR, "openssl_install")
  vm.RemoteCommand('cd {} && make clean'.format(openssl_dir), ignore_failure=True)
  vm.RemoteCommand('cd {0} && ./config --prefix={1} -Wl,-rpath,{0}'.format(openssl_dir, openssl_install_dir))
  vm.RemoteCommand('cd {} && make update'.format(openssl_dir))
  vm.RemoteCommand('cd {} && make -j 10'.format(openssl_dir))
  vm.RemoteCommand('cd {} && make install -j 10'.format(openssl_dir))

  # build rsamb (requires gcc 9 and python2)
  rsamb_dir = posixpath.join(NGINX_STRANG_DIR, "multibuff-engine", "crypto-mb")
  vm.RemoteCommand('cd {} && make clean'.format(rsamb_dir))
  vm.RemoteCommand('cd {} && OPENSSL={} make libcrypto-mb.a'.format(rsamb_dir, openssl_dir))

  # build engine
  engine_dir = posixpath.join(NGINX_STRANG_DIR, "multibuff-engine")
  vm.RemoteCommand('rm {}/lib/engines-3/rsamultibuff.so'.format(openssl_install_dir), ignore_failure=True)
  vm.RemoteCommand('cd {} && make clean'.format(engine_dir), ignore_failure=True)
  vm.RemoteCommand('cd {} && ./autogen.sh'.format(engine_dir))
  vm.RemoteCommand('cd {} && ./configure --with-openssl-dir={} --with-openssl_install_dir={} --with-ld-opt="-L{} -lcrypto-mb" --with-cc-opt="-DMULTIBUFF_RSA_MAX_BATCH=8 -DMULTIBUFF_RSA_MIN_BATCH=8"'.format(engine_dir, openssl_dir, openssl_install_dir, rsamb_dir))
  vm.RemoteCommand('cd {} && PERL5LIB={} make -j 10'.format(engine_dir, openssl_dir))

  # build nginx
  configure = ['LUAJIT_LIB=/usr/local/lib LUAJIT_INC=/usr/local/include/luajit-2.1',
               './configure',
               '--prefix={}'.format(NGINX_INSTALL_DIR),
               '--add-module={}'.format(NGINX_DEVEL_KIT_DIR),
               '--add-module={}'.format(NGINX_LUA_DIR),
               '--add-module={}'.format(NGINX_BROTLI_DIR),
               '--with-http_stub_status_module',
               '--with-http_v2_module',
               '--with-http_ssl_module',
               '--add-dynamic-module=modules/nginx_rsamultibuff_module',
               '--with-cc-opt="-DNGX_SECURE_MEM -I{}/include -Wno-error=deprecated-declarations"'.format(OPENSSL_LIB_DIR),
               '--with-ld-opt="-Wl,-rpath={0}/lib -L{0}/lib"'.format(OPENSSL_LIB_DIR)
               ]
  vm.RemoteCommand('cd {} && {} && make install'.format(NGINX_SRC_DIR, ' '.join(configure)))


def YumInstall(vm):
  vm.InstallPackages('openssl-devel pcre-devel zlib-devel')
  _Install(vm)


def AptInstall(vm):
  vm.InstallPackages('libssl-dev libpcre3-dev zlib1g-dev')
  _Install(vm)


def Uninstall(vm):
  pass
