# Copyright 2020 PerfKitBenchmarker Authors. All rights reserved.
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

import warnings

from perfkitbenchmarker import benchmark_sets
from perfkitbenchmarker import benchmark_spec
from perfkitbenchmarker import configs
from perfkitbenchmarker import package_lookup

from absl import flags
from perfkitbenchmarker.configs import benchmark_config_spec

FLAGS = flags.FLAGS


def CreateBenchmarkSpec(benchmark, vms, benchmark_uid):
  warnings.simplefilter("ignore", category=ResourceWarning)

  benchmark_name = benchmark.BENCHMARK_NAME
  config = configs.LoadConfig(benchmark.BENCHMARK_CONFIG, {}, benchmark_name)
  config_spec = benchmark_config_spec.BenchmarkConfigSpec(benchmark_name, flag_values=FLAGS, **config)

  spec = benchmark_spec.BenchmarkSpec(benchmark, config_spec, benchmark_uid)
  spec.vms.extend(vms)
  spec.Provision()

  package_lookup.SetPackageModuleFunction(benchmark_sets.PackageModule)
  return spec


def destroyBenchmarkSpec(spec):
  for vm in spec.vms:
    vm.teardown()
  del spec
