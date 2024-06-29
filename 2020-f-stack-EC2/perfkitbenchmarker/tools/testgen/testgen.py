#!/usr/bin/env python

import argparse
import random
import subprocess
import uuid
import yaml

def GetArgs(dict):
  args = []
  for key in sorted(dict.keys()):
    if dict[key] == True:
      args.append("--{}".format(key))
    elif dict[key] == False:
      pass 
    else:
      args.append("--{}={}".format(key, dict[key]))
  return args

def GetRunStageArgs(run_uri, run_stage):
  args = []
  args.append("--run_uri={}".format(run_uri))
  args.append("--run_stage={}".format(run_stage))
  return args

def GetBasicCommandLine(platform, pkb, benchmark):
  cmdline = []
  cmdline.extend(['/usr/bin/python3'])
  cmdline.extend(['./pkb.py'])
  cmdline.extend(GetArgs(platform))
  cmdline.extend(GetArgs(pkb))
  cmdline.extend(GetArgs(benchmark))
  return cmdline

def GetConfigFileFromRepo(url, file_name):
  try:
    command = "curl {} --output {}".format(url,file_name)
    download = subprocess.Popen(command, shell=True)
    download.wait()
  except subprocess.CalledProcessError as e:
    print(e.output)

def main():
  # TODO: Run each test case on a separate thread (option to run in parallel)
  parser = argparse.ArgumentParser(description='Generate, and optionally run, benchmark tests.')
  parser.add_argument("--type", type=str, choices=['developer', 'benchmark', 'acceptance', 'regression','random'], default="developer", help="The test types")
  parser.add_argument('--input', type=str, default="test_cases.yaml", help='The YAML file that defines the test cases')
  parser.add_argument("--execute", default=False, action='store_true', help="Whether to execute each test")
  parser.add_argument("--platform", type=str, default="default", help="The platform on which to run the tests")
  args = parser.parse_args()

  with open(args.input) as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

  if args.type == 'random':
    for _ in range(10):
      platform_name = random.choice(config['platforms'].keys())
      platform = config['platforms'][platform_name]

      pkb_name = random.choice(config['pkb-configurations'].keys())
      pkb = config['pkb-configurations'][pkb_name]

      benchmark_name = random.choice(config['benchmark-configurations'].keys())
      benchmark = config['benchmark-configurations'][benchmark_name]

      cmdline = GetBasicCommandLine(platform, pkb, benchmark)

      print("# Platform : {}".format(platform_name))
      print("# PKB      : {}".format(pkb_name))
      print("# Workload : {}".format(benchmark_name))
      print(' '.join(cmdline))
      print("")
  else:
    test_suite_node = config['test-suites'][args.type]
    for test in sorted(test_suite_node):
      try:
        test_node = test_suite_node[test]
  
        cmdline = []
        cmdline.extend(['/usr/bin/python3'])
        cmdline.extend(['./pkb.py'])
        if 'platform' in test_node.keys():
          cmdline.extend(GetArgs(test_node['platform']))
        else:
          cmdline.extend(GetArgs(config['platforms'][args.platform]))
        cmdline.extend(GetArgs(test_node['pkb']))
        cmdline.extend(GetArgs(test_node['benchmark']))

        if 'config' in test_node.keys():
          GetConfigFileFromRepo(test_node['config'], (test_node['platform']['benchmark_config_file']))
        
        if 'run_stages' in test_node.keys():
          run_uri = str(uuid.uuid4())[-8:]
          if args.execute:
            print('Executing test: {}...'.format(test))
          else:
            print('# {}'.format(test))

          for key in sorted(test_node['run_stages']):
            run_stage_cmdline = cmdline[:]
            run_stage_cmdline.extend(GetRunStageArgs(run_uri, test_node['run_stages'][key]))
            if args.execute:
              print(' '.join(run_stage_cmdline))
              p = subprocess.Popen(' '.join(run_stage_cmdline), shell=True)
              p.wait()
            else:
              print(' '.join(run_stage_cmdline))
              print('')
        else:
          if args.execute:
            print('Executing test: {}...'.format(test))
            print(' '.join(cmdline))
            print('')
            p = subprocess.Popen(' '.join(cmdline), shell=True)
            p.wait()
          else:
            print('# {}'.format(test))
            print(' '.join(cmdline))
            print('')
  
      except KeyError:
        print("The '{}' entry is invalid".format(test))

if __name__ == "__main__":
  main()
