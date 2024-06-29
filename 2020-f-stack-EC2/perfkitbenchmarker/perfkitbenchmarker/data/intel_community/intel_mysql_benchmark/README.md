# intel_mysql benchmark

## How to run on AWS

- Runing on Ubuntu

```./pkb.py --cloud=AWS --benchmarks=intel_mysql --machine_type=m5.24xlarge --os_type=ubuntu1804```

- Runing on Centos

```./pkb.py --cloud=AWS --benchmarks=intel_mysql --machine_type=m5.24xlarge --os_type=centos7```

## intel_mysql specific flag values

### Benchmark flags values

### Configuration flags


- `intel_mysql_host=[127.0.0.1]`: IP address of Mysql server listen 
- `intel_mysql_port=[6306]`: Port of Mysql server listen 
- `intel_mysql_tag=[intel]`: tag for the log
- `intel_mysql_install_path=[/opt/pkb/]`: The path Mysql installed

### Tunable Flags


- `intel_mysql_thread_count_start=[100]`: The min thread num for the Sysbench
- `intel_mysql_thread_count_step=[100]`: The step to increase thread_count_start
- `intel_mysql_thread_count_end=[1000]`: The max thread num for the Sysbench
- `intel_mysql_testtype=[ps]`: Test type for the Sysbench,ps:only search, rw:read and write
- `intel_mysql_sysbench_table_size=[2000000]`: The number of rows of each table used in the oltp tests
- `intel_mysql_sysbench_tables=[10]`: The number of tables used in sysbench oltp.lua tests
- `intel_mysql_sysbench_duration=[120]`: The duration of the actual run in seconds
- `intel_mysql_sysbench_latency_percentile=[99]`: The latency percentile we ask sysbench to compute
- `intel_mysql_sysbench_report_interval=[10]`: The interval in seconds that we ask sysbench to report results

### Package flags values


- `intel_mysql_deps_centos_mysql_vm_group1_ver=["5.7.22"]`: Version of mysql package on "centos7" OS

- `intel_mysql_deps_centos_sysbench_vm_group1_ver=["1.1.0"]`: Version of sysbench package on "centos7" OS

- `intel_mysql_deps_ubuntu_mysql_vm_group1_ver=["5.7.22"]`: Version of mysql package on "ubuntu1804" OS

- `intel_mysql_deps_ubuntu_sysbench_vm_group1_ver=["1.1.0"]`: Version of sysbench package on "ubuntu1804" OS

