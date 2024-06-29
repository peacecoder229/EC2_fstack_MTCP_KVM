# intel_python_django benchmark

## How to run on AWS

- Runing on Ubuntu

```./pkb.py --cloud=AWS --benchmarks=intel_python_django --machine_type=m5.24xlarge --os_type=ubuntu1804```

- Runing on Centos

```./pkb.py --cloud=AWS --benchmarks=intel_python_django --machine_type=m5.24xlarge --os_type=centos7```

## intel_python_django specific flag values

### Benchmark flags values

### Configuration flags


- `intel_python_django_version=[v1.1.1]`: The Python Django Workload version to be used. Cmd line parameter passed to the workload install script.
- `intel_python_django_webtier_version=[v1.0.4]`: The Webtier-provisioning version to be used. Cmd line parameter passed to the workload install script.
- `intel_python_django_https_enabled=[False]`: If True, Python Django will run using HTTPS. The default is False, defaulting to HTTP
- `intel_python_django_https_tls_version=[TLSv1.3]`: TLS version to be used by the workload with HTTPS mode. Default is TLSv1.3.
- `intel_python_django_https_cipher=[None]`: Cipher to be used by the workload with HTTPS mode. Only ciphers in TLSv1.2 can be specified.

### Tunable Flags


- `intel_python_django_run_count=[1]`: Number of times the WL is run. Default is 1.
- `intel_python_django_client_concurrency=[185]`: Number of Siege client workers. Default is 185.
- `intel_python_django_uwsgi_workers=[None]`: Number of uWSGI server workers. Default is equal to the number of vCPUs.

### Package flags values


- `intel_python_django_deps_ubuntu_ansible_vm_group1_ver=[None]`: Version of ansible package on "ubuntu1804" OS

