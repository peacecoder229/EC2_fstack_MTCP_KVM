from perfkitbenchmarker import configs
from perfkitbenchmarker.linux_packages import mlc


BENCHMARK_NAME = 'mlc'
BENCHMARK_CONFIG = """
mlc:
  description: >
    Uses Intel Memory Latency Checker to measure system
    memory performance.
  vm_groups:
    default:
      os_type: ubuntu1804
      vm_spec: *default_single_core
  flags:
"""


def GetConfig(user_config):
  return configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)


def Prepare(benchmark_spec):
  mlc.EnableHugePages(benchmark_spec.vms[0])
  benchmark_spec.vms[0].Install('mlc')


def Run(benchmark_spec):
  return mlc.Run(benchmark_spec.vms[0])


def Cleanup(benchmark_spec):
  mlc.DisableHugePages(benchmark_spec.vms[0])
