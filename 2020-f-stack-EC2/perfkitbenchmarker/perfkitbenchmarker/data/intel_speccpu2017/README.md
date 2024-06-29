## Intel SPEC cpu 2017 benchmark guideline

### Description

The SPEC CPU(R) 2017 benchmark package contains SPEC's next-generation, industry-standardized, CPU intensive suites for measuring and comparing compute intensive performance, stressing a system's processor, memory subsystem and compiler.

### Requirements

##### One-time steps to follow in order to get the workload running
1. On PKB host create a folder (e.g. mkdir speccpu2017)
2. Make sure the following resources are are copied in speccpu2017 folder that you just created (see table bellow to figure where to get these files):
    * SPEC cpu 2017 .ISO image file
    * tar archive package containing pre-compiled binaries for (gcc, icc and aocc)
3. Run PKB using  --data_search_paths=path/to/speccpu2017 flag to indicate the absolute path for your resources
 

### Command line examples

Run SPEC intrate throughput in AWS using icc 1.9 pre-compiled binaries:  
```
python pkb.py --cloud=AWS --benchmarks=intel_speccpu2017 --intel_spec17_runmode=SIR_TP_ICC19 --data_search_paths=path/to/ISOs/tars/yaml/and/script
```
Run SPEC intrate throughput on bare-metal using icc 1.9 pre-compiled binaries:
```
python pkb.py --benchmarks=intel_speccpu2017 --intel_spec17_runmode=SIR_TP_ICC19 --data_search_paths=path/to/ISOs/tars/yaml/and/script --benchmark_config_file=speccpu2017.yaml
```
Trigger customized run for SPEC single copy intrate throughput in AWS using icc 1.9 pre-compiled binaries 
```
python pkb.py --cloud=AWS --benchmarks=intel_speccpu2017 --intel_spec17_runmode=CUSTOM --data_search_paths=path/to/ISOs/tars/yaml/and/script --os_type=ubuntu1910  --intel_spec17_iso=cpu2017-1.1.0.iso  --intel_spec17_iso_sha256=55b014382d50b3e3867d2728066c2d20c7f993feeebf17ed13a30300621b97cc  --intel_spec17_tar=FOR-Intel-cpu2017-1.1.0-ic19.0.5.281-lin-binaries-20191015.tar.xz  --intel_spec17_tar_sha256=b8f841826e3c6de3f473dd821989d6d703fdf3f46ac45ade03b69068cb7b4917  --intel_spec17_config_file=ic19.0u5-lin-core-avx512-rate-20191015.cfg  --intel_spec17_action=validate  --intel_spec17_benchmark=intrate  --intel_spec17_iterations=1  --intel_spec17_runcpu_options=--nobuild  --intel_spec17_tuning=base  --intel_spec17_size=ref  --intel_spec17_define=default-platform-flags,smt-on,invoke_with_interleave,drop_caches
```
Trigger legacy run for SPEC intrate in AWS using icc 1.9 pre-compiled binaries using a runscript usually included inside the binaries talball
```
python pkb.py --cloud=AWS --benchmarks=intel_speccpu2017 --intel_spec17_runmode=CUSTOM --data_search_paths=path/to/ISOs/tars/yaml/and/script --os_type=ubuntu1910 --intel_spec17_runmode=CUSTOM --intel_spec17_tar=FOR-Intel-cpu2017-1.1.0-ic19.0.5.281-lin-binaries-20191015.tar.xz --intel_spec17_run_script=reportable-ic19.0u5-lin-core-avx512-rate-smt-on-20191015.sh 
```


**NOTES:**
* speccpu run script - SPECrate/speed 2017 Integer and SPECrate/speed 2017 Floating Point run scripts are included in the tarball if you need to change run option, place your customized script in speccpu2017 folder created on the PKB host.
* speccpu PKB config .yaml file - one can save complex execution scenarios of running SPEC cpu 2017 in PKB config file and use the file later to reproduce the results. When using  --data_search_paths flag in your command the .yaml needs to be placed as well in the speccpu2017 folder created on the PKB host. 
* above axamples will work for Ubuntu 19.04 or greater, check the resources sharedrive for older binaries packages that allow one to perform runs on older OS distros.



### Available flags
```
  --intel_spec17_runmode: <SIR_TP_ICC19|SIR_SC_ICC19|SFP_TP_ICC19|SFP_SC_ICC19|S
    IR_TP_GCC91|SIR_SC_GCC91|SFP_TP_GCC91|SFP_SC_GCC91|SIR_TP_AOCC20|SIR_SC_AOCC
    20|SFP_TP_AOCC20|SFP_SC_AOCC20|SIR_TP_GCC82|SIR_SC_GCC82|SFP_TP_GCC82|SFP_SC
    _GCC82|DEFAULT|CUSTOM>: Run mode to use. SIR=intrate, SFP=fprate,
    TP=throughput, SC=single copy.Run intrate single copy using icc 1.9 will be
    SIR_SC_ICC19 Defaults to None.
    (default: 'DEFAULT')

  --intel_spec17_tuning: <base|peak|base,peak>: Selects tuning to use: base,
    peak, or all. For a reportable run, must beeither base or all. Reportable
    runs do base first, then (optionally) peak.Defaults to base.

  --intel_spec17_benchmark: This will pass the workload to be ran, it can be one
    of the intrate, intspeed,fprate, fpspeed or all (e.g.
    --intel_spec17_benchmark="intrate fprate etc.") orjust a single benchmark
    from the suites for which --noreportable option will be added to the runcpu
    command

  --intel_spec17_config_file: Used by the PKB intel_speccpu2017 benchmark. Name
    of the cfg file to use asthe SPEC CPU config file provided to the runspec
    binary via its --config flag. By default this flag is null to allow usage of
    tarball included scripts

  --intel_spec17_copies: Number of copies to run for rate tests. If not set
    default to number of cpu coresusing lscpu.
    (an integer)

  --intel_spec17_define: Used by the PKB speccpu benchmarks. Optional comma-
    separated list of SYMBOL[=VALUE] preprocessor macros provided to the runspec
    binary via repeated --define option (e.g. numa,smt,sse=SSE4.2)

  --intel_spec17_iso: The speccpu2017 iso file.
    (default: 'cpu2017-1.1.0.iso')

  --intel_spec17_iso_sha256: sha256 hash for iso file

  --intel_spec17_iterations: Used by the PKB speccpu benchmarks. The number of
    benchmark iterations to execute, provided to the runspec binary via its
    --iterations flag.
    (an integer)

  --intel_spec17_run_script: The run script -- either already included in the
    tar or local. If local, itwill be copied to the target.

  --intel_spec17_runcpu_options: This will allow passing command options which
    are not already defined asa flag. Check a full list:
    https://www.spec.org/cpu2017/Docs/runcpu.html (e.g. -o all to output reports
    in all formats or --noreportable

  --intel_spec17_size: <test|train|ref>: Selects size of input data to run:
    test, train, or ref. The reference workload ("ref") is the only size whose
    time appears in reports.
    (default: 'ref')

  --intel_spec17_action: Used by the PKB speccpu benchmarks. If set, will append
    --action validateto runcpu command. Check this page for a full list of
    available options:https://www.spec.org/cpu2017/Docs/runcpu.html#action
    (default: 'validate')

  --intel_spec17_tar: Pre-built tar file containing binaries that will be
    extracted over the topof a directory of files created by running the spec17
    install.sh script   from the mounted iso.

  --intel_spec17_tar_sha256: sha256 for tar file

  --intel_spec17_threads: Number of threads to run for speed tests. If not set
    default to number of cpu threads using lscpu.
    (an integer)

```

### Available resources

Most recent resources / pre-requirements

| Resource | Description | Source |
|----------|-------------|--------|
|FOR-Intel-cpu2017-1.1.0-ic19.0.5.281-lin-binaries-20191015.tar.xz	|Best Intel (Intel Compiler binaries)	|\\\cloudpeca002.fm.intel.com\Infrastructure\Binaries\SPEC.CPU2017.FOR.INTEL\1.1.0\|
|FOR-Intel-Internal_only-cpu2017-aocc2.0-lin-baserateonly-binaries-20191115.tar.xz	|Best AMD (aocc1.3 compiler binaries)	|\\\cloudpeca002.fm.intel.com\Infrastructure\Binaries\SPEC.CPU2017.FOR.INTEL\1.1.0\|
|FOR-INTEL-cpu2017-1.0.5-gcc8.2.0-lin-O2-binaries-20181022.tar.xz	|GCC O2 optimized binaries	|\\\cloudpeca002.fm.intel.com\Infrastructure\Binaries\SPEC.CPU2017.FOR.INTEL\1.0.5\|
|FOR-INTEL-cpu2017-1.1.0-aarch64-gcc9.1.0-binaries-20181218.tar.xz	|ARM GCC 9.1 binaries	|\\\cloudpeca002.fm.intel.com\Infrastructure\Binaries\SPEC.CPU2017.FOR.INTEL\1.1.0\|
|cpu2017-1.0.5.iso	|SPEC cpu 2017 ver. 1.0.5 benchmark ISO	|\\\cloudpeca002.fm.intel.com\Infrastructure\Binaries\SPEC.CPU.2017|
|cpu2017-1.1.0.iso	|SPEC cpu 2017 ver. 1.1.0 benchmark ISO	|\\\cloudpeca002.fm.intel.com\Infrastructure\Binaries\SPEC.CPU.2017|
|reportable-ic19.0u4-lin-core-avx2-rate-smt-on-20190416.sh |speccpu Intel trigger script for ICC compiled binaries |can be found in the associated tarball|
|reportable-ic19.0u4-lin-core-avx512-rate-smt-on-20190416.sh |speccpu Intel trigger script for ICC compiled binaries |can be found in the associated tarball|
|reportable-ic19.0u4-lin-generic-avx2-rate-smt-on-20190416.sh |speccpu AMD trigger script for ICC tarball |can be found in the associated tarball|
|lab-reportable-aocc1.3-naples-gfortran.sh |speccpu AMD trigger script for aocc tarball |can be found in the associated tarball|


### Config file examples

speccpu2017.yaml:
```
## executor
###############################################################################
static_vms:
  - &SUT1
      os_type: ubuntu1804
      ip_address: <SUT1_IP_address>
      user_name: <SUT1_user>
      ssh_private_key: ~/.ssh/id_rsa
      internal_ip: <SUT1_IP_address>
      disk_specs:
        - mount_point: /home/<SUT1_user>

## benchmark
###############################################################################
intel_speccpu2017: {description: "Running intel_speccpu2017 on bare-metal",
                    name: intel_speccpu2017,
                    vm_groups: {default: {static_vms: [*SUT1]}},
                    flags: {http_proxy: 'http://proxy-chain.intel.com:911',
                            https_proxy: 'http://proxy-chain.intel.com:912'}}

```
**NOTE:**

Replace "<SUT1_user>" according to your environment. 

More config files [here](https://gitlab.devtools.intel.com/cumulus/cumulus_scripts/tree/master/PKB_config_files/intel_speccpu2017) 

### Benchmark specifics

SPEC CPU2017 has 43 benchmarks, organized into 4 suites:

 SPECrate 2017 Integer            SPECspeed 2017 Integer
 SPECrate 2017 Floating Point     SPECspeed 2017 Floating Point

Benchmark pairs shown as:

 5nn.benchmark_r / 6nn.benchmark_s

are similar to each other. Differences include: compile flags; workload sizes; and run rules. See: [OpenMP]   [memory]   [rules]

More [information on the wiki](https://wiki.ith.intel.com/display/cloudperf/SPECcpu2017+workload+guidance)