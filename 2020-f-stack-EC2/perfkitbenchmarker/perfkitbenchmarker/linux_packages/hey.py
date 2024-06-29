"""
hey -- HTTP Load generator
"""
import posixpath
import re

from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker.linux_packages import golang

INSTALL_CMD = 'GOPATH=%s %s get -u github.com/rakyll/hey' % (golang.GO_PATH_DIR, golang.GO_BIN)

HEY_BIN = posixpath.join(golang.GO_PATH_BIN_DIR, 'hey')


def Run(vm, options, url):
  """
  Runs hey with provided options and url
  Args:
    options: hey command line options
    url: the url
  Returns:
    hey's output (stdout)
  """
  stdout, _ = vm.RobustRemoteCommand('%s %s %s' % (HEY_BIN, options, url))
  return stdout


def ParseSummaryOutput(output):
  """
  Creates dictionary of interesting metrics from hey summary output
  Args:
    output: stdout captured from run of hey
  Returns:
    dictionary where key is metric name and value is a tuple: (value, units, boolean: where True means to average the results)
  """
  """
  Example output:
  Summary:
    Total:        0.2018 secs
    Slowest:      0.0066 secs
    Fastest:      0.0001 secs
    Average:      0.0003 secs
    Requests/sec: 49554.6646

    Total data:   6120000 bytes
    Size/request: 612 bytes

  Response time histogram:
    0.000 [1]     |
    0.001 [9725]  |++++++++++++++++++
    0.001 [245]   |+++
    0.002 [13]    |
    0.003 [5]     |
    0.003 [5]     |
    0.004 [1]     |
    0.005 [2]     |
    0.005 [1]     |
    0.006 [0]     |
    0.007 [2]     |


  Latency distribution:
    10% in 0.0002 secs
    25% in 0.0003 secs
    50% in 0.0003 secs
    75% in 0.0003 secs
    90% in 0.0003 secs
    95% in 0.0005 secs
    99% in 0.0009 secs

  Details (average, fastest, slowest):
    DNS+dialup:   0.0000 secs, 0.0001 secs, 0.0066 secs
    DNS-lookup:   0.0000 secs, 0.0000 secs, 0.0000 secs
    req write:    0.0000 secs, 0.0000 secs, 0.0065 secs
    resp wait:    0.0003 secs, 0.0001 secs, 0.0025 secs
    resp read:    0.0000 secs, 0.0000 secs, 0.0045 secs

  Status code distribution:
    [200] 10000 responses
  """
  results = {}
  match = re.search(r'Total:\s*(\d+.\d+)', output)
  if match:
    results['Total'] = (float(match.group(1)), 'sec', False)
  match = re.search(r'Slowest:\s*(\d+.\d+)', output)
  if match:
    results['Slowest'] = (float(match.group(1)), 'sec', False)
  match = re.search(r'Fastest:\s*(\d+.\d+)', output)
  if match:
    results['Fastest'] = (float(match.group(1)), 'sec', False)
  match = re.search(r'Average:\s*(\d+.\d+)', output)
  if match:
    results['Average'] = (float(match.group(1)), 'sec', False)
  match = re.search(r'Requests\/sec:\s*(\d+.\d+)', output)
  if match:
    results['Throughput'] = (float(match.group(1)), 'Requests/sec', False)
  match = re.search(r'Total data:\s*(\d+)', output)
  if match:
    results['Total data size'] = (float(match.group(1)), 'bytes', False)
  match = re.search(r'Size\/request:\s*(\d+)', output)
  if match:
    results['Size/request'] = (float(match.group(1)), 'bytes', True)
  match = re.search(r'90% in\s+(\d+.\d+)\s+secs', output)
  if match:
    results['p90'] = (float(match.group(1)), 'secs', False)
  match = re.search(r'95% in\s+(\d+.\d+)\s+secs', output)
  if match:
    results['p95'] = (float(match.group(1)), 'secs', False)
  match = re.search(r'99% in\s+(\d+.\d+)\s+secs', output)
  if match:
    results['p99'] = (float(match.group(1)), 'secs', False)
  match = re.search(r'\[200\]\s+(\d+)\s+responses', output)
  if match:
    results['HTTP 200 OK'] = (float(match.group(1)), 'responses', False)
  return results


def Install(vm):
  vm.Install('golang')
  vm.RemoteCommand(INSTALL_CMD)


def Uninstall(vm):
  pass
