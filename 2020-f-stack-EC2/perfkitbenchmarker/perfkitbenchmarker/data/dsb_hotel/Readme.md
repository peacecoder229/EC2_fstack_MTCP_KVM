# DeathStarBench Hotel Reservation (dsb_hotel) benchmark

## Foreward
The workload measures the performance of the Hotel Reservation workload from DeathStarBench
in a Kubernetes cluster.

## Running dsb_hotel with PKB
### Sample benchmark configuration files can be found in the same folder as the README
* dsb_hotel_cloud.yaml
* dsb_hotel_static.yaml

### Command line
```
./pkb.py --cloud=AWS --benchmarks=dsb_hotel --benchmark_config_file=dsb_hotel_cloud.yaml
```

### Details
Download or clone the repo. Checkout branch if not merged into master.

I'm not going to provide instructions on how to configure your system to run PKB here as there are better instructions elsewhere.
 
I assume you have a pre-configured Kubernetes cluster. You will need the kubeconfig file on your PKB machine. PKB uses kubectl to communicate with the cluster. It is useful to verify that the machine can communicate with the cluster before involving PKB. The workload attempts to pull Docker images through Intel's image cache server. This reduces or eliminates the number of pulls on Docker Hub. You may know that Docker Hub put limits on the number of pulls. Your cluster nodes need to be configured with an Intel certificate in order to trust Intel's image cache server. If you know how to do this, good, otherwise here is some information: Copy http://certificates.intel.com/repository/certificates/IntelSHA256RootCA-Base64.crt to the Ubuntu system certificate store (https://superuser.com/a/719047) and restart the docker daemon.
 
By default, the workload expects to have access to a client machine that resides outside of the cluster. The client machine needs to have a network path to the K8S cluster...preferably at least 10Gb. The client machine must be configured for password-less SSH and password-less sudo. This is a normal PKB requirement, not specific to DSB.

To view all the options available for running the workload:
- $ ./pkb.py --helpmatch dsb_hotel_benchmark
- There are MANY options. See them listed below. Don't let this discourage you. You can use the defaults to get started.

When run with default settings, the workload runs in a mode that scales the load via the client send rate -- meaning that the rate at which the client sends requests starts low (e.g., 500 req/s), then increments the rate by 100. It will keep going until the throughput declines two times in a row. It will then report the Maximum Throughput achieved and the Throughput under the P99 latency SLA of 30ms. This mode is useful to get an understanding of the performance given the current settings. When ready to collect telemetry, e.g. EMON, it is best to control the workload more directly, specifying a specific rate, duration, etc. This can be done through the workload flags defined below.

## Configuration Options

### Cluster / Machine Configuration
  --[no]dsb_hotel_clients_in_cluster: When True, client nodes will be allocated in the K8s cluster.
    (default: 'false')
  
  --dsb_hotel_client_nodes: Number of client nodes to provision. If dsb_hotel_clients_in_cluster is True, these will be provisioned as part of the cluster, otherwise they will be VMs).
    (default: '1')
    (a positive integer)
  
  --dsb_hotel_worker_nodes: Number of worker nodes to provision. Relevant only if using PKB to provision the cluster..
    (default: '1')
    (a positive integer)
  
  --[no]dsb_hotel_assign_nodes: When True, the frontend, bizlogic, and cache/database tiers will be assigned to specific nodes. The following three flags must be set to specify the number of nodes assigned to each tier.
    (default: 'false')
  
  --dsb_hotel_frontend_nodes: Number of worker nodes allocated to front end services. Only relevent when dsb_hotel_assign_nodes is True.
    (default: '1')
    (a positive integer)
  
  --dsb_hotel_application_nodes: Number of worker nodes allocated to application services. Only relevent when dsb_hotel_assign_nodes is True.
    (default: '1')
    (a positive integer)
  
  --dsb_hotel_cachedb_nodes: Number of worker nodes allocated to cache and database services. Only relevent when dsb_hotel_assign_nodes is True.
    (default: '1')
    (a positive integer)
  
### Replica Configuration
#### Use the replicas_override flag to use the same number of replicas for all replicable services
  --dsb_hotel_replicas_override: If greater than 0, this value will be used to set the number of replicas for all replicable services.
    (default: '0')
    (a non-negative integer)
#### Use the following flags if you want to set the number of replicas individually per service
  --dsb_hotel_frontend_replicas: The number of replicas for frontend.
    (default: '1')
    (a positive integer)

  --dsb_hotel_geo_replicas: The number of replicas for geo.
    (default: '1')
    (a positive integer)

  --dsb_hotel_profile_replicas: The number of replicas for profile.
    (default: '1')
    (a positive integer)

  --dsb_hotel_rate_replicas: The number of replicas for rate.
    (default: '1')
    (a positive integer)

  --dsb_hotel_recommendation_replicas: The number of replicas for recommendation.
    (default: '1')
    (a positive integer)

  --dsb_hotel_reservation_replicas: The number of replicas for reservation.
    (default: '1')
    (a positive integer)

  --dsb_hotel_search_replicas: The number of replicas for search.
    (default: '1')
    (a positive integer)

  --dsb_hotel_user_replicas: The number of replicas for user.
    (default: '1')
    (a positive integer)
    
  --dsb_hotel_wrk2_replicas: The number of replicas for wrk2.
    (default: '1')
    (a positive integer)

### Client Run Options
  --dsb_hotel_client_connections: Number of connections from each client to the application. None to set to num vCPUs on client machine (when dsb_hotel_clients_in_cluster is False), otherwise set to default value: 32.
    (default: None)
    (a positive integer)
  
  --dsb_hotel_client_duration: Number of seconds client(s) will make requests.
    (default: '60')
    (a positive integer)
  
  --dsb_hotel_client_instances_per_vm: Number of client process instances that will be run on each client machine. This only applies when
    dsb_hotel_clients_in_cluster is False.
    (default: '1')
    (a positive integer)
  
  --dsb_hotel_client_threads: Number of client threads. None to set to minimum of vCPUs on client and number of client connections (can't have more threads than connections).
    (default: None)
    (a positive integer)
  
  --dsb_hotel_client_timeout: Request timeout in seconds.
    (default: '5')
    (a positive integer)

### Client Rate and Rate Auto-Scaling Configuration
  --dsb_hotel_client_rate: Client requests per second. Setting this will disable client rate auto-scaling and run the given rate one time.
    (default: None)
    (a positive integer)
  
  --dsb_hotel_client_rate_autoscale_min: Client requests per second for first iteration when auto-scaling rate.
    (default: '500')
    (a positive integer)
  
  --dsb_hotel_client_rate_autoscale_increment: Client requests per second to increment between rate auto-scaling iterations.
    (default: '100')
    (a positive integer)
  
  --dsb_hotel_client_rate_autoscale_max: Client requests per second to short-circuit (exit) rate auto-scaling. None allows auto-scaling to continue until throughput decreases.
    (default: None)
    (a positive integer)

### Workload Options
  --dsb_hotel_namespace: The namespace that will be used by the hotel network K8s resources.
    (default: 'hotel-res')
  
  --dsb_hotel_dsb_archive: The URL or local path to the DeathStarBench repo archive file.
    (default: 'https://github.com/delimitrou/DeathStarBench/archive/master.tar.gz')
  
  --dsb_hotel_image_cache: Set the image cache server and path that Kubernetes/Docker will use to pull images. Set to empty string to pull from Docker Hub. If provided, string must end with forward slash.
    (default: 'amr-cache-registry.caas.intel.com/cache/')
  
  --dsb_hotel_docker_image: The docker image for hotel Network microservices.
    (default: 'cesgsw/dsb-hotel-reservation-microservices:v1.0')
  
  --dsb_hotel_node_label: A key/value that has been applied to cluster nodes to specify which nodes can be used for this application, e.g., 'project=hotel-reservation'.
    (default: None)
  
  --dsb_hotel_p99_sla: The P99 latency SLA in milliseconds. The maximum throughput found with the P99 <= this value will be reported.
    (default: '30')
    (an integer)
  
  --[no]dsb_hotel_p99_sla_only: Stop the workload when SLA is exceeded.
    (default: 'false')
  
  --dsb_hotel_error_limit: The fraction of transactions that are allowed to be errors. If this error rate is exceeded, the test will be terminated.
    (default: '0.05')
    (a number)
  
  --dsb_hotel_workloads: The workloads to run. One or more of mixed-workload_type_1.
    (default: 'mixed-workload_type_1')
    (a comma separated list)

  --[no]dsb_hotel_skip_teardown: When set to True, don't teardown the application between runs and/or iterations.
    (default: 'false')
  