# facebook5 benchmark

## How to run on AWS

- Runing on Ubuntu

```./pkb.py --cloud=AWS --benchmarks=facebook5 --machine_type=m5.24xlarge --os_type=ubuntu1804```

- Runing on Centos

```./pkb.py --cloud=AWS --benchmarks=facebook5 --machine_type=m5.24xlarge --os_type=centos7```

## facebook5 specific flag values

### Benchmark flags values



### Package flags values


- `facebook5_deps_ubuntu_tar_vm_group1_ver=[None]`: Version of tar package on "Ubuntu" OS
- `facebook5_deps_ubuntu_python_setuptools_vm_group1_ver=[None]`: Version of python-setuptools package on "Ubuntu" OS
- `facebook5_deps_ubuntu_numactl_vm_group1_ver=[None]`: Version of numactl package on "Ubuntu" OS
