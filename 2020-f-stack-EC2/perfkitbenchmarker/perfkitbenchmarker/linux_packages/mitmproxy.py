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


"""Module containing mitmproxy installation and cleanup functions."""
import logging
from perfkitbenchmarker import vm_util


def Install(vm=None):
  """Installs the package on the VM."""
  if vm is None:
    _LocalInstall()
  else:
    vm.Install('pip')
    vm.RemoteCommand('sudo pip install {}'.format(_GetMitmproxyVersion()))


def _LocalInstall():
  vm_util.IssueCommand('sudo pip install {}'.format(_GetMitmproxyVersion()))


def _GetMitmproxyVersion():
  Requirements = "perfkitbenchmarker/data/mitmproxy/requirements.txt"
  try:
    cmd = [
        "egrep '^mitmproxy' {}".format(Requirements)
    ]
    return vm_util.IssueCommand(cmd[0])[0].rstrip('\n')
  except Exception as e:
    logging.error("Error accessing {0}: {1}".format(Requirements, e))
  finally:
    # Give a default
    return "mitmproxy==4.0.4"
