## Intel FIO (Flexible I/O tester) benchmark guidelines

### Description

FIO (Flexible I/O tester) is a tool that will spawn a number of threads or processes doing a particular type of I/O action as specified by the user. The typical use of fio is to write a job file matching the I/O load one wants to simulate. See official documentation here.

### Command line examples

Run on AWS
```
python pkb.py --cloud=AWS --benchmarks=intel_fio --machine_type=m5.2xlarge
```
Run on-prem
```
python pkb.py --benchmarks=intel_fio_static --benchmark_config_file=fio_static_machine.yaml
```
Clear Linux AWS
```
# Uses Clear Linux AMI submitted to the marketplace by the Clear Linux team for us-east-1. Use ami-019a46e59b0a02646 for us-west-2.
python pkb.py --cloud=AWS --benchmarks=intel_fio --machine_type=t2.large --os_type=clear --aws_boot_disk_size=25 --image=ami-032138b8a0ee244c9
```
Striping NVMe Example on AWS
```
# Uses AWS and apply RAID0 striping across the four local NVMe drives using num_striped_disk option
python pkb.py --cloud=AWS --benchmarks=intel_fio --machine_type=m5d.24xlarge --zones=us-east-1c --intel_fio_jobfile=fio_apollo.job --num_striped_disks=4
```

### Available flags
```
 --intel_fio_version: Flexible I/O version that will be checked out and built.
   (default: '3.18')
   
 --intel_fio_repository: Repository used to pull the FIO benchmark source code.
   (default: 'https://github.com/axboe/fio.git')
 
 --intel_fio_jobfile: Job file that fio will use. If not given, use a job file
   bundled with PKB. Cannot use with --intel_fio_generate_scenarios.
 
 --intel_fio_runtime: The number of seconds to run each fio job for.
   (default: '600')
   (a positive integer)
   
 --[no]intel_fio_bw_log: Whether to collect a bandwidth log of the fio jobs.
   (default: 'false')
 
 --intel_fio_command_timeout_sec: Timeout for fio commands in seconds.
   (an integer)
 
 --intel_fio_fill_size: The amount of device to fill in prepare stage. The
   valid value can either be an integer, which represents the number of bytes
   to fill or a percentage, which represents the percentage of the device. A
   filesystem will be unmounted before filling and remounted afterwards. Only
   valid when --intel_fio_target_mode is against_device_with_fill or
   against_file_with_fill.
   (default: '100%')
 
 --intel_fio_generate_scenarios: Generate a job file with the given scenarios.
   Special scenario 'all' generates all scenarios. Available scenarios are
   sequential_write, sequential_read, random_write, and random_read. Cannot use
   with --intel_fio_jobfile.
   (default: '')
   (a comma separated list)
 
 --[no]intel_fio_hist_log: Whether to collect clat histogram.
   (default: 'false')
 
 --intel_fio_io_depths: IO queue depths to run on. Can specify a single number,
   like --intel_fio_io_depths=1, a range, like --intel_fio_io_depths=1-4, or a
   list, like --intel_fio_io_depths=1-4,6-8
   (default: '1')
   (A comma-separated list of integers or integer ranges. Ex: -1,3,5:7 is read
   as -1,3,5,6,7.)
 
 --[no]intel_fio_iops_log: Whether to collect an IOPS log of the fio jobs.
   (default: 'false')
  
 --[no]intel_fio_lat_log: Whether to collect a latency log of the fio jobs.
   (default: 'false')
 
 --intel_fio_log_avg_msec: By default, this will average each log entry in the
   fio latency, bandwidth, and iops logs over the specified period of time in
   milliseconds. If set to 0, fio will log an entry for every IO that
   completes, this can grow very quickly in size and can cause performance
   overhead.
   (default: '1000')
   (a non-negative integer)
 
 --intel_fio_log_hist_msec: Same as fio_log_avg_msec, but logs entries for
   completion latency histograms. If set to 0, histogram logging is disabled.
   (default: '1000')
   (an integer)
 
 --intel_fio_num_jobs: Number of concurrent fio jobs to run.
   (default: '1')
   (A comma-separated list of integers or integer ranges. Ex: -1,3,5:7 is read
   as -1,3,5,6,7.)
 
 --intel_fio_parameters: Parameters to apply to all PKB generated fio jobs.
   Each member of the list should be of the form "param=value".
   (default: 'randrepeat=0')
   (a comma separated list)
    
 --intel_fio_target_mode: <against_device_with_fill|against_device_without_fill
   |against_file_with_fill|against_file_without_fill>: Whether to run against a
   raw device or a file, and whether to prefill.
   (default: 'against_file_without_fill')
 
 --intel_fio_working_set_size: The size of the working set, in GB. If not
   given, use the full size of the device. If using
   --intel_fio_generate_scenarios and not running against a raw device, you
   must pass --intel_fio_working_set_size.
   (a non-negative integer)
 
 --[no]intel_fio_write_against_multiple_clients: Whether to run fio against
   multiple nfs. Only applicable when running fio against network mounts and
   rw=write.
   (default: 'false')
```

### Configuration file example 

intel_fio_static_machine.yaml:
```
static_vms:
  - &vm0
    ip_address: <SUT_ip_address>
    user_name: <SUT_user_name>
    ssh_private_key: /path/to/PKB_host_private_key
    internal_ip: <SUT_ip_address>
    disk_specs:
      - mount_point: /home/<SUT_user_name>/
intel_fio_static:
  name: fio
  vm_groups:
    default:
      static_vms:
        - *vm0
```
[More config files](https://gitlab.devtools.intel.com/cumulus/cumulus_scripts/blob/master/PKB_config_files/intel_fio)
