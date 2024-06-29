### Breaking changes:

### New features:

### Enhancements:
- Add support in Collectd ethstat to allow specifying interface wildcards and extend the Collectd interfaces list to cover more interface types (!268)
- Enhance framework to make it compatible with upstream regression tests, when running with both Python 2 and Python 3. (!287)
- Reverted fio, iperf and mongodb_ycsb to upstream and renamed aerospike and netperf to pass regression tests. (!277)
- Add intel_community to data directory (!291)

### Bug fixes and maintenance updates:
- Update Maven version to 3.6.3, last used version tarball is not available to be downloaded anymore. (!298)
- Add DEFAULT_USER_NAME=ubuntu for Ubuntu1904 in AWS, to override the default ec2-user AWS username. (!275)
- Fixed issue with empty metadata for Azure instances causing runs to fail (!278)
- Fixed missing explicit conversion in linux intel_hammerdb_benchmark (!276)
- Fixed CollectD build and run for Kubernetes provider (!281)
- Fixed a circular dependency issue in the automated generated code. (!282)
- Make output_dir logic more robust on auto-generated benchmarks. (!295)
- Eliminate trailing whitespaces and ensure correct yaml indentation on auto-generated benchmarks. (!294)
- Change Maven mirror. (!304)
