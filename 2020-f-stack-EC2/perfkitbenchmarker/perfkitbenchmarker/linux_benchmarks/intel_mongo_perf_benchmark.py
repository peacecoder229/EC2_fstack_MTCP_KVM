import tempfile
import os
import logging
import posixpath
import json

from absl import flags

from perfkitbenchmarker import configs
from perfkitbenchmarker import sample
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker import vm_util


flags.DEFINE_string('mongo_perf_mongodb_docker_image', 'cesgsw/mongo-enterprise:4.4.1',
                    'Docker image for MongoDB that will be used.')
flags.DEFINE_boolean("mongo_perf_require_tls", True,
                     "Use TLS secure communications between Mongo client and "
                     "database server.")
flags.DEFINE_string('mongo_perf_tls_key_type', "rsa",
                    "Specify the key type to use for TLS.")
flags.DEFINE_integer("mongo_perf_tls_key_size", 2048,
                     "Specify the key size for TLS...typically 2048 or 4096.")
flags.DEFINE_integer('mongo_perf_client_thread_count', None,
                     'The number of threads each client will use to drive load. When not '
                     'set, the thread count will be set to the number of vCPUs on the server.',
                     lower_bound=1, upper_bound=128)
flags.DEFINE_integer('mongo_perf_vcpus_per_mongodb_instance', 12,
                     'The number of vCPUs per MongoDB instance. Controls the number '
                     'of MongoDB instances used in the benchmark.',
                     lower_bound=1)
flags.DEFINE_integer('mongo_perf_duration', 60,
                     'The number of seconds to run in each iteration.',
                     lower_bound=1)
flags.DEFINE_integer('mongo_perf_iteration_count', 5,
                     'The number of times to measure performance. The best result '
                     'will be reported.',
                     lower_bound=1)
FLAGS = flags.FLAGS

BENCHMARK_NAME = 'intel_mongo_perf'
BENCHMARK_CONFIG = """
intel_mongo_perf:
  description: >
      Run mongo-perf against MongoDB.
  vm_groups:
    clients:
      vm_spec: *default_high_compute
      os_type: ubuntu2004
      vm_count: 1
    workers:
      vm_spec: *default_high_compute
      os_type: ubuntu2004
      vm_count: 1
"""

MONGO_PERF_URL = "https://gitlab.devtools.intel.com/cloud/mongo-perf/-/archive/intel-main/mongo-perf-intel-main.tar.gz"
MONGO_PERF_TARBALL = "mongo-perf-intel-main.tar.gz"
MONGO_PERF_DIRECTORY = "mongo-perf-intel-main"
MONGO_PORT = 27017

MIXED_WORKLOAD_80_20_JS = """
if ( typeof(tests) != "object" ) {
    tests = [];
}
tests.push( { name: "Mixed.FindThenUpdate-80-20",
              tags: ['mixed','indexed','regression'],
              pre: function( collection ) {
                  collection.drop();

                  var docs = [];
                  for ( var i = 0; i < 4800; i++ ) {
                      docs.push( { x : i, y : generateRandomString(1024) } );
                  }
                  collection.insert(docs);
                  collection.getDB().getLastError();
                  collection.ensureIndex( { x : 1 } );
                  collection.ensureIndex( { y : 1 } );
              },
              ops: [
                  { op: "let", target: "x", value: {"#RAND_INT_PLUS_THREAD": [0,100]}},
                  { op: "find",
                    query: { x : { "#VARIABLE" : "x" } } },
                  { op: "let", target: "x", value: {"#RAND_INT_PLUS_THREAD": [0,100]}},
                  { op: "find",
                    query: { x : { "#VARIABLE" : "x" } } },
                  { op: "let", target: "x", value: {"#RAND_INT_PLUS_THREAD": [0,100]}},
                  { op: "find",
                    query: { x : { "#VARIABLE" : "x" } } },
                  { op: "let", target: "x", value: {"#RAND_INT_PLUS_THREAD": [0,100]}},
                  { op: "find",
                    query: { x : { "#VARIABLE" : "x" } } },
                  { op: "update",
                    query: { x : { "#VARIABLE" : "x" } },
                    update: { $set : { y : {"#RAND_STRING": [1024] } } } },
              ] } );
"""

MONGO_RUN_SH_TEMPLATE = """#!/bin/bash
docker run --network host --rm --mount type=bind,src=/opt/pkb,dst=/opt/pkb --mount type=bind,src=/tmp,dst=/tmp --mount type=bind,src={mongo_perf_dir},dst=/mongo-perf -w /mongo-perf {mongo_image} mongo "$@" {tls_options}
"""

WORKLOAD_SCRIPT_NAME = 'mixed_workload_80_20.js'
WORKLOAD_PATH = posixpath.join(INSTALL_DIR, MONGO_PERF_DIRECTORY, 'testcases', WORKLOAD_SCRIPT_NAME)

CERTIFICATE_PATH = posixpath.join(INSTALL_DIR, "mongodb.crt")
PRIVATE_KEY_PATH = posixpath.join(INSTALL_DIR, "mongodb.key")
CERTIFICATE_KEY_PATH = posixpath.join(INSTALL_DIR, "mongodb.pem")


def GetConfig(user_config):
  return configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)


def _GetMongodInstanceCount(vm):
  return max(1, int(vm.NumCpusForBenchmark() / FLAGS.mongo_perf_vcpus_per_mongodb_instance))


def Prepare(benchmark_spec):
  benchmark_spec.always_call_cleanup = True
  worker = benchmark_spec.vm_groups['workers'][0]
  client = benchmark_spec.vm_groups['clients'][0]
  vms = benchmark_spec.vm_groups['workers'] + benchmark_spec.vm_groups['clients']

  def _PrepareCommon(vm):
    vm.Install('docker_ce')

  def _PrepareClient(vm):
    vm.Install('python2')
    vm_util.IssueCommand(["wget", MONGO_PERF_URL, "-P", vm_util.GetTempDir()])
    vm.PushFile(os.path.join(vm_util.GetTempDir(), MONGO_PERF_TARBALL), INSTALL_DIR)
    vm.RemoteCommand("cd {} && tar -xf {}".format(INSTALL_DIR, MONGO_PERF_TARBALL))
    with open(os.path.join(vm_util.GetTempDir(), WORKLOAD_SCRIPT_NAME), 'w') as f:
      f.write(MIXED_WORKLOAD_80_20_JS)
    vm.PushFile(os.path.join(vm_util.GetTempDir(), WORKLOAD_SCRIPT_NAME), WORKLOAD_PATH)

  def _PrepareWorker(vm):
    # Create self-signed certificate, private key, and combined pem files to be used when TLS is required
    subject_name = "/CN={}".format(vm.hostname)
    key_type = "{}:{}".format(FLAGS.mongo_perf_tls_key_type, FLAGS.mongo_perf_tls_key_size)
    openssl_cmd = ['openssl', 'req', '-newkey', key_type, '-new', '-x509', '-days', '3650', '-nodes', '-out', CERTIFICATE_PATH, '-keyout', PRIVATE_KEY_PATH, '-subj', subject_name]
    vm.RemoteCommand(' '.join(openssl_cmd))
    vm.RemoteCommand("sed w{} {} {}".format(CERTIFICATE_KEY_PATH, CERTIFICATE_PATH, PRIVATE_KEY_PATH))

    # start mongod server
    num_mongod_instances = _GetMongodInstanceCount(vm)
    image = FLAGS.mongo_perf_mongodb_docker_image
    cache_gb = max(1, vm.total_memory_kb / 1000000 / 2 / num_mongod_instances)
    for i in range(num_mongod_instances):
        port = MONGO_PORT + i
        mongod_flags = ("--port {port} "
                        "--wiredTigerCacheSizeGB {cache_gb} "
                        "--tlsMode {tls_mode}").format(port=port, cache_gb=cache_gb, tls_mode="requireTLS" if FLAGS.mongo_perf_require_tls else "disabled")
        if FLAGS.mongo_perf_require_tls:
          mongod_flags += " --tlsCertificateKeyFile {pemfile}".format(pemfile=CERTIFICATE_KEY_PATH)
        cmd = ("docker run --rm "
               "--name mongodb-{port} "
               "-p {port}:{port} "
               "--mount type=bind,src=/opt/pkb,dst=/opt/pkb "
               "-d {image} "
               "{mongod_flags}").format(port=port, image=image, mongod_flags=mongod_flags)
        vm.RemoteCommand(cmd)

  vm_util.RunThreaded(_PrepareCommon, vms)
  _PrepareClient(client)
  _PrepareWorker(worker)
  # copy certificate from worker to client
  with tempfile.NamedTemporaryFile() as tf:
    temp_path = tf.name
    worker.RemoteCopy(
        temp_path, CERTIFICATE_PATH, copy_to=False)
    client.RemoteCopy(
        temp_path, CERTIFICATE_PATH, copy_to=True)


def Run(benchmark_spec):

  def _RunMongoClient(vm, index, thread_count, worker):
    script_path = posixpath.join(INSTALL_DIR, 'mongo_run{}.sh'.format(index))
    outfile_path = posixpath.join(INSTALL_DIR, "result_{}.json".format(index))
    workload_path = posixpath.join("testcases", WORKLOAD_SCRIPT_NAME)
    duration = FLAGS.mongo_perf_duration
    iterations = FLAGS.mongo_perf_iteration_count
    host = worker.hostname
    port = MONGO_PORT + index
    mongo_perf_dir = posixpath.join(INSTALL_DIR, MONGO_PERF_DIRECTORY)
    image = FLAGS.mongo_perf_mongodb_docker_image
    tls_options = " --tls --tlsCAFile {}".format(CERTIFICATE_PATH) if FLAGS.mongo_perf_require_tls else ""
    script = MONGO_RUN_SH_TEMPLATE.format(mongo_perf_dir=mongo_perf_dir, mongo_image=image,
                                          tls_options=tls_options)
    with open(os.path.join(vm_util.GetTempDir(), "mongo_run{}.sh".format(index)), 'w') as f:
      f.write(script)
    vm.PushFile(os.path.join(vm_util.GetTempDir(), "mongo_run{}.sh".format(index)), script_path)
    vm.RemoteCommand('chmod +x {}'.format(script_path))
    cmd_template = "cd {mongo_perf_dir}; python2 ./benchrun.py --host {host} --port {port} -f {workload} -t {threadcount} --trialTime {duration} --trialCount {iterations} -s {mongo_run} --out {outfile}"
    cmd = cmd_template.format(mongo_perf_dir=mongo_perf_dir, host=host, port=port,
                              workload=workload_path,
                              threadcount=thread_count, duration=duration, iterations=iterations,
                              mongo_run=script_path, outfile=outfile_path)
    vm.RemoteCommand(cmd)

  def _ParseResults(vm, num_results, thread_count):
    samples = []
    total_ops_per_sec = 0
    for i in range(num_results):
      json_txt = vm.RemoteCommand('cat {}'.format(posixpath.join(INSTALL_DIR, "result_{}.json".format(i))))[0]
      logging.info(json_txt)
      output = json.loads(json_txt)
      for testcase_result in output["results"]:
        max_val = 0
        for val in testcase_result["results"][str(thread_count)]["ops_per_sec_values"]:
          max_val = max(max_val, val)
        total_ops_per_sec += max_val
    samples.append(sample.Sample("Maximum Throughput", total_ops_per_sec, "ops/sec",
                                 {"client threadcount": thread_count,
                                  "mongodb instances": num_results,
                                  "mongodb image": FLAGS.mongo_perf_mongodb_docker_image,
                                  "TLS enabled": "Yes" if FLAGS.mongo_perf_require_tls else "No"}))
    return samples

  worker = benchmark_spec.vm_groups['workers'][0]
  client = benchmark_spec.vm_groups['clients'][0]
  num_mongod_instances = _GetMongodInstanceCount(worker)
  thread_count = FLAGS.mongo_perf_client_thread_count or min(128, worker.NumCpusForBenchmark())
  args = [((client, i, thread_count, worker), {})
          for i in range(num_mongod_instances)]
  vm_util.RunThreaded(_RunMongoClient, args)
  return _ParseResults(client, num_mongod_instances, thread_count)


def Cleanup(benchmark_spec):
    worker = benchmark_spec.vm_groups['workers'][0]
    num_mongod_instances = _GetMongodInstanceCount(worker)
    for i in range(num_mongod_instances):
      port = MONGO_PORT + i
      worker.RemoteCommand("docker stop mongodb-{}".format(port))  # stop container
