"""
Installs OpenResty (nginx w/ LuaJIT)
"""

import posixpath
import os

from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import data

OPENRESTY_VERSION = "1.17.8.1rc1"
OPENRESTY_SRC_URL = "https://openresty.org/download/openresty-{}.tar.gz".format(OPENRESTY_VERSION)
OPENRESTY_SRC_DIR = posixpath.join(INSTALL_DIR, 'openresty-{}'.format(OPENRESTY_VERSION))
OPENRESTY_INSTALL_DIR = posixpath.join(INSTALL_DIR, 'openresty')
OPENRESTY_BIN = posixpath.join(OPENRESTY_INSTALL_DIR, 'bin', 'openresty')

NGINX_BROTLI_GIT = 'https://github.com/google/ngx_brotli.git'
NGINX_BROTLI_DIR = posixpath.join(INSTALL_DIR, 'ngx_brotli')

NGINX_CONF_FILENAME = 'nginx.conf'
NGINX_CONF_DIR = posixpath.join(OPENRESTY_INSTALL_DIR, 'nginx', 'conf')
NGINX_HTML_DIR = posixpath.join(OPENRESTY_INSTALL_DIR, 'nginx', 'html')


def Start(vm):
  vm.RemoteCommand('ulimit -n 65536; sudo {}'.format(OPENRESTY_BIN))


def TestConfig(vm):
  vm.RemoteCommand('ulimit -n 65536; sudo {} -T'.format(OPENRESTY_BIN))


def Stop(vm):
  vm.RemoteCommand('sudo {} -s quit'.format(OPENRESTY_BIN))


def _Install(vm):
  vm.Install('wget')
  vm.RemoteCommand("cd {} && curl -L {} | tar -xzf -".format(INSTALL_DIR, OPENRESTY_SRC_URL))
  vm.RemoteCommand("cd {} && git clone --recursive {}".format(INSTALL_DIR, NGINX_BROTLI_GIT))
  configure = ['./configure',
               '--prefix={}'.format(OPENRESTY_INSTALL_DIR),
               '--with-http_ssl_module',
               '--with-cc-opt="-O3"',
               '--with-http_stub_status_module',
               '--with-http_v2_module',
               '--add-module={}'.format(NGINX_BROTLI_DIR),
               ]
  vm.RemoteCommand('cd {} && {} && make -j2 && make install'.format(OPENRESTY_SRC_DIR, ' '.join(configure)))


def YumInstall(vm):
  vm.InstallPackages("pcre-devel openssl-devel gcc curl zlib-devel")
  _Install(vm)


def AptInstall(vm):
  vm.InstallPackages("libpcre3-dev libssl-dev perl make build-essential curl zlib1g-dev")
  _Install(vm)


def Uninstall(vm):
  pass
