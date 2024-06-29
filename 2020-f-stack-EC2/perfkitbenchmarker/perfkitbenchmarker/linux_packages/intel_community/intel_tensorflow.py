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

"""Module containing pip-based TensorFlow installation and cleanup functions."""

import os

from absl import flags
from perfkitbenchmarker.vm_util import VM_TMP_DIR

FLAGS = flags.FLAGS

flags.DEFINE_enum('intel_tensorflow_name',
                  'intel_tensorflow',
                  ['intel_tensorflow', 'tensorflow'],
                  '''Name of the TF package to be installed. intel-tensorflow uses MKL-DNN and has Intel optimizations
                     whereas tensorflow uses Eigen threads and is currently not optimized for Intel.''')

flags.DEFINE_string('intel_tensorflow_version',
                    '1.14.0',
                    '''Version of TF package to be installed. Benchmark was tested with 1.14.0. Consult
                       https://pypi.org/project/intel-tensorflow/#history and
                       https://pypi.org/project/tensorflow/#history for available versions.''')

flags.DEFINE_string('intel_tensorflow_wheel',
                    None,
                    '''If a custom tensorflow build is desired, you can provide a path to the wheel file on the
                       controller host. 'name' and 'version' flags need to be set to None if a custom wheel is used''')

PIP_CMD = "sudo -H python3 -m pip"


def _CheckFlags(name, version, wheel):
    if (name is not None and version is not None and wheel is None) or \
       (name is None and version is None and wheel is not None):
        return

    raise ValueError("Incorrect flags combination passed. Consult workload README to understand what's wrong.")


def _CheckTFInstallation(vm, version):
    # Ideally we should also check if it's the Intel optimized version but I haven't found a way to do it
    cur_ver, _ = vm.RemoteCommand('echo -e "import tensorflow\nprint(tensorflow.__version__)" | python3')
    if cur_ver.strip() != version:
        raise ValueError("Expected TF to report version {} but got {} instead.".format(version, cur_ver))


def Install(vm):
    name = FLAGS.intel_tensorflow_name
    version = FLAGS.intel_tensorflow_version
    wheel = FLAGS.intel_tensorflow_wheel

    _CheckFlags(name, version, wheel)

    # Make sure that there are no TF conflicts
    Uninstall(vm)

    # intel_tensorflow==1.14 cannot be installed with pip >= 20.0 so let's stick with version that works for all
    cmd = '{} install --upgrade pip=={}'.format(PIP_CMD, "19.3.1")
    vm.RemoteCommand(cmd)

    if wheel is None:
        cmd = '{} install --upgrade {}=={}'.format(PIP_CMD, name, version)
        vm.RemoteCommand(cmd)
        _CheckTFInstallation(vm, version)
    else:
        if not os.path.exists(wheel):
            raise ValueError("Wheel file {} does not exist. Consider absolute path".format(wheel))

        wheel_filename = os.path.basename(wheel)
        if not wheel_filename.endswith("whl"):
            raise ValueError("Unrecognized file format (needs to end with '.whl'): {}".format(wheel))

        _, _, retcode = vm.RemoteCommandWithReturnCode('test -f {}/{}'.format(VM_TMP_DIR, wheel_filename),
                                                       ignore_failure=True)
        if retcode != 0:
            vm.PushFile(wheel, VM_TMP_DIR)
        cmd = '{} install --force-reinstall {}/{}'.format(PIP_CMD, VM_TMP_DIR, wheel_filename)
        vm.RemoteCommand(cmd)


def Uninstall(vm):
    vm.RemoteCommand('{} uninstall intel-tensorflow tensorflow -y'.format(PIP_CMD))
