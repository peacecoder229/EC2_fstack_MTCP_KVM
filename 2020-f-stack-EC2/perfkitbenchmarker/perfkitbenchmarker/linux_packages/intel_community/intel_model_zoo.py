# Copyright 2019 PerfKitBenchmarker Authors. All rights reserved.
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

"""Module containing installation and cleanup of Intel Model Zoo repository.

   It will download a copy of IntelAI/models reposiory under PKB INSTALL_DIR.
"""

from absl import flags
from perfkitbenchmarker.linux_packages import INSTALL_DIR

# Using mnarusze's fork until upstream issues are fixed
# INTEL_MODEL_ZOO_URL = "https://github.com/IntelAI/models"
INTEL_MODEL_ZOO_URL = "https://github.com/mnarusze-intel/models"
INTEL_MODEL_ZOO_GIT = "{}.git".format(INTEL_MODEL_ZOO_URL)

flags.DEFINE_string('intel_model_zoo_version',
                    'fixes',
                    'Tag, branch name or commit hash of Intel Model Zoo Repository. See {} for more'
                    'information'.format(INTEL_MODEL_ZOO_URL))

flags.DEFINE_string('intel_model_zoo_dir',
                    '/opt/intel/intel_model_zoo',
                    'Directory where Intel Model Zoo will be installed.')

flags.DEFINE_boolean('intel_model_zoo_remove_files',
                     False,
                     'If set, Intel Model Zoo will be removed after the workload is finished.')

FLAGS = flags.FLAGS


def Install(vm):
    vm.InstallPackages('git')
    vm.RemoteCommand('sudo mkdir -p {path} && sudo chown {user} {path}'.format(path=FLAGS.intel_model_zoo_dir, user=vm.user_name))
    vm.RemoteCommand('cd {} ; if [ ! -d .git ] ; then git clone {} . ; fi'.format(FLAGS.intel_model_zoo_dir, INTEL_MODEL_ZOO_GIT))
    vm.RemoteCommand('cd {} && git checkout {}'.format(FLAGS.intel_model_zoo_dir, FLAGS.intel_model_zoo_version))


def Uninstall(vm):
    if FLAGS.intel_model_zoo_remove_files:
        vm.RemoveFile(FLAGS.intel_model_zoo_dir)
