# mpich_compile_multi_node benchmark

## How to run on AWS

- Runing on Ubuntu

```./pkb.py --cloud=AWS --benchmarks=mpich_compile_multi_node --machine_type=m5.24xlarge --os_type=ubuntu1804```

- Runing on Centos

```./pkb.py --cloud=AWS --benchmarks=mpich_compile_multi_node --machine_type=m5.24xlarge --os_type=centos7```

## mpich_compile_multi_node specific flag values

### Benchmark flags values

### Configuration flags


- `mpich_compile_multi_node_cores=[None]`: number of cores
- `mpich_compile_multi_node_list_cfg=[[200]]`: description of list parameter
- `mpich_compile_multi_node_enum_cfg=[1810]`: description of enum parameter
- `mpich_compile_multi_node_version=[None]`: description of ver
- `mpich_compile_multi_node_hex_cfg=[None]`: description of hex parameter
- `mpich_compile_multi_node_float_cfg=[3.14]`: description of float parameter

### Tunable Flags



### Package flags values


- `mpich_compile_multi_node_deps_ubuntu_build_essential_head_node_ver=["12.1ubuntu2"]`: Version of build-essential package on "ubuntu1604" OS

- `mpich_compile_multi_node_deps_ubuntu_mpich_head_node_ver=["3.3"]`: Version of mpich package on "ubuntu1604" OS

- `mpich_compile_multi_node_deps_centos_wget_head_node_ver=["1.14-18.el7.x86_64"]`: Version of wget package on "centos7" OS

- `mpich_compile_multi_node_deps_centos_mpich_head_node_ver=["3.3"]`: Version of mpich package on "centos7" OS


- `mpich_compile_multi_node_deps_ubuntu_wget_compute_nodes_ver=[None]`: Version of wget package on "ubuntu1604" OS

- `mpich_compile_multi_node_deps_centos_wget_compute_nodes_ver=["1.14-18.el7.x86_64"]`: Version of wget package on "centos7" OS

