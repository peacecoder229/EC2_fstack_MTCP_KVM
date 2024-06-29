"""Module containing sysstat installation and utility functions."""

VMSTAT_TOOL = 'vmstat'
MPSTAT_TOOL = 'mpstat'
IOSTAT_TOOL = 'iostat'
SAR_TOOL = 'sar'

BASH_TEXT = \
    """#!/bin/bash
%s %s
"""


def StartSysStat(vm, tool, args):
  script = BASH_TEXT % (tool, args)
  start_script = 'start-%s.sh' % (tool)
  command = ["echo '%s' > %s" % (script, start_script),
             "screen -S %sscreen -dm bash %s" % (tool, start_script)
             ]
  vm.RemoteCommand(' && '.join(command))


def StopSysStat(vm, tool):
  vm.RemoteCommand('killall %s' % (tool), ignore_failure=True)


def PostProcessSar(vm, binary_file, csv_file):
  vm.RemoteCommand('sadf -t -d %s -- -A > %s' % (binary_file, csv_file))


def Install(vm):
  vm.InstallPackages('screen sysstat')
