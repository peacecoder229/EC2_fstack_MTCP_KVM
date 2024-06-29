# widedeep benchmark

## How to run on AWS

- Runing on Ubuntu

```./pkb.py --cloud=AWS --benchmarks=widedeep --machine_type=m5.24xlarge --os_type=ubuntu1804```

- Runing on Centos

```./pkb.py --cloud=AWS --benchmarks=widedeep --machine_type=m5.24xlarge --os_type=centos7```

## widedeep specific flag values

### Benchmark flags values


- `widedeep_vcpu=[None]`: Number of virtual cpus to use. 
- `widedeep_run_mode=[default]`: Select default, custom, or optimize. 
- `widedeep_benchmark_mode=[benchmark-only]`: Select either benchmark-only or accuracy to use. 
- `widedeep_framework=[tensorflow-1.14.1]`: Version of tensorflow framework to use. 
- `widedeep_precision=[fp32]`: Inference precision to use. 
- `widedeep_batchsize=[1]`: Batch size to use. 
- `widedeep_intra_threads=[1]`: Number of intra-threads to use. 
- `widedeep_inter_threads=[1]`: Number of inter-threads to use. 
- `widedeep_omp_threads=[1]`: Number of omp threads to use. 

### Package flags values


- `widedeep_deps_ubuntu_tar_vm_group1_ver=[None]`: Version of tar package on "Ubuntu" OS
- `widedeep_deps_ubuntu_python_setuptools_vm_group1_ver=[None]`: Version of python-setuptools package on "Ubuntu" OS
- `widedeep_deps_ubuntu_numactl_vm_group1_ver=[None]`: Version of numactl package on "Ubuntu" OS
