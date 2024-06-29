"""spectre_meltdown_checker.

This runs the spectre-meltdown-checker script.
"""

import logging
import re
from six import StringIO
import time

from perfkitbenchmarker import configs
from perfkitbenchmarker import flag_util
from absl import flags
from perfkitbenchmarker import sample


FLAGS = flags.FLAGS


BENCHMARK_NAME = 'spectre_meltdown_checker'
BENCHMARK_CONFIG = """
spectre_meltdown_checker:
  description: spectre_meltdown_checker.
  vm_groups:
    vm_1:
      os_type: ubuntu1604
      vm_spec: *default_single_core
"""


def GetConfig(user_config):
  return configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)


def Prepare(benchmark_spec):
  """Prepare the client test VM

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  vm = benchmark_spec.vms[0]
  vm.InstallPackages('binutils')
  vm.InstallPackages('git')
  vm.RemoteCommand('git clone https://github.com/speed47/spectre-meltdown-checker.git')


def Run(benchmark_spec):
  """Run the spectre-meltdown-checker script and publishes results.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.

  Returns:
    Results.
  """
  vm = benchmark_spec.vms[0]
  results = []
  stdout, _ = vm.RemoteCommand('cd spectre-meltdown-checker && sudo ./spectre-meltdown-checker.sh --batch text', ignore_failure=True, suppress_warning=True)
  logging.info("stdout:\n%s" % stdout)
  """ Sample output:
  CVE-2017-5753: OK (Mitigation: OSB (observable speculation barrier, Intel v6))
  CVE-2017-5715: OK (Full retpoline + IBPB are mitigating the vulnerability)
  CVE-2017-5754: OK (Mitigation: PTI)
  CVE-2018-3640: VULN (an up-to-date CPU microcode is needed to mitigate this vulnerability)
  CVE-2018-3639: VULN (Your CPU doesn't support SSBD)
  """
  output_io = StringIO(stdout)
  for line in output_io:
    sline = line.strip()
    match = re.search(r'(CVE-[\d]{4}-[\d]{4}): ([\w]*) \((.*)\)', sline)
    results.append(sample.Sample(match.group(1), match.group(2), 'N/A', {'Detail': match.group(3)}))

  return results


def Cleanup(benchmark_spec):
  """Clean up benchmark related states.

  Args:
    benchmark_spec: The benchmark specification. Contains all data that is
        required to run the benchmark.
  """
  vm = benchmark_spec.vms[0]
  vm.RemoteCommand('rm -rf spectre-meltdown-checker')
