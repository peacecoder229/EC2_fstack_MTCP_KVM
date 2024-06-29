#!/usr/bin/env python
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
""" This is a tool used to sign and verify a manifest. It seems more appropriate
to have a separate tool since not all caches will need to be signed.  """

import argparse
import logging
import os
import json
import hashlib

class ManifestSecurityTools(object):

  def __init__(self):
    self._OpenSSLPresent()
    # Project Cumulus will use an intermediate key
    self.IntermediatePrivKey = "~/CumulusCA/intermediate" 
    self.RootKey = "../../Cumulus_Root.pem"

  def _HaveIntermediateKey(self):
    try:
      os.path.exists(self.IntermediatePrivKey)
    except RuntimeError("{0} signing key does not exist.".format(self.IntermediatePrivKey)):
      logging.error("Unable to sign manifest due to missing key.")
    return True

  def _OpenSSLPresent(self):
    """ Check if openssl is available """
    try:
      os.system("command -v openssl >/dev/null || exit 1")
    except EnvironmentError:
      logging.error("Unable to find openssl executable! Please verify \
                     openssl is installed and in your path.") 

  def VerifyChecksum(self, Manifest):
    """ Returns a boolean for checksum verification """
    Dirname = os.path.dirname(Manifest)
    Cache, ManifestSum = self.GetManifestChecksum(Manifest)
    FQPath = Dirname + '/' + Cache
    CurrentSum = self.GenChecksum512(FQPath)
    if CurrentSum == ManifestSum:
      result = True
      logging.info("Checksum verification success!")
    else:
      result = False
      logging.error("Checksum verification failed!\
                    ManifestSum: {0} ; CurrentSum: {1}"
                    .format(ManifestSum, CurrentSum))
    return result

  def GetManifestChecksum(self, Manifest):
    """ Return first entry in manifest. """
    with open(Manifest, "r") as fh:
      ManifestData = json.load(fh)
    for entry in ManifestData["manifest"]["entry"]:
      return [entry["filename"],entry["sha512sum"]]

  def GenChecksum512(self, File):
    """ Returns a sha512sum for the given file """
    BlockSize = 65536
    Hasher = hashlib.sha512()
    with open(File, 'rb') as fh:
      Buf = fh.read(BlockSize)
      while len(Buf) > 0:
        Hasher.update(Buf)
        Buf = fh.read(BlockSize)
    return(Hasher.hexdigest())

  def SignManifest(self, Manifest):
    """
    OpenSSL sign a manifest. 
    Requires a key, the creation of which is beyond
    the scope of this tool as end users will typically only verify.
    Example:
    openssl genrsa -aes128 -passout pass:<passphrase> -out privkey.pem 4096
    openssl rsa -in privkey.pem -passin pass:<phrase> -pubout -out pubkey.pem
    """
    if not self.VerifyChecksum(Manifest):
      raise Exception("The manifest checksum does not match the current file. Refusing to sign the manifest.")
    self._HaveIntermediateKey()
    cmd = "openssl smime -sign -binary -in {0} -signer {1}.pem -inkey {1}.key -out {0}.sign -outform DER".format(Manifest, self.IntermediatePrivKey)
    try:
        os.system(cmd)
    except Exception:
      logging.error("Signing failed!")

  def VerifyManifest(self, Manifest):
    cmd = "openssl smime -verify -in {0}.sign -inform DER -content {0} -purpose any -CAfile {1}".format(Manifest, self.RootKey)
    try:
        os.system(cmd)
    except Exception:
      logging.error("Validation failed!")

""" Do work """
parser = argparse.ArgumentParser()
parser.add_argument("--manifest", help="manifest to operate on")
parser.add_argument("--sign", help="sign a manifest", action="store_true")
parser.add_argument("--verify", help="verify a manifest signature", action="store_true")
s = ManifestSecurityTools()
args = parser.parse_args()
if args.sign:
  s.SignManifest(args.manifest)
if args.verify:
  s.VerifyManifest(args.manifest)
