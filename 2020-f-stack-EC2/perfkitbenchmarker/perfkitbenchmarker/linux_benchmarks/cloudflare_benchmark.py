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

"""The Cloudflare Benchmark"""
import logging
import os
import posixpath
import time

import yaml

from perfkitbenchmarker import data, configs, events, sample, vm_util, errors
from absl import flags

from perfkitbenchmarker.benchmark_spec import BenchmarkSpec
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker.linux_virtual_machine import BaseLinuxMixin
from perfkitbenchmarker.traces import emon, IsAnyTraceEnabled

BENCHMARK_NAME = 'cloudflare'
BENCHMARK_CONFIG = """
cloudflare:
  description: Micro benchmarks suite from cloudflare (
  vm_groups:
    vm_1:
      vm_spec: *default_single_core
"""

FLAGS = flags.FLAGS

# Define the cloudflare-specific command-line options
flags.DEFINE_string('cloudflare_config_file', 'cloudflare_benchmark_tests.yaml',
                    'The cloudflare benchmark tests configuration file')

flags.register_validator('cloudflare_config_file', lambda value: value != "",
                         'The cloudflare workload requires a configuration file (you cannot set '
                         '--cloudflare_config_file=\"\")')


flags.DEFINE_string('cloudflare_run_tests', 'all',
                    'The cloudflare tests to run')


def cloudflare_run_tests_checker(value):
    if (value is None or value == '') and not FLAGS.get_benchmark_usage:
        return False
    return True


flags.register_validator('cloudflare_run_tests',
                         cloudflare_run_tests_checker,
                         'You must specify at least one test to run using --cloudflare_run_tests')

flags.DEFINE_list('cloudflare_run_on_threads', [1],
                  'The cloudflare list of threads to run tests on ex: [1,4,8,16,96]')

# The single instance of the CloudflareWorkload class
cf_instance = None  # type: CfWorkload


def _InstanceWorkload(benchmark_spec):
    """Create the single instance of the CloudflareWorkload class if it isn't already created"""
    global cf_instance
    if cf_instance is None:
        cf_instance = CfWorkload(benchmark_spec)


def ReinitializeFlags():
    FLAGS.cloudflare_config_file = 'cloudflare_benchmark_test.yaml'
    FLAGS.cloudflare_run_tests = 'go'
    FLAGS.cloudflare_run_on_threads = [1]


def GetUsage(_):
    CfWorkload.GetUsage()


def GetConfig(user_config):
    return configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)


def CheckPrerequisites(_):
    try:
        data.ResourcePath("cloudflare/" + FLAGS.cloudflare_config_file)
    except Exception:
        raise errors.Config.InvalidValue(
            'The configuration file \'{}\' specified with --cloudflare_config_file does not exist'.format(
                FLAGS.cloudflare_config_file))


def Prepare(benchmark_spec):
    _InstanceWorkload(benchmark_spec)

    cf_instance.PrepareFiles()
    _InstanceWorkload(benchmark_spec)

    cf_instance.ReadConfig()

    _ReadFlags()

    host = cf_instance.vm
    repo_dir = 'pkb_cf'

    host.RemoveFile(repo_dir)
    host.RemoteCommand('git clone --recurse-submodules '
                       'https://github.com/cloudflare/cf_benchmark.git '
                       f'{repo_dir}')
    host.Install('build_tools')

    _InstallGo(host)
    _GoGetPackage(host)
    _PatchFiles(host, repo_dir)
    _BuildBenchmarks(host, repo_dir)


def Run(benchmark_spec):
    samples = []

    targets = cf_instance.GetTargets(cf_instance.arg_tests)
    logging.info(f"Tests to run: {targets}")

    sorted_targets = cf_instance.SortTargetsByGroup(targets)
    logging.info(f"Tests to run (sorted): {sorted_targets}")

    host = cf_instance.vm
    repo_dir = 'pkb_cf'

    # for iteration in range(cf_instance.arg_iteration):
    for arg_thread in cf_instance.arg_threads:
        logging.info(f"Starting tests execution. Threads [{arg_thread}]")
        _TestExecutionLoop(host, repo_dir, sorted_targets, arg_thread, samples)

    cf_instance.DownloadResults()

    return samples


def _TestExecutionLoop(host, repo_dir, sorted_targets, threads, samples):
    cf_instance.csv_result = CsvResultFile(cf_instance.vm, cf_instance.result_dir, threads)

    if 'lua' in sorted_targets.keys():
        _RunTemplate(_RunLua, sorted_targets['lua'], host, repo_dir, threads, samples)
    if 'brotli' in sorted_targets.keys():
        _RunTemplate(_RunCompression, sorted_targets['brotli'], host, repo_dir, threads, samples)
    if 'gzip' in sorted_targets.keys():
        _RunTemplate(_RunCompression, sorted_targets['gzip'], host, repo_dir, threads, samples)
    if 'openssl-pki' in sorted_targets.keys():
        _RunTemplate(_RunOpensslPki, sorted_targets['openssl-pki'], host, repo_dir, threads, samples)
    if 'openssl-cipher' in sorted_targets.keys():
        _RunTemplate(_RunOpensslCipher, sorted_targets['openssl-cipher'], host, repo_dir, threads, samples)
    if 'go' in sorted_targets.keys():
        _RunTemplate(_RunGo, sorted_targets['go'], host, repo_dir, threads, samples)


def _ReadFlags():
    logging.info(f"Flags cloudflare_run_tests: {FLAGS.cloudflare_run_tests}")
    cf_instance.arg_tests = FLAGS.cloudflare_run_tests.split(',')

    logging.info(f"Flags cloudflare_run_on_threads: {FLAGS.cloudflare_run_on_threads}")
    cf_instance.arg_threads = FLAGS.cloudflare_run_on_threads


def _RunIntermediate(target, host, repo_dir, threads, params_order_reverse=False):
    test = cf_instance.config[target]
    arg = test['arg']
    params_args = [arg, threads]
    params = test['params'].format(*params_args if not params_order_reverse else reversed(params_args))
    cmd = test['cmd']
    return host.RemoteCommand(f"cd {repo_dir} && {cmd} {params}")


def _RunGo(target, host, repo_dir, threads):
    stdout = _RunIntermediate(target, host, repo_dir, threads)
    result = stdout[0].rstrip()
    return result


def _RunOpensslCipher(target, host, repo_dir, threads):
    stdout = _RunIntermediate(target, host, repo_dir, threads, params_order_reverse=True)
    result_raw = stdout[0].rstrip()
    result_gibs = round(float(result_raw) * 1000 / 1024 / 1024 / 1024, 3)
    result = f"{result_gibs} GiB/s"
    return result


def _RunOpensslPki(target, host, repo_dir, threads):
    stdout = _RunIntermediate(target, host, repo_dir, threads, params_order_reverse=True)
    result = f"{stdout[0].rstrip()} ops/s"
    return result


def _RunCompression(target, host, repo_dir, threads):
    stdout = _RunIntermediate(target, host, repo_dir, threads)
    result = f"{stdout[0].rstrip()} MiB/s"
    return result


def _RunLua(target, host, repo_dir, threads):
    stdout = _RunIntermediate(target, host, repo_dir, threads, params_order_reverse=True)
    result = f"{stdout[0].rstrip()} ops/s"
    return result


def _GenerateTemplateSample(test_name, result, threads, samples):
    test = cf_instance.config[test_name]
    arg = test['arg']
    params = test['params']
    cmd = test['cmd']
    metadata = {
        'test_name': test_name,
        'test_threads': threads,
        'test_bin': cmd,
        'test_arg': arg,
        'test_params': params
    }

    if result == "":
        error_str = f"Empty result for test {test_name}"
        logging.error(error_str)
        raise ValueError(error_str)
    result_num = result.split()[0]
    result_unit = result.split()[1]
    samples.append(sample.Sample(f"{test_name}", result_num, result_unit, metadata=metadata))


def _CanControlEmon():
    return FLAGS.trace_allow_benchmark_control and IsAnyTraceEnabled() and emon.IsEnabled()


def _RunTemplate(run_method, targets, host, repo_dir, threads, samples):
    result_obj = cf_instance.csv_result
    for target in targets:
        logging.info("Starting emon")
        if _CanControlEmon():
            events.before_phase.send(events.RUN_PHASE, benchmark_spec=cf_instance.benchmark_spec)
            events.start_trace.send(events.RUN_PHASE, benchmark_spec=cf_instance.benchmark_spec)

        result = run_method(target, host, repo_dir, threads)
        logging.info(f"Result: {result}")
        result_obj.AppendToResult(result, target)
        _GenerateTemplateSample(target, result, threads, samples)

        if _CanControlEmon():
            events.stop_trace.send(events.RUN_PHASE, benchmark_spec=cf_instance.benchmark_spec)

        logging.info("Stopping emon")

        if _CanControlEmon():
            logging.info(f"Debug:target->{target}")
            emon_dir = posixpath.join(cf_instance.result_dir, target)
            cf_instance.PostProcessEmon(emon_dir, threads)


def _PatchFiles(host, repo_dir):
    lua_makefile = data.ResourcePath("cloudflare/bench_lua/Makefile")
    host.PushFile(lua_makefile, f"{repo_dir}/bench_lua/Makefile")

    go_file = data.ResourcePath("cloudflare/go_benchmarks.go")
    host.PushFile(go_file, f"{repo_dir}/go_benchmarks.go")


def _BuildBenchmarks(host: BaseLinuxMixin, repo_dir):
    _CdAndMake(host, f"{repo_dir}/bench_lua")  # lua
    _CdAndMake(host, f"{repo_dir}/comp_bench")  # compression
    host.RemoteCommand(f"cd {repo_dir}/openssl && ./config no-shared && make -j")  # openssl


def _CdAndMake(host: BaseLinuxMixin, dir: str):
    host.RemoteCommand(f'cd {dir} && make')


def _InstallGo(host: BaseLinuxMixin):
    host.Install("wget")
    remove_previous_downloads = "rm -rf go1.15.3* && rm -rf go"
    wget_cmd = "wget https://dl.google.com/go/go1.15.3.linux-amd64.tar.gz"
    untar_cmd = "tar -xvf go1.15.3.linux-amd64.tar.gz"
    remove_previous_go = "sudo rm -rf  /usr/local/go"
    move_cmd = "sudo mv go /usr/local"
    add_go_bin_cmd = "sudo cp /usr/local/go/bin/go /usr/bin/go"
    _RunMultipleCommandOnHost(host, [
        remove_previous_downloads, wget_cmd, untar_cmd, remove_previous_go, move_cmd, add_go_bin_cmd
    ])


def _GoGetPackage(host):
    pkg = "golang.org/x/crypto/chacha20poly1305/..."
    host.RemoteCommand(f"go get -u -v {pkg}")


def _RunMultipleCommandOnHost(host: BaseLinuxMixin, cmds):
    host.RemoteCommand(" && ".join(cmds))


def Cleanup(benchmark_spec):
    pass


class CfWorkload:

    def __init__(self, benchmark_spec: BenchmarkSpec):
        self.arg_threads = None
        self.arg_iteration = None
        self.arg_tests = None

        self.config = {}
        self.benchmark_spec = benchmark_spec
        self.vm = benchmark_spec.vms[0]  # type: BaseLinuxMixin

        self.run_date_time = time.strftime("%F_%T")
        self.result_dir = f"{INSTALL_DIR}/results_{self.run_date_time}"
        self.result_bench_args = f"{self.result_dir}/results_args.csv"
        self.csv_result = None  # type: CsvResultFile

        self.config_file = data.ResourcePath("cloudflare/" + FLAGS.cloudflare_config_file)
        self.benchmark_spec.control_traces = True
        self.run_number = 0

    def PrepareFiles(self):
        self.vm.RemoteCommand(f"mkdir -p {self.result_dir}")
        self.vm.RemoteCommand(f"touch {self.result_bench_args}")

    @staticmethod
    def GetUsage():
        """Display command-line usage information for the this workload"""
        logging.info("cloudflare benchmark  description file:")
        config_file = data.ResourcePath("cloudflare/" + FLAGS.cloudflare_config_file)
        logging.info("  \'{}\'".format(config_file))

        # open file, read tests.
        with open(config_file) as file:
            config = yaml.load(file, Loader=yaml.SafeLoader)
            logging.info("Available cloudflare benchmark tests:")
            for test in sorted(config.keys()):
                logging.info("  {:<35} # {}".format(test, config[test]['description']))

    def ReadConfig(self):
        # Parse the YAML file into the self.config dictionary
        with open(self.config_file) as file:
            self.config = yaml.load(file, Loader=yaml.SafeLoader)

    def GetTargets(self, initial_target_list):
        full_target_list = []

        for target in initial_target_list:
            if target not in self.config.keys():
                raise Exception('ERROR: The test \"{}\" is not present in the test configuration file'.format(target))
            elif 'group' in self.config[target].keys():
                for t1 in self.config[target]['group'].split():
                    for sub_target in self.GetTargets([t1]):
                        if sub_target not in full_target_list:
                            full_target_list.append(sub_target)
            else:
                if target not in full_target_list:
                    full_target_list.append(target)

        return full_target_list

    def SortTargetsByGroup(self, targets):
        sortbygroup = {}
        for target in targets:
            if target in self.config['lua']['group']:
                sortbygroup.setdefault("lua", []).append(target)
            elif target in self.config['brotli']['group']:
                sortbygroup.setdefault("brotli", []).append(target)
            elif target in self.config['gzip']['group']:
                sortbygroup.setdefault("gzip", []).append(target)
            elif target in self.config['openssl-pki']['group']:
                sortbygroup.setdefault("openssl-pki", []).append(target)
            elif target in self.config['openssl-cipher']['group']:
                sortbygroup.setdefault("openssl-cipher", []).append(target)
            elif target in self.config['go']['group']:
                sortbygroup.setdefault("go", []).append(target)
            else:
                raise Exception(f'ERROR: The test {target} is not present in any predefined group')
        logging.info(f"Sorted by groups: {sortbygroup}")
        return sortbygroup

    def DownloadResults(self):
        """Archive and download the result directory"""
        archive = f'results_iter_{self.run_number}.tar.gz'
        self.vm.RemoteCommand('tar -czf {} {}/'.format(archive, self.result_dir))
        self.vm.PullFile(vm_util.GetTempDir(), archive)
        self.run_number = +1

    def PostProcessEmon(self, dirname, core_number):
        target_dir = os.path.join(dirname, f"n{str(core_number)}", "emon")
        logging.info(f"Fetching EMON results, target EMON output directory is {target_dir}")
        self.vm.RemoteCommand(f"sudo mkdir -p {target_dir}")
        self.vm.RemoteCommand(f"sudo mv /tmp/emon_result.tar.gz {target_dir}/")


class CsvResultFile:
    def __init__(self, vm, result_dir, cur_thread, cur_iter=0):
        self.vm = vm
        self.cur_threads = cur_thread
        self.cur_iteration = cur_iter
        self.result_file = f"{result_dir}/results_i{self.cur_iteration}_n{self.cur_threads}"
        self._CreateFile()
        self._PrepareHeader()

    def _CreateFile(self):
        self.vm.RemoteCommand(f"touch {self.result_file}")

    def _PrepareHeader(self):
        self._AddRowToCsvResult("benchmark", f"{self.cur_threads} core")

    def AppendToResult(self, result, target):
        self._AddRowToCsvResult(target, result)

    def _AddRowToCsvResult(self, col1, col2):
        self.vm.RemoteCommand(f"echo '{col1}, {col2}' >> {self.result_file}")
