import os
import posixpath
import logging
import time
import re
import glob
import json
import yaml

from absl import flags

from perfkitbenchmarker import configs
from perfkitbenchmarker import sample
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import autoscale_util
from perfkitbenchmarker import linux_packages
from perfkitbenchmarker import data
from perfkitbenchmarker import errors

MEMCACHED_SERVICES = ["memcached-profile", "memcached-rate", "memcached-reserve"]
MONGODB_SERVICES = ["mongodb-geo", "mongodb-profile", "mongodb-rate", "mongodb-recommendation", "mongodb-reservation", "mongodb-user"]
APPLICATION_SERVICES = ["geo", "profile", "rate", "recommendation", "reservation", "search", "user"]
FRONTEND_SERVICES = ["frontend"]
TRACING_SERVICES = ["jaeger"]
TRACING_SERVICES_OUT = ["jaeger-out"]
MESH_SERVICES = ["consul"]
CLIENT_SERVICES = ["wrk2"]
REPLICABLE_SERVICES = FRONTEND_SERVICES + APPLICATION_SERVICES
CACHEDB_SERVICES = MEMCACHED_SERVICES + MONGODB_SERVICES

DEFAULT_CLUSTER_CLIENT_CONNECTION_COUNT = 32
DEFAULT_NAMESPACE = "hotel-res"

DSB_COMMIT_ID = "44f7fbcb452ea001e1dfe94bc2c930cba8d2fd8b"
DSB_URL = f"https://github.com/delimitrou/DeathStarBench/archive/{DSB_COMMIT_ID}.tar.gz"
DSB_ARCHIVE = "DeathStarBench.tgz"
DSB_DIRECTORY = "DeathStarBench"

FLAGS = flags.FLAGS

# Cluster / Machine Configuration
flags.DEFINE_boolean("dsb_hotel_clients_in_cluster", False,
                     "When True, client nodes will be allocated in the K8s cluster.")
flags.DEFINE_integer("dsb_hotel_client_nodes", 1,
                     "Number of client nodes to provision. If dsb_hotel_clients_in_cluster is True, "
                     "these will be provisioned as part of the cluster, otherwise they will be VMs).",
                     lower_bound=1)
flags.DEFINE_integer("dsb_hotel_worker_nodes", 1,
                     "Number of worker nodes to provision. Relevant only if using PKB to provision the cluster.",
                     lower_bound=1)
flags.DEFINE_boolean("dsb_hotel_assign_nodes", False,
                     "When True, the frontend, bizlogic, and cache/database tiers will be assigned to specific "
                     "nodes. The following three flags must be set to specify the number of nodes assigned to "
                     "each tier.")
flags.DEFINE_integer("dsb_hotel_frontend_nodes", 1,
                     "Number of worker nodes allocated to front end services. "
                     "Only relevant when dsb_hotel_assign_nodes is True.",
                     lower_bound=1)
flags.DEFINE_integer("dsb_hotel_application_nodes", 1,
                     "Number of worker nodes allocated to application services. "
                     "Only relevant when dsb_hotel_assign_nodes is True.",
                     lower_bound=1)
flags.DEFINE_integer("dsb_hotel_cachedb_nodes", 1,
                     "Number of worker nodes allocated to cache and database services. "
                     "Only relevant when dsb_hotel_assign_nodes is True.",
                     lower_bound=1)

# Service Replica Configuration
for service in REPLICABLE_SERVICES + CLIENT_SERVICES:
  flags.DEFINE_integer("dsb_hotel_" + service + "_replicas", 1, "The number of replicas for {}.".format(service), lower_bound=1)
flags.DEFINE_integer("dsb_hotel_replicas_override", 0,
                     "If greater than 0, this value will be used to set the number of replicas "
                     "for all replicable services.",
                     lower_bound=0)

# Client Run Options
flags.DEFINE_integer("dsb_hotel_client_instances_per_vm", 1,
                     "Number of client process instances that will be run on each client "
                     "machine. This only applies when dsb_hotel_clients_in_cluster is False.",
                     lower_bound=1)
flags.DEFINE_integer("dsb_hotel_client_connections", None,
                     "Number of connections from each client to the application. None "
                     "to set to num vCPUs on client machine (when dsb_hotel_clients_in_cluster is False), "
                     "otherwise set to default value: {}".format(DEFAULT_CLUSTER_CLIENT_CONNECTION_COUNT),
                     lower_bound=1)
flags.DEFINE_integer("dsb_hotel_client_threads", None,
                     "Number of client threads. None to set to minimum of vCPUs on "
                     "client and number of client connections (can't have more threads than "
                     "connections).",
                     lower_bound=1)
flags.DEFINE_integer("dsb_hotel_client_timeout", 5,
                     "Request timeout in seconds.",
                     lower_bound=1)
flags.DEFINE_integer("dsb_hotel_client_duration", 60,
                     "Number of seconds client(s) will make requests.",
                     lower_bound=1)

# Client Rate and Rate Auto-Scaling Configuration
flags.DEFINE_integer("dsb_hotel_client_rate", None,
                     "Client requests per second. Setting this will disable client "
                     "rate auto-scaling and run the given rate one time.",
                     lower_bound=1)
flags.DEFINE_integer("dsb_hotel_client_rate_autoscale_min", 500,
                     "Client requests per second for first iteration when auto-scaling rate.",
                     lower_bound=1)
flags.DEFINE_integer("dsb_hotel_client_rate_autoscale_increment", 100,
                     "Client requests per second to increment between rate auto-scaling iterations.",
                     lower_bound=1)
flags.DEFINE_integer("dsb_hotel_client_rate_autoscale_max", None,
                     "Client requests per second to short-circuit (exit) rate auto-scaling. "
                     "None allows auto-scaling to continue until throughput decreases.",
                     lower_bound=1)

# Workload Options
flags.DEFINE_string("dsb_hotel_namespace", DEFAULT_NAMESPACE,
                    "The namespace that will be used by the hotel reservation K8s resources.")
flags.DEFINE_string("dsb_hotel_dsb_archive", DSB_URL,
                    "The URL or local path to the DeathStarBench repo archive file.")
flags.DEFINE_string("dsb_hotel_image_cache", "amr-cache-registry.caas.intel.com/cache/",
                    "Set the image cache server and path that Kubernetes/Docker will use to "
                    "pull images. Set to empty string to pull from Docker Hub. If provided, "
                    "string must end with forward slash.")
flags.DEFINE_string("dsb_hotel_docker_image", "cesgsw/dsb-hotel-reservation-microservices:v1.0",
                    "The docker image for Hotel Reservation microservices")
flags.DEFINE_string("dsb_hotel_node_label", None,
                    "A key/value that has been applied to cluster nodes to specify which nodes "
                    "can be used for this application, e.g., 'project=hotel-reservation")
flags.DEFINE_integer("dsb_hotel_p99_sla", 30,
                     "The P99 latency SLA in milliseconds. The maximum throughput "
                     "found with the P99 <= this value will be reported.")
flags.DEFINE_boolean("dsb_hotel_p99_sla_only", False,
                     "Stop the workload when SLA is exceeded.")
flags.DEFINE_float("dsb_hotel_error_limit", 0.05,
                   "The fraction of transactions that are allowed to be errors. "
                   "If this error rate is exceeded, the test will be terminated.")
ALL_WORKLOADS = ['mixed-workload_type_1']
flags.DEFINE_list("dsb_hotel_workloads",
                  ['mixed-workload_type_1'],
                  "The workloads to run. One or more of {}.".format(', '.join(ALL_WORKLOADS)))
flags.register_validator(
    'dsb_hotel_workloads',
    lambda workloads: workloads and set(workloads).issubset(ALL_WORKLOADS))
flags.DEFINE_boolean("dsb_hotel_skip_teardown", False,
                     "When set to True, don't teardown the application between runs and/or iterations.")
flags.DEFINE_boolean("dsb_hotel_deploy_jaeger", False,
                     "When set to True, the workload will deploy Jaeger into the cluster.")

BENCHMARK_NAME = "dsb_hotel"
BENCHMARK_CONFIG = """
dsb_hotel:
  description: DeathStarBench Hotel Reservation
  vm_groups:
    client:
      os_type: ubuntu2004
      vm_spec: *default_dual_core
    controller:
      os_type: ubuntu2004
      vm_spec: *default_dual_core
    worker:
      os_type: ubuntu2004
      vm_spec: *default_dual_core
  container_specs: {}
  container_registry: {}
  container_cluster:
    vm_spec: *default_dual_core
"""

SOCIAL_NETWORK_DIR = posixpath.join(linux_packages.INSTALL_DIR, DSB_DIRECTORY, "socialNetwork")
HOTEL_RES_DIR = posixpath.join(linux_packages.INSTALL_DIR, DSB_DIRECTORY, "hotelReservation")
WRK2_DIR = posixpath.join(SOCIAL_NETWORK_DIR, "wrk2")
WRK2_SCRIPTS_DIR = posixpath.join(HOTEL_RES_DIR, 'wrk2_lua_scripts')

WEB_FRONTEND_PORT = 5000
JAEGER_PORT = 16686

CONFIG_MAPS_APP = {
    "configmap-config-json": "configmaps/config.json"
}


def _IsManagedCluster():
  # if kubeconfig is in the temp dir, it is assumed to have been created by PKB
  # when provisioning a cloud cluster, e.g., EKS
  if FLAGS.kubeconfig:
    return FLAGS.kubeconfig.startswith(vm_util.GetTempDir())
  else:
    return True


def GetConfig(user_config):
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
  client_vm_count = FLAGS.dsb_hotel_client_nodes if not FLAGS.dsb_hotel_clients_in_cluster else 0
  config['vm_groups']['client']['vm_count'] = client_vm_count
  if _IsManagedCluster():
    client_node_count = FLAGS.dsb_hotel_client_nodes if FLAGS.dsb_hotel_clients_in_cluster else 0
    worker_node_count = FLAGS.dsb_hotel_frontend_nodes + FLAGS.dsb_hotel_application_nodes + FLAGS.dsb_hotel_cachedb_nodes if FLAGS.dsb_hotel_assign_nodes else FLAGS.dsb_hotel_worker_nodes
    cluster_node_count = client_node_count + worker_node_count
    config['container_cluster']['vm_count'] = cluster_node_count
    del config['vm_groups']['controller']
    del config['vm_groups']['worker']
  else:  # will provision a cloud cluster
    del config['container_cluster']
    del config['container_specs']
    del config['container_registry']
  return config


def CheckPrerequisites(benchmark_config):
  pass


def _GetClients(benchmark_spec):
  return benchmark_spec.vm_groups["client"] if not FLAGS.dsb_hotel_clients_in_cluster else []


def _GetControlNode(benchmark_spec):
  return benchmark_spec.vm_groups["controller"][0]


def _GetTotalClientConnectionCount(benchmark_spec):
  """ Get the total (all clients included) connection count """
  client_count = len(_GetClients(benchmark_spec)) * FLAGS.dsb_hotel_client_instances_per_vm or FLAGS.dsb_hotel_replicas_override or FLAGS.dsb_hotel_wrk2_replicas
  return _GetClientConnectionCount(benchmark_spec) * client_count


def _GetClientConnectionCount(benchmark_spec):
  """ Get the number of connections for a single client """
  if FLAGS.dsb_hotel_clients_in_cluster:
    return FLAGS.dsb_hotel_client_connections or DEFAULT_CLUSTER_CLIENT_CONNECTION_COUNT
  else:
    return FLAGS.dsb_hotel_client_connections or _GetClients(benchmark_spec)[0].NumCpusForBenchmark()


def _GetClientThreadCount(benchmark_spec):
  """ Get the number of threads for a single client """
  # threads must be less than or equal to connections
  if FLAGS.dsb_hotel_clients_in_cluster:
    return (FLAGS.dsb_hotel_client_threads or
            _GetClientConnectionCount(benchmark_spec))
  else:
    return (FLAGS.dsb_hotel_client_threads or
            min(_GetClientConnectionCount(benchmark_spec),
                _GetClients(benchmark_spec)[0].NumCpusForBenchmark()))


def _GetKubectlPrefix(namespace=None):
  cmd = [FLAGS.kubectl, '--kubeconfig={}'.format(FLAGS.kubeconfig)]
  if namespace:
    cmd.append('--namespace={}'.format(namespace))
  return cmd


def _GetKubectlCmd(cmd, namespace=None):
  return _GetKubectlPrefix(namespace) + cmd


def _RunKubectl(benchmark_spec, cmd, append_namespace=True, suppress_failure=False, suppress_warning=False, force_info_log=False, timeout=vm_util.DEFAULT_TIMEOUT):
  namespace = FLAGS.dsb_hotel_namespace if append_namespace else None
  kubectl_cmd = _GetKubectlCmd(cmd, namespace)
  if _IsManagedCluster():
    return vm_util.IssueCommand(kubectl_cmd, raise_on_failure=not suppress_failure, suppress_warning=suppress_warning, force_info_log=force_info_log, timeout=timeout)
  else:
    return _GetControlNode(benchmark_spec).RemoteCommandWithReturnCode(' '.join(kubectl_cmd), ignore_failure=suppress_failure, suppress_warning=suppress_warning, should_log=force_info_log, timeout=timeout)


def _GetGetNodesCommand(format):
  selectors = ["!node-role.kubernetes.io/master"]
  if FLAGS.dsb_hotel_node_label is not None:
    selectors.append(FLAGS.dsb_hotel_node_label)
  return ['get', 'nodes', '--selector={}'.format(','.join(selectors)), '-o', format]


def _GetClusterWorkerNodes(benchmark_spec):
  cmd = _GetGetNodesCommand('jsonpath={.items..metadata.name}')
  return _RunKubectl(benchmark_spec, cmd)[0].split()


def _DeleteNamespace(benchmark_spec):
  if FLAGS.dsb_hotel_namespace:
    _RunKubectl(benchmark_spec, ['delete', 'namespace', FLAGS.dsb_hotel_namespace], append_namespace=False, suppress_failure=True)


def _CreateNamespace(benchmark_spec):
  if FLAGS.dsb_hotel_namespace:
    _RunKubectl(benchmark_spec, ['create', 'namespace', FLAGS.dsb_hotel_namespace], append_namespace=False)


def _GetNodePort(benchmark_spec, service):
  num_waits_left = FLAGS.k8s_get_retry_count
  web_port = ""
  while not web_port and num_waits_left:
    web_port, _, _ = _RunKubectl(benchmark_spec, ['get', '-o', 'jsonpath="{.spec.ports[0].nodePort}"', 'services', service], suppress_failure=True, suppress_warning=True)
    if not web_port:
      time.sleep(FLAGS.k8s_get_wait_interval)
      num_waits_left -= 1
  if not web_port:
    raise errors.Benchmarks.PrepareException(service + " port not found.")
  return web_port.strip("\"")


def _GetWebPort(benchmark_spec, service):
  if _IsManagedCluster():
    if service == "frontend":
      return WEB_FRONTEND_PORT
    elif service == "jaeger-out":
      return JAEGER_PORT
  else:
    return _GetNodePort(benchmark_spec, service)
  raise errors.Benchmarks.PrepareException("Unknown service.")


def _GetWebIpAddress(benchmark_spec, service):
  web_ip = ""
  num_waits_left = FLAGS.k8s_get_retry_count
  while not web_ip and num_waits_left:
    if _IsManagedCluster():
      stdout, stderr, _ = _RunKubectl(benchmark_spec, ['get', 'svc', service, '-ojsonpath={.status.loadBalancer.ingress[*].hostname}'], suppress_failure=True, suppress_warning=True)
    else:
      stdout, stderr, _ = _RunKubectl(benchmark_spec, _GetGetNodesCommand('json'), suppress_failure=True, suppress_warning=True)
    if stderr:
      raise errors.Benchmarks.PrepareException("Error received from kubectl get: " + stderr)
    if not stdout:
      time.sleep(FLAGS.k8s_get_wait_interval)
      num_waits_left -= 1
      continue
    if _IsManagedCluster():
      web_ip = stdout
    else:
      addresses = json.loads(stdout)["items"][0]["status"]["addresses"]
      for address in addresses:
        if address["type"] == "InternalIP":
          web_ip = address["address"]
  if not web_ip:
    raise errors.Benchmarks.PrepareException(service + ' IP address not found.')
  return web_ip


def _GetSvcIpAddress(benchmark_spec, service):
  return _RunKubectl(benchmark_spec, ['get', 'svc', service, '-ojsonpath={.spec.clusterIP}'])[0]


def _GetWrk2Pods(benchmark_spec):
  output = _RunKubectl(benchmark_spec, ['get', 'pods', '-l', 'app=wrk2', '-o' 'custom-columns=:metadata.name'])[0]
  return [line for line in output.splitlines() if line]


def _UpdateReplicas(benchmark_spec):
  num_client_pods = len(_GetWrk2Pods(benchmark_spec))
  for deployment in REPLICABLE_SERVICES:
    if num_client_pods == 0 and deployment == "wrk2":
      continue
    replicas = FLAGS.dsb_hotel_replicas_override or FLAGS.flag_values_dict()["dsb_hotel_" + deployment + "_replicas"]
    _RunKubectl(benchmark_spec, ['scale', '--replicas', str(replicas), "deployment/{}".format(deployment)])


def _WaitForWebServer(vm, web_frontend_ip, web_frontend_port):
  logging.info("Waiting for web server.")
  response = ""
  num_waits_left = FLAGS.k8s_get_retry_count
  while num_waits_left:
    response = vm.RemoteCommand("wget --no-proxy --spider -S \"{}:{}\" 2>&1".format(web_frontend_ip, web_frontend_port) + r" | awk '/HTTP\// {print $2}'")[0].strip()
    if response == "200":
      break
    logging.info("Sleeping for {} seconds.".format(FLAGS.k8s_get_wait_interval))
    time.sleep(FLAGS.k8s_get_wait_interval)
    num_waits_left -= 1
  if not response:
    raise errors.Benchmarks.PrepareException("Timeout waiting to connect to web server.")


def _WaitForPods(benchmark_spec):
  # make sure the pods have been scheduled
  logging.info("Waiting for all pods to be scheduled.")
  all_running = False
  num_waits_left = FLAGS.k8s_get_retry_count
  while num_waits_left and not all_running:
    all_running = True
    result = _RunKubectl(benchmark_spec, ['get', 'pods', '-o', 'json'])[0]
    pods = json.loads(result)
    for pod in pods["items"]:
      for condition in pod["status"]["conditions"]:
        if condition["status"]:
          continue
        else:
          logging.info("Sleeping for {} seconds.".format(FLAGS.k8s_get_wait_interval))
          time.sleep(FLAGS.k8s_get_wait_interval)
          all_running = False
          break
  if not all_running:
    raise errors.Benchmarks.PrepareException("Timeout waiting for all pods to be scheduled.")
  # make sure the containers are ready
  logging.info("Waiting for all containers to enter ready state.")
  all_running = False
  num_waits_left = FLAGS.k8s_get_retry_count
  while num_waits_left and not all_running:
    all_running = True
    result = _RunKubectl(benchmark_spec, ['get', 'pods', '-o', 'json'])[0]
    pods = json.loads(result)
    for pod in pods["items"]:
      if "containerStatuses" not in pod["status"]:
        all_running = False
        break
      for cstatus in pod["status"]["containerStatuses"]:
        if not cstatus["ready"]:
          all_running = False
          break
      if not all_running:
        break
    logging.info("Sleeping for {} seconds.".format(FLAGS.k8s_get_wait_interval))
    time.sleep(FLAGS.k8s_get_wait_interval)
    num_waits_left -= 1
  if not all_running:
    raise errors.Benchmarks.PrepareException("Timeout waiting for all containers to enter ready state.")


def _CreateConfigMaps(benchmark_spec, config_maps, root_dir):
  for name, file in config_maps.items():
    _RunKubectl(benchmark_spec, ['create', 'configmap', name, '--from-file={}'.format(posixpath.join(root_dir, file))], suppress_failure=True)


def _TweakConfigMaps(benchmark_spec, config_maps):
  rootdir = os.path.join(vm_util.GetTempDir(), DSB_DIRECTORY, "hotelReservation", "openshift")
  deploydir = os.path.join(vm_util.GetTempDir(), 'deploy')
  if not _IsManagedCluster():
    deploydir = posixpath.join(linux_packages.INSTALL_DIR, "deploy")
  for _, filepath in config_maps.items():
    text = ""
    with open(os.path.join(rootdir, filepath), 'r') as f:
      text = f.read()
    text = text.replace(DEFAULT_NAMESPACE, FLAGS.dsb_hotel_namespace)
    if _IsManagedCluster():
      vm_util.IssueCommand(['mkdir', '-p', os.path.join(deploydir, os.path.split(filepath)[0])])
      with open(os.path.join(deploydir, filepath), 'w') as f:
        f.write(text)
    else:
      vm_util.CreateRemoteFile(_GetControlNode(benchmark_spec), text, posixpath.join(deploydir, os.path.split(filepath)[0]))


def _DeployPods(benchmark_spec):
  deploydir = os.path.join(vm_util.GetTempDir(), 'deploy')
  remote_deploydir = posixpath.join(linux_packages.INSTALL_DIR, 'deploy')
  if not _IsManagedCluster():
    _GetControlNode(benchmark_spec).RemoteCommand('rm -rf {0} && mkdir {0}'.format(remote_deploydir))
  for yaml_file in glob.glob(os.path.join(deploydir, "*.yaml")):
    if not _IsManagedCluster():
      _GetControlNode(benchmark_spec).PushFile(yaml_file, remote_deploydir)
      yaml_file = posixpath.join(remote_deploydir, os.path.split(yaml_file)[1])
    _RunKubectl(benchmark_spec, ['apply', '-f', yaml_file])


def _GetPods(benchmark_spec):
  output = _RunKubectl(benchmark_spec, ['get', 'pods', '-o', 'custom-columns=:metadata.name'])[0]
  return [line for line in output.splitlines() if line]


def _DeployApplication(benchmark_spec):
  previously_deployed = len(_GetPods(benchmark_spec)) > 0
  if not previously_deployed:
    _CreateNamespace(benchmark_spec)
    _TweakConfigMaps(benchmark_spec, CONFIG_MAPS_APP)
    root_dir = os.path.join(vm_util.GetTempDir(), 'deploy')
    if not _IsManagedCluster():
      root_dir = posixpath.join(HOTEL_RES_DIR, "openshift")
    _CreateConfigMaps(benchmark_spec, CONFIG_MAPS_APP, root_dir)
    _DeployPods(benchmark_spec)
  _UpdateReplicas(benchmark_spec)
  _WaitForPods(benchmark_spec)
  if not FLAGS.dsb_hotel_clients_in_cluster:
    web_ip_host = _GetWebIpAddress(benchmark_spec, "frontend")
    web_port = _GetWebPort(benchmark_spec, "frontend")
    _WaitForWebServer(_GetClients(benchmark_spec)[0], web_ip_host, web_port)


def _TeardownApplication(benchmark_spec):
  _DeleteNamespace(benchmark_spec)


def _SavePodConfig(benchmark_spec, label):
  filename = vm_util.PrependTempDir('pod_config.txt')
  with open(filename, 'a') as f:
    f.write(f"\n{label}:\n")
    pod_config = _RunKubectl(benchmark_spec, ['get', 'pods', '-o', 'wide', '--all-namespaces'], append_namespace=False, force_info_log=True)[0]
    f.write(pod_config)


def Prepare(benchmark_spec):

  def _PrepareClients(clients):
    def _InstallDependencies(vm):
      vm.InstallPackages("wget luarocks python3-pip")
      vm.RemoteCommand("pip3 install asyncio && pip3 install aiohttp && sudo luarocks install luasocket")
      local_dsb_archive = os.path.join(vm_util.GetTempDir(), DSB_DIRECTORY, DSB_ARCHIVE)
      remote_dsb_directory = posixpath.join(linux_packages.INSTALL_DIR, DSB_DIRECTORY)
      remote_dsb_archive = posixpath.join(remote_dsb_directory, DSB_ARCHIVE)
      vm.RemoteCommand("mkdir -p {}".format(remote_dsb_directory))
      vm.PushFile(local_dsb_archive, remote_dsb_directory)
      vm.RemoteCommand("tar -xf {} --strip-components=1 -C {}".format(remote_dsb_archive, remote_dsb_directory))

    def _InstallWrk2(client):
      client.Install("build_tools")
      client.Install("openssl")
      client.InstallPackages("zlib1g-dev apt-transport-https ca-certificates curl software-properties-common unzip")
      client.RemoteCommand("cd {} && sed -i ' 1 s/.*/& -fPIC/' Makefile && make clean && make".format(WRK2_DIR))

    def _SetMaxOpenFiles(vm, nofile):
      before = int(vm.RemoteCommand('ulimit -n')[0])
      logging.info("vm ulimit -n (before): {}".format(before))
      logging.info("vm nofile minimum needed: {}".format(nofile))
      if nofile > before:
        vm.RemoteCommand('echo "* soft nofile {}" | sudo tee -a /etc/security/limits.conf'.format(nofile))
        vm.RemoteCommand('echo "* hard nofile {}" | sudo tee -a /etc/security/limits.conf'.format(nofile))
        logging.info("vm ulimit -n (after): {}".format(vm.RemoteCommand('ulimit -n')[0]))

    vm_util.RunThreaded(_InstallDependencies, clients)
    vm_util.RunThreaded(_InstallWrk2, clients)
    arbitrary_fudge_factor = 4
    nofiles = _GetClientConnectionCount(benchmark_spec) * FLAGS.dsb_hotel_client_instances_per_vm * arbitrary_fudge_factor
    vm_util.RunThreaded(_SetMaxOpenFiles, [((client, nofiles), {}) for client in clients])

  def _PrepareCluster(benchmark_spec):

    def _ConfigureNodeSelectors(benchmark_spec):
      def _LabelClusterNode(benchmark_spec, node, key, value):
        _RunKubectl(benchmark_spec, ['label', '--overwrite', 'nodes', node, '{}={}'.format(key, value)], append_namespace=False)

      def _ClearNodeAssignments(benchmark_spec, nodes):
        for node in nodes:
          for selector in ["frontend", "application", "cachedb", "client"]:
            _RunKubectl(benchmark_spec, ['label', 'nodes', node, '{}-'.format(selector)], append_namespace=False, suppress_failure=True)

      nodes = _GetClusterWorkerNodes(benchmark_spec)
      _ClearNodeAssignments(benchmark_spec, nodes)
      if FLAGS.dsb_hotel_assign_nodes:
        total_node_count = len(nodes)
        client_node_count = FLAGS.dsb_hotel_client_nodes if FLAGS.dsb_hotel_clients_in_cluster else 0
        min_required_node_count = client_node_count + FLAGS.dsb_hotel_frontend_nodes + FLAGS.dsb_hotel_application_nodes + FLAGS.dsb_hotel_cachedb_nodes
        if min_required_node_count > total_node_count:
          raise errors.Benchmarks.PrepareException(f"Not enough nodes in cluster to assign application tiers to nodes. Have {total_node_count} nodes. Need at least {min_required_node_count} nodes.")
        unassigned_nodes = nodes
        for _ in range(client_node_count):
          _LabelClusterNode(benchmark_spec, unassigned_nodes[0], "client", "ok")
          unassigned_nodes.pop(0)
        for _ in range(FLAGS.dsb_hotel_frontend_nodes):
          _LabelClusterNode(benchmark_spec, unassigned_nodes[0], "frontend", "ok")
          unassigned_nodes.pop(0)
        for _ in range(FLAGS.dsb_hotel_application_nodes):
          _LabelClusterNode(benchmark_spec, unassigned_nodes[0], "application", "ok")
          unassigned_nodes.pop(0)
        for _ in range(FLAGS.dsb_hotel_cachedb_nodes):
          _LabelClusterNode(benchmark_spec, unassigned_nodes[0], "cachedb", "ok")
          unassigned_nodes.pop(0)
        if len(unassigned_nodes) > 0:
          logging.info(f"{len(unassigned_nodes)} nodes in the cluster will not be used.")

    def _TweakManifests():
      rootdir = os.path.join(vm_util.GetTempDir(), DSB_DIRECTORY, "hotelReservation", "openshift")
      deploydir = os.path.join(vm_util.GetTempDir(), 'deploy')
      vm_util.IssueCommand(['mkdir', '-p', deploydir])
      if FLAGS.dsb_hotel_clients_in_cluster:
        vm_util.IssueCommand(['cp', data.ResourcePath(os.path.join('dsb_hotel', 'extras', 'wrk2.yaml')), rootdir])
      for filename in glob.glob(os.path.join(rootdir, "*.yaml")):
        if 'hr-client' in filename:
          continue
        if 'persistentvolumeclaim' in filename:
          continue
        if 'jaeger-deployment' in filename and not FLAGS.dsb_hotel_deploy_jaeger:
          continue
        # tweak manifests as needed
        new_filename = os.path.join(deploydir, os.path.basename(filename))
        with open(filename) as original_file:
          txt = original_file.read()
          manifest = yaml.safe_load_all(txt)
          with open(new_filename, 'w') as new_file:
            new_docs = []
            for doc in manifest:
              # update namespace
              doc['metadata']['namespace'] = FLAGS.dsb_hotel_namespace
              if doc['kind'] == 'Service':
                # update service type
                if doc['metadata']['name'] in FRONTEND_SERVICES + TRACING_SERVICES_OUT:
                  doc['spec']['type'] = "LoadBalancer" if _IsManagedCluster() else "NodePort"
              if doc['kind'] == 'Deployment':
                # remove persistentvolumeclaim from mongodb deployments
                if "volumes" in doc["spec"]["template"]["spec"]:
                  if "persistentVolumeClaim" in doc["spec"]["template"]["spec"]["volumes"][0]:
                    del doc["spec"]["template"]["spec"]["volumes"][0]["persistentVolumeClaim"]
                    doc["spec"]["template"]["spec"]["volumes"][0]["emptyDir"] = {}
                # update image
                if doc['metadata']['name'] in APPLICATION_SERVICES + FRONTEND_SERVICES:
                  for container in doc['spec']['template']['spec']['containers']:
                    container['image'] = FLAGS.dsb_hotel_docker_image
                if FLAGS.dsb_hotel_image_cache:
                  # add cache path to image path
                  for container in doc['spec']['template']['spec']['containers']:
                    path = FLAGS.dsb_hotel_image_cache
                    if '/' not in container['image']:
                      path = path + 'library/'
                    container['image'] = path + container['image']
                doc['spec']['template']['spec']['nodeSelector'] = {}
                if FLAGS.dsb_hotel_node_label:
                  # add label as a nodeSelector so that pods will only be deployed to nodes with this label
                  key, value = FLAGS.dsb_hotel_node_label.split('=')
                  doc['spec']['template']['spec']['nodeSelector'][key] = value
                if FLAGS.dsb_hotel_assign_nodes:
                  # seperate service types across nodes using nodeSelector
                  if doc['metadata']['name'] in APPLICATION_SERVICES:
                    doc['spec']['template']['spec']['nodeSelector']['application'] = 'ok'
                  elif doc['metadata']['name'] in FRONTEND_SERVICES:
                    doc['spec']['template']['spec']['nodeSelector']['frontend'] = 'ok'
                  elif doc['metadata']['name'] in CACHEDB_SERVICES + TRACING_SERVICES:
                    doc['spec']['template']['spec']['nodeSelector']['cachedb'] = 'ok'
                  elif doc['metadata']['name'] in CLIENT_SERVICES:
                    doc['spec']['template']['spec']['nodeSelector']['client'] = 'ok'
              new_docs.append(doc)
            yaml.safe_dump_all(new_docs, new_file)

    _TeardownApplication(benchmark_spec)
    _ConfigureNodeSelectors(benchmark_spec)
    _TweakManifests()
    _DeployApplication(benchmark_spec)

  def _GetDeathStarBenchArchive():
    target_dir = os.path.join(vm_util.GetTempDir(), DSB_DIRECTORY)
    target_file = os.path.join(target_dir, DSB_ARCHIVE)
    vm_util.IssueCommand(["mkdir", "-p", target_dir])
    if FLAGS.dsb_hotel_dsb_archive.startswith("http"):
      vm_util.IssueCommand(["curl", "-L", "-o", target_file, FLAGS.dsb_hotel_dsb_archive])
    else:
      vm_util.IssueCommand(["cp", FLAGS.dsb_hotel_dsb_archive, target_file])
    vm_util.IssueCommand(["tar", "-xf", target_file, "--strip-components=1", "-C", target_dir])

  benchmark_spec.always_call_cleanup = True
  _GetDeathStarBenchArchive()
  _PrepareClients(_GetClients(benchmark_spec))
  _PrepareCluster(benchmark_spec)
  _SavePodConfig(benchmark_spec, "After Prepare")


def Run(benchmark_spec):
  results = []

  def _ParseWrkOutput(outputs, metadata):
    request_throughput = 0.0
    results_metadata = metadata.copy()
    percentile_pattern = re.compile(r"^\s*([0-9]{2,3}\.[0-9]{3}\%)\s*([0-9]+\.[0-9]*)(\w+)\s*$", flags=re.MULTILINE)
    counts_pattern = re.compile(r"^\s*([0-9]+)\s*requests\s*in\s([0-9]+\.[0-9]*)(\w),\s*([0-9]+\.[0-9]*)(\w+)\s*read$", flags=re.MULTILINE)
    errors_pattern = re.compile(r"^\s*Socket errors:\s*connect\s*([0-9]+),\s*read\s*([0-9]+),\s*write\s*([0-9]+),\s*timeout\s*([0-9]+)$", flags=re.MULTILINE)
    retcode_pattern = re.compile(r"^\s*Non-2xx or 3xx responses:\s*([0-9]+)$", flags=re.MULTILINE)
    requests_pattern = re.compile(r"^Requests/sec:\s*([0-9]*\.[0-9]*)$", flags=re.MULTILINE)
    for output in outputs:
      # percentiles
      def _MetadataPercentile(key, value, unit):
        """ record worst case for each percentile across all clients """
        v = value if unit == "ms" else value * 1000
        try:
          if v > results_metadata[key]:
            results_metadata[key] = v
        except KeyError:
          results_metadata[key] = v
      for match in percentile_pattern.finditer(output):
        _MetadataPercentile(match.group(1), float(match.group(2)), match.group(3))

      # counts
      def _MetadataCount(key, value):
        try:
          results_metadata[key] += value
        except KeyError:
          results_metadata[key] = value
      match = counts_pattern.search(output)
      _MetadataCount("request_count", int(match.group(1)))
      results_metadata["time"] = match.group(2) + match.group(3)  # don't aggregate
      # socket errors
      match = errors_pattern.search(output)
      _MetadataCount("connect_error_count", int(match.group(1)) if match else 0)
      _MetadataCount("read_error_count", int(match.group(2)) if match else 0)
      _MetadataCount("write_error_count", int(match.group(3)) if match else 0)
      _MetadataCount("timeout_error_count", int(match.group(4)) if match else 0)
      # http errors
      match = retcode_pattern.search(output)
      _MetadataCount("http_error_count", int(match.group(1)) if match else 0)
      # throughput in requests (primary metric of interest)
      match = requests_pattern.search(output)
      request_throughput += float(match.group(1))
    return sample.Sample("Request Throughput", request_throughput, "requests/sec", results_metadata)

  def _AutoScale(benchmark_spec, workload):
    """start with the min rate and scale up the rate until exit condition is met"""
    samples = []
    throughputs = []
    rate = FLAGS.dsb_hotel_client_rate or FLAGS.dsb_hotel_client_rate_autoscale_min
    max_error_rate_exceeded_count = 2
    error_rate_exceeded_count = 0
    iteration_sample = None

    while True:
      error_rate_exceeded = False

      def _RunOnClient(client, command):
        return client.RobustRemoteCommand(command, should_log=True)[0]

      def _RunOnCluster(benchmark_spec, pod, command):
        return _RunKubectl(benchmark_spec, ['exec', pod, "--"] + command.split(' '), timeout=FLAGS.dsb_hotel_client_duration + 10, force_info_log=True)[0]

      command_fmt = "{} -D exp -T {}s -t {} -c {} -d {} -L -s {} {} -R {}".format(
          "{}",
          FLAGS.dsb_hotel_client_timeout,
          _GetClientThreadCount(benchmark_spec),
          _GetClientConnectionCount(benchmark_spec),
          FLAGS.dsb_hotel_client_duration,
          "{}",
          "{}",
          rate)
      if FLAGS.dsb_hotel_clients_in_cluster:
        url = "http://{}:{}".format(_GetSvcIpAddress(benchmark_spec, "frontend"), WEB_FRONTEND_PORT)
        wrk2 = posixpath.join("socialNetwork", "wrk2", "wrk")
        script = posixpath.join("hotelReservation", "wrk2_lua_scripts", workload["script"])
        command = command_fmt.format(wrk2, script, url)
        client_outputs = vm_util.RunThreaded(_RunOnCluster, [((benchmark_spec, pod, command), {}) for pod in _GetWrk2Pods(benchmark_spec)])
      else:
        url = "http://{}:{}".format(_GetWebIpAddress(benchmark_spec, "frontend"), _GetWebPort(benchmark_spec, "frontend"))
        wrk2 = "./wrk"
        script = posixpath.join(WRK2_SCRIPTS_DIR, workload["script"])
        command = "cd {} && ".format(WRK2_DIR) + command_fmt.format(wrk2, script, url)
        client_outputs = vm_util.RunThreaded(_RunOnClient, [((client_vm, command), {}) for client_vm in _GetClients(benchmark_spec) for _ in range(FLAGS.dsb_hotel_client_instances_per_vm)])

      # record the state of the application
      _SavePodConfig(benchmark_spec, f"After collection with a client rate of {rate}")
      # parse the client output
      iteration_sample = _ParseWrkOutput(client_outputs,
                                         {'workload': workload["name"],
                                          'rate': rate,
                                          'rate_total': rate * len(_GetClients(benchmark_spec)) * FLAGS.dsb_hotel_client_instances_per_vm,
                                          'duration': FLAGS.dsb_hotel_client_duration,
                                          'connections': _GetClientConnectionCount(benchmark_spec),
                                          'connections_total': _GetTotalClientConnectionCount(benchmark_spec)}
                                         )
      # did the run exceed the allowable number of errors from the client?
      error_rate_exceeded = \
          iteration_sample.metadata["http_error_count"] + \
          iteration_sample.metadata["connect_error_count"] + \
          iteration_sample.metadata["read_error_count"] + \
          iteration_sample.metadata["write_error_count"] + \
          iteration_sample.metadata["connect_error_count"] \
          > iteration_sample.metadata["request_count"] * FLAGS.dsb_hotel_error_limit
      # was the SLA exceeded?
      sla_exceeded = iteration_sample.metadata["99.000%"] > FLAGS.dsb_hotel_p99_sla

      if error_rate_exceeded:
        error_rate_exceeded_count += 1
        logging.info("Error rate exceeded.")
        if error_rate_exceeded_count < max_error_rate_exceeded_count:
          logging.info("Try again at same rate ({})".format(rate))
      else:
        error_rate_exceeded_count = 0
        samples.append(iteration_sample)
        throughputs.append(iteration_sample.value)
        rate += FLAGS.dsb_hotel_client_rate_autoscale_increment

      # are we done?  check all conditions for exit.
      if autoscale_util.MeetsExitCriteria(throughputs):
        logging.info("Performance degrading. Terminating.")
        iteration_sample.metadata["Termination"] = "Performance degrading."
        break
      if FLAGS.dsb_hotel_p99_sla_only and sla_exceeded:
        logging.info("p99 SLA exceeded. Terminating.")
        iteration_sample.metadata["Termination"] = "p99 SLA exceeded."
        break
      if error_rate_exceeded_count == max_error_rate_exceeded_count:
        logging.info("Max retries on errors met. Terminating.")
        iteration_sample.metadata["Termination"] = "Max retries on errors met."
        break
      if FLAGS.dsb_hotel_client_rate_autoscale_max and rate > FLAGS.dsb_hotel_client_rate_autoscale_max:
        logging.info("Met user-specified maximum rate: {}. Terminating".format(FLAGS.dsb_hotel_client_rate_autoscale_max))
        iteration_sample.metadata["Termination"] = "Met user-specified maximum rate."
        break
      if FLAGS.dsb_hotel_client_rate:
        logging.info("User specified a single rate. Terminating.")
        iteration_sample.metadata["Termination"] = "User specified a single rate."
        break
      # reset the application in preparation for next iteration
      if not FLAGS.dsb_hotel_skip_teardown:
        _TeardownApplication(benchmark_spec)
        _DeployApplication(benchmark_spec)

    # find the max and max_sla throughputs
    throughput_samples = [s for s in samples if s.metric == "Request Throughput"]
    if throughput_samples:
      max_throughput = 0
      max_sla_throughput = 0
      max_sample = None
      max_sla_sample = None
      for ts in throughput_samples:
        if ts.value > max_throughput:
          max_throughput = ts.value
          max_sample = ts
        if ts.metadata["99.000%"] <= FLAGS.dsb_hotel_p99_sla and ts.value > max_sla_throughput:
          max_sla_throughput = ts.value
          max_sla_sample = ts
      if max_sample and not FLAGS.dsb_hotel_p99_sla_only:
        samples.append(sample.Sample("Maximum Throughput",
                                     max_sample.value, max_sample.unit, max_sample.metadata))
      if max_sla_sample:
        max_sla_metadata = max_sla_sample.metadata.copy()
        max_sla_metadata["p99 SLA (ms)"] = FLAGS.dsb_hotel_p99_sla
        samples.append(sample.Sample("Maximum Throughput with SLA",
                                     max_sla_sample.value, max_sla_sample.unit, max_sla_metadata))
    else:
      if not FLAGS.dsb_hotel_p99_sla_only:
        samples.append(sample.Sample("Maximum Throughput",
                                     0, "requests/sec", {'workload': workload["name"]}))
      samples.append(sample.Sample("Maximum Throughput with SLA",
                                   0, "requests/sec", {'workload': workload["name"], 'p99 SLA (ms)': FLAGS.dsb_hotel_p99_sla}))
    return samples

  # user may want to change replica counts between repeated 'run' requests at a specific
  # run rate, e.g. when using Adapative Optimization to drive the workload
  if len(FLAGS.run_stage) == 1:  # only the "run" run_stage was requested
    if FLAGS.dsb_hotel_client_rate is not None:  # a specific rate was specified (not auto-scaling)
      if not FLAGS.dsb_hotel_skip_teardown:
        _TeardownApplication(benchmark_spec)
      _DeployApplication(benchmark_spec)

  workloads = []
  if "mixed-workload_type_1" in FLAGS.dsb_hotel_workloads:
    workloads.append({"name": "mixed-workload_type_1",
                      "script": "mixed-workload_type_1.lua"})
  for workload in workloads:
    results.extend(_AutoScale(benchmark_spec, workload))

  return results


def Cleanup(benchmark_spec):
  _TeardownApplication(benchmark_spec)
