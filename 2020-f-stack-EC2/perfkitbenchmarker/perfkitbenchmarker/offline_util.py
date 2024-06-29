# Copyright 2017 PerfKitBenchmarker Authors. All rights reserved.
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
"""
This class is for starting and using a man-in-the-middle service for capturing
and using cache for benchmarks. The intent is so users may build caches and use
them in an offline environment.

For now this will remain a local service.

"""
import os
import hashlib
import logging
import json
import time
from absl import flags
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import version
from perfkitbenchmarker.linux_packages import mitmproxy


flags.DEFINE_string('offline_mode',
                    '',
                    'Select offline mode: log, record, or replay')
flags.DEFINE_string('offline_cakey',
                    '~/.mitmproxy/mitmproxy-ca-cert.cer',
                    'mitmproxy CA key file')
flags.DEFINE_string('offline_upstream_proxy',
                    'http://proxy-chain.intel.com:912',
                    'Proxy to use for upstream connections')
flags.DEFINE_string('offline_executable',
                    '/usr/bin/mitmdump',
                    'offline mode executable')
flags.DEFINE_string('offline_listen_ipaddr',
                    '',
                    'IP address to bind offlineproxy to')
flags.DEFINE_string('offline_listen_port',
                    '8920',
                    'Port to bind mitmproxy to')
flags.DEFINE_string('offline_cache_file',
                    '',
                    'Cache file name, saved to run directory')
flags.DEFINE_string('offline_log',
                    '',
                    'offline log file')
flags.DEFINE_string('offline_error_log',
                    '',
                    'offline error log file')
flags.DEFINE_string('offline_cache_key_prefix',
                    '~/CumulusCA/intermediate',
                    'Offline cache signing key')
flags.DEFINE_string('offline_cache_publisher',
                    'Project Cumulus',
                    'Name of party publishing the cache (i.e. your team name)')
flags.DEFINE_string('offline_cache_customer',
                    'Internal Intel',
                    'Target customer for cache')
flags.DEFINE_string('offline_cache_security',
                    'Intel Confidential',
                    'Security level assigned to cache')
flags.DEFINE_string('offline_cache_version',
                    '1.0',
                    'Cache version')
flags.DEFINE_string('offline_cache_description',
                    'Cumulus Cache File',
                    'Cache file description')
flags.DEFINE_string('cumulus_root_cert',
                    'Cumulus_Root.pem',
                    'Cumulus Root RSA Certificate')
flags.DEFINE_bool('offline_insecure',
                  False,
                  'Ignore failed cache verification')
FLAGS = flags.FLAGS


class OfflineProxyService(object):
  """
    Utility class for starting/stopping a proxy service, recording,
    and replaying a cache in offline mode.
  """
  def __init__(self):
    self.RootKey = FLAGS.cumulus_root_cert
    self.OfflineExecutable = FLAGS.offline_executable
    self.OfflineUpstreamProxy = FLAGS.offline_upstream_proxy
    self.OfflineListenHost = FLAGS.offline_listen_ipaddr
    self.OfflineListenPort = FLAGS.offline_listen_port
    self.OfflineInsecure = FLAGS.offline_insecure
    self.OfflineCacheUserPath = FLAGS.offline_cache_file
    if not os.path.dirname(self.OfflineCacheUserPath):
      self.OfflineCacheFile = vm_util.GetTempDir() + '/' + self.OfflineCacheUserPath
    else:
      self.OfflineCacheFile = self.OfflineCacheUserPath
    if not FLAGS.offline_log:
      self.OfflineLog = vm_util.GetTempDir() + '/offline_mode.log'
    else:
      self.OfflineLog = FLAGS.offline_log
    if not FLAGS.offline_error_log:
      self.OfflineErrorLog = vm_util.GetTempDir() + '/offline_mode-error.log'
    else:
      self.OfflineErrorLog = FLAGS.offline_error_log
    # Use default location
    self.OfflineCaKey = os.path.expanduser(FLAGS.offline_cakey)
    # Set the default cache properties
    self.CacheProperties = {
        "publisher": FLAGS.offline_cache_publisher,
        "customer": FLAGS.offline_cache_customer,
        "security": FLAGS.offline_cache_security,
        "description": FLAGS.offline_cache_description,
        "version": FLAGS.offline_cache_version,
        "pkb_version": version.VERSION,
    }
    if not os.path.exists(self.OfflineExecutable):
      # If we don't pass a VM object, it will install locally
      logging.warn("Unable to find {0}. Attempting to install...".format(self.OfflineExecutable))
      mitmproxy.Install()

  def Stop(self):
    """ Stop the mitmproxy process used for offline mode. """
    cmd = "pidof -x {}".format(self.OfflineExecutable).split(" ")
    Pid = vm_util.IssueCommand(cmd)[0].rstrip('\n')
    logging.info('Killing PID: {}'.format(Pid))
    try:
      vm_util.IssueCommand(['kill',
                           '{}'.format(Pid)],
                           self.OfflineLog,
                           self.OfflineErrorLog)
    except:
      vm_util.IssueCommand(['kill', '-9',
                           '{}'.format(Pid)],
                           self.OfflineLog,
                           self.OfflineErrorLog)

  def GetProxyString(self):
    """ Assemble proxy string for use in SUT configuration. """
    ProxyString = "http://{0}:{1}".format(self.OfflineListenHost,
                                          self.OfflineListenPort)
    return ProxyString

  def StartUpstreamMode(self):
    """
      Start a proxy service for the purpose of inspecting traffic during
      workload execution.
    """
    vm_util.IssueBackgroundCommand(['{}'.format(self.OfflineExecutable),
                                    '--mode', 'upstream:{}'
                                   .format(self.OfflineUpstreamProxy),
                                    '--listen-host', '{}'
                                   .format(self.OfflineListenHost),
                                    '--listen-port', '{}'
                                   .format(self.OfflineListenPort)],
                                   self.OfflineLog, self.OfflineErrorLog)

  def StartRecordMode(self):
    """
      Start a proxy service for the purpose of recording a cache during a
      workload execution.
    """
    vm_util.IssueBackgroundCommand(['{}'.format(self.OfflineExecutable),
                                    '--mode', 'upstream:{}'.format(
                                    self.OfflineUpstreamProxy),
                                    '--save-stream-file', '{}'.format(self.OfflineCacheFile),
                                    '--listen-host', '{}'.format(
                                    self.OfflineListenHost),
                                    '--listen-port', '{}'.format(
                                    self.OfflineListenPort),
                                    '--anticache'],
                                   self.OfflineLog, self.OfflineErrorLog)

  def StartReplayMode(self):
    """
      Start a proxy service for the purpose of replaying a workload cache
      in full offline mode.
    """
    # IN replay mode we need the user-specified path instead on the TempDir path
    if not os.path.exists(self.OfflineCacheFile):
      logging.error("Path does not exist: {}".format(self.OfflineCacheFile))
      raise Exception("Unable to continue without valid cache file.")
    if not self.VerifyManifest("{}".format(self.GetManifestFilename())):
      logging.warn("Unable to verify the signature of the manifest!")
      if not self.OfflineInsecure:
        raise Exception("Failed to verify signature. Refusing to continue! (override --offline_insecure=True")
    else:
      logging.info("Manifest signature verified successfully.")
    if not self.VerifyChecksum("{}".format(self.GetManifestFilename())):
      logging.warn("Checksum verification failed!")
      if not self.OfflineInsecure:
        raise Exception("Failed to verify checksum. Refusing to continue! (override --offline_insecure=True")
    else:
      logging.info("Checksum for cache verified successfully.")
    vm_util.IssueBackgroundCommand(['{}'.format(self.OfflineExecutable),
                                    '--listen-host', '{}'.format(
                                    self.OfflineListenHost),
                                    '--listen-port', '{}'.format(
                                    self.OfflineListenPort),
                                    '--server-replay', '{}'.format(
                                    self.OfflineCacheFile),
                                   '--set', 'server_replay_nopop=true',
                                    '--set', 'upstream_cert=false',
                                    '--mode', 'regular'],
                                   self.OfflineLog, self.OfflineErrorLog)

  def GetFileSize(self, Filename):
    """ Return the size of a given file """
    if os.path.isfile(Filename):
      return(os.path.getsize(Filename))
    else:
      raise IOError('Cannot get size of non-existent file!')

  def GenChecksum512(self, File):
    """
      Returns a checksum for the given file
    """
    BlockSize = 65536
    Hasher = hashlib.sha512()
    with open(File, 'rb') as fh:
      Buf = fh.read(BlockSize)
      while len(Buf) > 0:
        Hasher.update(Buf)
        Buf = fh.read(BlockSize)
    return(Hasher.hexdigest())

  def GetManifestChecksum(self, Manifest):
    result = {}
    with open(Manifest, "r") as fh:
      ManifestData = json.load(fh)
    for entry in ManifestData["manifest"]["entry"]:
        result[entry["filename"]] = entry["sha512sum"]
        break  # Right now we only have a single entry per manifest
    return result

  def VerifyChecksum(self, Manifest):
    """ Returns a boolean for checksum verification """
    try:
      ManifestSum = self.GetManifestChecksum(Manifest)
    except:
      logging.warn("Unable to obtain checksum!")
      return False
    CurrentSum = self.GenChecksum512(self.OfflineCacheFile)
    if CurrentSum == ManifestSum[os.path.basename(self.OfflineCacheFile)]:
      result = True
    else:
      result = False
      logging.warn("Checksum from manifest doesn't match current checksum: ManifestSum: {0} ; CurrentSum: {1}".format(ManifestSum, CurrentSum))
    return result

  def WriteManifest(self):
    ts = time.gmtime()
    ManifestEntry = {
        "manifest":
            {
                "entry":
                [
                    {
                        "filename": "{}".format(os.path.basename(self.OfflineCacheFile)),
                        "description": "{}".format(self.CacheProperties["description"]),
                        "version": "{}".format(self.CacheProperties["version"]),
                        "pkb_version": "{}".format(self.CacheProperties["pkb_version"]),
                        "publisher": "{}".format(self.CacheProperties["publisher"]),
                        "customer": "{}".format(self.CacheProperties["customer"]),
                        "security": "{}".format(self.CacheProperties["security"]),
                        "size": "{}".format(self.GetFileSize(self.OfflineCacheFile)),
                        "sha512sum": "{}".format(self.GenChecksum512(self.OfflineCacheFile)),
                        "created": "{}".format(time.strftime("%Y-%m-%d %H:%M:%S", ts))
                    },
                ]
            }
    }
    Manifest = self.GetManifestFilename()
    ManifestJson = json.dumps(ManifestEntry)
    with open(Manifest, "w") as fh:
      fh.write(ManifestJson)
    logging.info("Manifest written to {}".format(Manifest))
    return Manifest

  def VerifyManifest(self, Manifest):
    cmd = "openssl smime -verify -in {0}.sign -inform DER -content {0} -purpose any -CAfile {1}".format(Manifest, self.RootKey)
    logging.info("executing openssl CMD: {}".format(cmd))
    result = os.system(cmd)
    if result != 0:
      return False
    else:
      return True

  def GetManifestFilename(self):
    return self.OfflineCacheFile + '.manifest'

  def PpManifest(self, Manifest):
    json.dumps(Manifest, indent=4)
