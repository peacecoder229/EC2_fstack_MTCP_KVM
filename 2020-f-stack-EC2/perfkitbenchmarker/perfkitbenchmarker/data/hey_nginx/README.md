# Hey NGINX benchmark

## Foreward
The workload measures the performance of the NGINX web server configured with LuaJIT and Brotli.

## Running hey_nginx with PKB
### Sample benchmark configuration files 
* hey_nginx_cloud.yaml
* hey_nginx_static.yaml

### Command line
```
./pkb.py --cloud=AWS --benchmarks=hey_nginx --benchmark_config_file=hey_nginx_cloud.yaml
```

### Configuration
* hey_nginx_client_vms: the number of client machines running the 'hey' process that generate load on the server
* hey_nginx_requests_per_client: the number of HTTP requests each client process should make to the server
* hey_nginx_threads_per_client: the number of threads each client process should use to make requests
* hey_nginx_nginx: the nginx implementation to use, currently either openresty or intel_nginx

Note: The intel_nginx implementation is optimized for Intel Architecture.

