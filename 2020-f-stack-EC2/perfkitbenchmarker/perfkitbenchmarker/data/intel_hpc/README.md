# HPC Workloads in Cumulus

TOPICS :-

1. [Workloads in HPC ](#workloads-in-hpc)
2. [Commands to run workloads on Cloud Service Providers](#commands-to-run-workloads-on-csp)
3. [Commands to run workloads on On-prem systems](#commands-to-run-workloads-on-on-prem-systems)
4. [HPC Container Image Versioning](#hpc-container-image-versioning)
5. [HPC Multinode Support](#hpc-multinode-support)
6. [Cluster Checker Support](#cluster-checker-support)
7. [AWS High Performanece Fabric(EFA) Support](#aws-efa-support)
8. [AWS High Performance File Storage(FSX) Support](#aws-fsx-support)
9. [HPC - head_node - Custom Image for AWS and Azure ](#hpc-Head_node-custom-image-for-aws-and-azure)
10. [Flags used for HPC workloads](#flags-used-for-hpc-workloads)


## Workloads in HPC 

Following are the list of HPC workloads supported in Cumulus :-

1. Lammps
2. Gromacs
3. Openfoam
4. ComputeBenches ( HPL, HPCG, SGEMM, DGEMM )
5. WRF
6. NAMD
7. MonteCarlo (Tested on IA only)
8. Blacksholes (Tested on IA only)
9. BinomialOptions (Tested on IA only)
```
Current Status of HPC Workloads

  a. Single Node is supported for all workloads on Intel and AMD systems on AWS,GCP,Azure and Tencent
  b. Multi Node is supported and tested for AWS and GCP for the following workloads :-
     1. Lammps
     2. Gromacs
     3. NAMD
     4. Openfoam
```

## Commands to run workloads on CSP 

### On IA - avx512 images

1. Lammps :-

Run on AWS 

```
./pkb.py --cloud=AWS --benchmarks=intel_hpc_lammps --zone=us-east-1 --svrinfo --collectd --kafka_publish --owner=pdevaraj
```

Run on Azure 

```
./pkb.py --cloud=Azure --benchmarks=intel_hpc_lammps --machine_type=Standard_HC44rs --zone=westus2  --svrinfo --collectd --kafka_publish --owner=pdevaraj
```

2. Gromacs :-

Run on AWS :-

```
./pkb.py --cloud=AWS --benchmarks=intel_hpc_gromacs --zone=us-east-1  --svrinfo --collectd --kafka_publish --owner=pdevaraj  

```

Run on Azure 

```
./pkb.py --cloud=Azure --benchmarks=intel_hpc_gromacs --machine_type=Standard_HC44rs --zone=westus2  --svrinfo --collectd --kafka_publish --owner=pdevaraj

```

3. Openfoam :-

Run on AWS :-

```
./pkb.py --cloud=AWS --benchmarks=intel_hpc_openfoam --zone=us-east-1  --svrinfo --collectd --kafka_publish --owner=pdevaraj  

```

Run on Azure 

```
./pkb.py --cloud=Azure --benchmarks=intel_hpc_openfoam --machine_type=Standard_HC44rs --zone=westus2  --svrinfo --collectd --kafka_publish --owner=pdevaraj

```

4. ComputeBenches :-

Run on AWS :-

```
./pkb.py --cloud=AWS --benchmarks=intel_hpc_computebenches --zone=us-east-1  --svrinfo --collectd --kafka_publish --owner=pdevaraj  

```

Run on Azure 

```
./pkb.py --cloud=Azure --benchmarks=intel_hpc_openfoam --machine_type=Standard_HC44rs --zone=westus2  --svrinfo --collectd --kafka_publish --owner=pdevaraj

```

5. WRF :-

Run on AWS :-

```
./pkb.py --cloud=AWS --benchmarks=intel_hpc_wrf --zone=us-east-1  --svrinfo --collectd --kafka_publish --owner=pdevaraj  
```

Run on Azure 

```
./pkb.py --cloud=Azure --benchmarks=intel_hpc_wrf --machine_type=Standard_HC44rs --zone=westus2  --svrinfo --collectd --kafka_publish --owner=pdevaraj

```

6. NAMD :-

Run on AWS :-

```
./pkb.py --cloud=AWS --benchmarks=intel_hpc_namd --zone=us-east-1  --svrinfo --collectd --kafka_publish --owner=pdevaraj  
```

Run on Azure 

```
./pkb.py --cloud=Azure --benchmarks=intel_hpc_namd --machine_type=Standard_HC44rs --zone=westus2  --svrinfo --collectd --kafka_publish --owner=pdevaraj

```

7. MonteCarlo (Tested on IA only):-

Run on AWS :-

```
./pkb.py --cloud=AWS --benchmarks=intel_hpc_montecarlo --machine_type=c5.9xlarge  --zone=us-east-1  --svrinfo  --collectd --kafka_publish --owner=pdevaraj

```

Run on Azure :-

```
./pkb.py --cloud=Azure --benchmarks=intel_hpc_montecarlo --machine_type=Standard_E8s_v3  --svrinfo  --collectd --kafka_publish --owner=pdevaraj

```

Run on GCP :-

```
./pkb.py --cloud=GCP --benchmarks=intel_hpc_montecarlo --machine_type=n2-standard-16 --svrinfo --collectd --kafka_publish --owner=pdevaraj

```

8. Blacksholes (Tested on IA only):-

Run on AWS :-

```
./pkb.py --cloud=AWS --benchmarks=intel_hpc_blacksholes  --machine_type=c5.9xlarge  --zone=us-east-1  --svrinfo  --collectd --kafka_publish --owner=pdevaraj
```

Run on Azure :-

```
./pkb.py --cloud=Azure --benchmarks=intel_hpc_blacksholes  --machine_type=Standard_E8s_v3  --svrinfo  --collectd --kafka_publish --owner=pdevaraj
```

Run on GCP :-

```
./pkb.py --cloud=GCP --benchmarks=intel_hpc_blacksholes  --machine_type=n2-standard-16 --svrinfo --collectd --kafka_publish --owner=pdevaraj

```

9. BinomialOptions (Tested on IA only):-

Run on AWS :-

```
./pkb.py --cloud=AWS --benchmarks=intel_hpc_binomialoptions  --machine_type=c5.9xlarge  --zone=us-east-1  --svrinfo  --collectd --kafka_publish --owner=pdevaraj
```

Run on Azure :-

```
./pkb.py --cloud=Azure --benchmarks=intel_hpc_binomialoptions  --machine_type=Standard_E64s_v3  --svrinfo  --collectd --kafka_publish --owner=pdevaraj
```

Run on GCP :-

```
./pkb.py --cloud=GCP --benchmarks=intel_hpc_binomialoptions  --machine_type=n2-standard-16 --svrinfo --collectd --kafka_publish --owner=pdevaraj

```


### Commands to run workloads on On prem systems

```
./pkb.py --benchmarks=intel_hpc_lammps --benchmark_config_file=lammps.yml --svrinfo --collectd --kafka_publish --owner=pdevaraj

```

Shown below is an example of bare metal config file for Lammps.

```
static_vms:
  - &vm0
    ip_address: 10.x.x.x
    user_name: pkb
    ssh_private_key: ~/.ssh/id_rsa
    internal_ip: 10.x.x.x
    os_type: rhel
    disk_specs:
      - mount_point: /home/pkb/
  - &vm1
    ip_address: 10.x.x.x
    user_name: pkb
    ssh_private_key: ~/.ssh/id_rsa
    internal_ip: 10.x.x.x
    os_type: rhel
    disk_specs:
      - mount_point: /home/pkb/
 
  - &vm2
    ip_address: 10.x.x.x
    user_name: pkb
    ssh_private_key: ~/.ssh/id_rsa
    internal_ip: 10.x.x.x
    os_type: rhel
    disk_specs:
      - mount_point: /home/pkb/
 
 
intel_hpc_lammps:
  vm_groups:
    head_node:
      static_vms:
        - *vm0
    compute_nodes:
      static_vms:
        - *vm1
        - *vm2
```

### For Runs on AMD :-

add intel_hpc_<workload name>_image_type='amd'

Run on Azure  - Lammps 

```
./pkb.py --cloud=Azure --benchmarks=intel_hpc_lammps --machine_type=Standard_HB120rs_v2  --zone=southcentralus  --intel_hpc_lammps_image_type='amd' --svrinfo --collectd --kafka_publish --owner=pdevaraj
```


## HPC Container Image Versioning

All HPC workload container images are now versioned.

Please read the instructions below before running the workloads :-

### Default Run - Latest Images

All the latest container images will be maintained on Amazon S3 and are public within Intel.

This will be the image that will be run by default if no custom options are given by the user.

### Custom Images

If the user wishes to run previous images, they are maintained on a separate server by the HPC team.

It is the user's responsibility to copy the image from the HPC server to their PKB host before running this custom image.

### Access to HPC Server

In order to get access to this server, please get the permission and credentials by sending an email to

```
Tim Mefford < tim.mefford@intel.com >

Smahane Douyeb < smahane.douyeb@intel.com>
```

Once you have access to the server copy the image from the server to the PKB host.

**Important Flags**

```
Image Name :- 
This is an example of the name of the HPC container images

lammps.avx512.2a71919412e817e86fbc00f46ff1cdb3aa33835d.simg
[Workload] . [Image Type] . [Image Version] . simg

```

```
--intel_hpc_<workload name>_image_type

for eg:- intel_hpc_lammps_image_type

This flags is used to represent format of container images.
Values are
* 'avx512'  for IA
* 'amd' for AMD

Default value is avx512
```

```
--intel_hpc_<workload name>_image_version

for eg :- intel_hpc_lammps_image_version

This flag is used to represent the version of HPC container images.

Defaut Value - Mar2020 
These are the latest images as of March 2020.
```

```
--data_search_paths

If this flag is mentioned, the user has to download the HPC containers before starting the workload.
The location of the containers must be passed to this flag.

```

## HPC Multinode Support

Given below are commands to run these workloads on TCP fabric on HPC.
AWS and Azure support high performance fabrics.
In this release EFA on AWS is supported by the workloads below.
Please goto AWS-EFA-Support below for these commands.

### On IA - avx512 images

1. Lammps :-

Run on AWS

```
./pkb.py --cloud=AWS --benchmarks=intel_hpc_lammps --zone=us-east-1  --intel_hpc_lammps_nodes=2  --kafka_publish --owner=pdevaraj
```

Run on GCP

```
./pkb.py --cloud=GCP --machine_type=c2-standard-60 --benchmarks=intel_hpc_lammps --intel_hpc_lammps_nodes=2  --zones=us-east1-b --kafka_publish --owner=pdevaraj
```

2. Gromacs :-

Run on AWS :-

```
./pkb.py --cloud=AWS --benchmarks=intel_hpc_gromacs --intel_hpc_gromacs_nodes=2 --zone=us-east-1 --kafka_publish --owner=pdevaraj

```

Run on GCP

```
./pkb.py --cloud=GCP --machine_type=c2-standard-60 --benchmarks=intel_hpc_gromacs --intel_hpc_gromacs_nodes=2  --zones=us-east1-b --kafka_publish --owner=pdevaraj
```

3. NAMD :-

Run on AWS :-

```
./pkb.py --cloud=AWS --benchmarks=intel_hpc_namd --intel_hpc_namd_nodes=2  --zone=us-east-1  --kafka_publish --owner=pdevaraj
```

Run on GCP

```
./pkb.py --cloud=GCP --machine_type=c2-standard-60 --benchmarks=intel_hpc_namd --intel_hpc_namd_nodes=2  --zones=us-east1-b  --kafka_publish --owner=pdevaraj
```

## Cluster Checker Support

When we setup HPC clusters, it is good to make sure that they are compliant with Intel HPC Platform Specificaitons.
Cluster Checker is a tool used to verify the compute, network, storage, memory on a cluster setup and ensure that it is configured to run parallel applications.

By default the CC is disabled. The user can enable it by using the flag :-

--intel_hpc_<workload_name>_CC=True

You can enable Cluster checker for any of your MultiNode runs.

For eg:-

```
./pkb.py --cloud=AWS --benchmarks=intel_hpc_lammps --intel_hpc_lammps_nodes=2  --intel_hpc_lammps_CC=True   --zone=us-east-1  --kafka_publish --owner=pdevaraj
```

Cluster checker has been tested on AWS (upto 16 nodes) , Azure(Upto 4 nodes) and GCP(Upto 8 nodes)
More tests are in progress and we are restricted by resource availabilty.

When you use this flag,
1. All the packages necessary for CC will be installed.
2. Cluster Checker runs multiple tests to ensure that the cluster setup is good
3. It will display the results of these tests on your console.
4. If there is a failure, please refer to the pkb.log.


## AWS EFA Support

On AWS, a high performance fabric called EFA(Elastic Fabric Adapter) is available.
This gives better performance results over the usage of TCP fabric.

By using the flags :-

--aws_efa=True
--aws_efa_version=1.8.4

you can get the EFA support for your systems.

```
Note :- EFA support from AWS is avaiable only on very few systems. c5n.18xlarge, c5n.metal have been used for HPC testing
```

Eg:-

```
./pkb.py --cloud=AWS --benchmarks=intel_hpc_lammps --intel_hpc_lammps_nodes=2 --zone=us-east-1 --machine_type=c5n.18xlarge --aws_efa=True --aws_efa_version=1.8.4 --kafka_publish --owner=pdevaraj
```

## AWS FSX Support

AWS supports the usage of Lustre file storage systems with the use of AWS FSX APIs. With FSX it is very easy to install, use and remove Lustre storage systems.

By using the flag:

--intel_hpc_<workload_name>_fss_type='FSX'

you can enable FSX storage.

If you dont choose FSX, NFS is used by default.

Eg:-

```
./pkb.py --cloud=AWS --benchmarks=intel_hpc_lammps --intel_hpc_lammps_nodes=2 --zone=us-east-1 --intel_hpc_lammps_fss_type=FSX  --machine_type=c5n.18xlarge  --kafka_publish --owner=pdevaraj
```


## HPC - Head_node - Custom Image for AWS, Azure and GCP

We have created a provision for the user to create a custom image which has all the packages needed for HPC workload execution.

RootCause :-
* The installation of the packages for HPC consumes a lot of time.
* There is a set of packages which needs to be installed on every node in the HPC cluster.

Solution:-
* We have come up with a solution which is the head_node image for HPC.
* We have a head_node benchmark (intel_hpc_head_node_benchmark.py) which can be run on the CSP which is purely for package installation.

*At the end of the run, you get an AWS / Azure / GCP image id which is your custom image.

*This custom image can then be used to run all the HPC workloads.
*This works for Single Node as well as Multi Node.

### On AWS

The run will now consists of two steps :-

A.Run the intel_hpc_head_node_benchmark.py and create your custom image

```
./pkb.py --cloud=AWS --benchmarks=intel_hpc_head_node --zones=us-east-2 --owner=pdevaraj"

```
The output of the above command will be an AWS AMI , lets call it  **HPC_Custom_Image**

B.We will now pass this new image as a parameter in --image to run all the HPC workloads

**Except for the --image parameter nothing else will change in the commands to run the workloads**

SN Run:-

```
./pkb.py --cloud=AWS --benchmarks=intel_hpc_lammps --zone=us-east-1  --image="<HPC_Custom_Image>" --svrinfo --collectd --kafka_publish --owner=pdevaraj
```

MN Run:-

```
./pkb.py --cloud=AWS --benchmarks=intel_hpc_lammps --intel_hpc_lammps_nodes=2 --zone=us-east-1  --image="<HPC_Custom_Image>" --kafka_publish --owner=pdevaraj
```

### On Azure

The run will now consists of two steps :-

A.Run the intel_hpc_head_node_benchmark.py and create your custom image

```
./pkb.py --cloud=Azure --benchmarks=intel_hpc_head_node --machine_type=Standard_HC44rs --zone=westus2

```
The output of the above command will be an Azure image id  , lets call it  **HPC_Custom_Image**

Note :- On Azure, if you have to create an image you have to be disconnected from the system from which your image is being generated.
        So this run will generate an image and output it but the PKB run will show "Failed status" because we are disconnected from the system.
        Please use the image name from here and ignore the failure.


B.We will now pass this new image as a parameter in --image to run all the HPC workloads

**Except for the --image parameter nothing else will change in the commands to run the workloads**

SN Run:-
```
./pkb.py --cloud=Azure --benchmarks=intel_hpc_lammps --machine_type=Standard_HC44rs --zone=westus2  --image="<HPC_Custom_Image>" --svrinfo --collectd --kafka_publish --owner=pdevaraj
```

MN Run:-
```
/pkb.py --cloud=Azure --benchmarks=intel_hpc_lammps  --intel_hpc_lammps_nodes=2  --machine_type=Standard_HC44rs --zone=westus2  --image="<HPC_Custom_Image>"  --kafka_publish --owner=pdevaraj
```

### On GCP

The run will now consists of two steps :-

A.Run the intel_hpc_head_node_benchmark.py and create your custom image

```
./pkb.py --cloud=GCP --benchmarks=intel_hpc_head_node  --machine_type=c2-standard-60 --zones=us-east1 --owner=pdevaraj"

```
The output of the above command will be an GCP Image , lets call it  **HPC_Custom_Image**

B.We will now pass this new image as a parameter in --image to run all the HPC workloads

** For GCP we need to mention the image as well as the name of your project in GCP. You can find this on your Gcloud console.
   This is because each image is given access to your project alone unless you wish to change these permissions.**

SN Run:-
```
./pkb.py --cloud=GCP --benchmarks=intel_hpc_lammps --machine_type=c2-standard-60 --zone=us-east1  --image="<HPC_Custom_Image>" --svrinfo --collectd --kafka_publish --owner=pdevaraj
```

MN Run:-

```
./pkb.py --cloud=GCP --benchmarks=intel_hpc_lammps  --intel_hpc_lammps_nodes=2  --machine_type=c2-standard-60 --zone=us-east1  --image="<HPC_Custom_Image>"  --image_project="<Name of your GCP project>"  --kafka_publish --owner=pdevaraj


Note :- This support is not available for other CSPs yet.

## Flags used for HPC workloads

```

perfkitbenchmarker.linux_benchmarks.intel_hpc_binomialoptions:
  --[no]intel_hpc_binomialoptions_CC: If benchmark runs or not with Cluster Checker
    (default: 'false')
  --intel_hpc_binomialoptions_fss_type: File Shared System type: FSX or NFS
    (default: 'NFS')
  --intel_hpc_binomialoptions_image_type: Image type for binomialoptions
    (default: 'avx512')
  --intel_hpc_binomialoptions_image_version: Image version for binomialoptions
    (default: 'Jul2020')
  --intel_hpc_binomialoptions_nodes: The number of nodes to use
    (default: '1')
    (a positive integer)

perfkitbenchmarker.linux_benchmarks.intel_hpc_blacksholes:
  --[no]intel_hpc_blacksholes_CC: If benchmark runs or not with Cluster Checker
    (default: 'false')
  --intel_hpc_blacksholes_fss_type: File Shared System type: FSX or NFS
    (default: 'NFS')
  --intel_hpc_blacksholes_image_type: Image type for blacksholes
    (default: 'avx512')
  --intel_hpc_blacksholes_image_version: Image version for blacksholes
    (default: 'Jun2020')
  --intel_hpc_blacksholes_nodes: The number of nodes to use
    (default: '1')
    (a positive integer)

perfkitbenchmarker.linux_benchmarks.intel_hpc_montecarlo:
  --[no]intel_hpc_montecarlo_CC: If benchmark runs or not with Cluster Checker
    (default: 'false')
  --intel_hpc_montecarlo_fss_type: File Shared System type: FSX or NFS
    (default: 'NFS')
  --intel_hpc_montecarlo_image_type: Image type for montecarlo
    (default: 'avx512')
  --intel_hpc_montecarlo_image_version: Image version for montecarlo
    (default: 'Jun2020')
  --intel_hpc_montecarlo_nodes: The number of nodes to use
    (default: '1')
    (a positive integer)

perfkitbenchmarker.linux_benchmarks.intel_hpc_computebenches_benchmark:
  --[no]intel_hpc_computebenches_CC: If benchmark runs or not with Cluster Checker
    (default: 'false')
  --intel_hpc_computebenches_fss_type: File Shared System type: FSX or NFS
    (default: 'FSX')
  --intel_hpc_computebenches_image_type: Image type for computeBenches
    (default: 'avx512')
  --intel_hpc_computebenches_image_version: Image version for computeBenches
    (default: 'Mar2020')
  --intel_hpc_computebenches_nodes: The number of nodes to use
    (default: '1')
    (a positive integer)

perfkitbenchmarker.linux_benchmarks.intel_hpc_gromacs_benchmark:
  --[no]intel_hpc_gromacs_CC: If benchmark runs or not with Cluster Checker
    (default: 'false')
  --intel_hpc_gromacs_fss_type: File Shared System type: FSX or NFS
    (default: 'FSX')
  --intel_hpc_gromacs_image_type: Image type for gromacs
    (default: 'avx512')
  --intel_hpc_gromacs_image_version: Image version for gromacs
    (default: 'Mar2020')
  --intel_hpc_gromacs_nodes: The number of nodes to use
    (default: '1')
    (a positive integer)

perfkitbenchmarker.linux_benchmarks.intel_hpc_lammps_benchmark:
  --[no]intel_hpc_lammps_CC: If benchmark runs or not with Cluster Checker
    (default: 'false')
  --intel_hpc_lammps_fss_type: File Shared System type: FSX or NFS
    (default: 'FSX')
  --intel_hpc_lammps_image_type: Image type for lammps
    (default: 'avx512')
  --intel_hpc_lammps_image_version: Image version for lammps
    (default: 'Mar2020')
  --intel_hpc_lammps_nodes: The number of nodes to use
    (default: '1')
    (a positive integer)

perfkitbenchmarker.linux_benchmarks.intel_hpc_head_node_benchmark:
  --[no]intel_hpc_head_node_CC: If benchmark runs or not with Cluster Checker
    (default: 'false')
  --intel_hpc_head_node_fss_type: File Shared System type: FSX or NFS
    (default: 'FSX')
  --intel_hpc_head_node_image_type: Image type for head_node
    (default: 'avx512')
  --intel_hpc_head_node_image_version: Image version for head_node
    (default: 'July')
  --intel_hpc_head_node_nodes: The number of nodes to use
    (default: '1')
    (a positive integer)

perfkitbenchmarker.linux_benchmarks.intel_hpc_namd_benchmark:
  --[no]intel_hpc_namd_CC: If benchmark runs or not with Cluster Checker
    (default: 'false')
  --intel_hpc_namd_fss_type: File Shared System type: FSX or NFS
    (default: 'FSX')
  --intel_hpc_namd_image_type: Image type for namd
    (default: 'avx512')
  --intel_hpc_namd_image_version: Image version for namd
    (default: 'Mar2020')
  --intel_hpc_namd_nodes: The number of nodes to use
    (default: '1')
    (a positive integer)

perfkitbenchmarker.linux_benchmarks.intel_hpc_openfoam_benchmark:
  --[no]intel_hpc_openfoam_CC: If benchmark runs or not with Cluster Checker
    (default: 'false')
  --intel_hpc_openfoam_fss_type: File Shared System type: FSX or NFS
    (default: 'FSX')
  --intel_hpc_openfoam_image_type: Image type for openfoam
    (default: 'avx512')
  --intel_hpc_openfoam_image_version: Image version for openfoam
    (default: 'Mar2020')
  --intel_hpc_openfoam_nodes: The number of nodes to use
    (default: '1')
    (a positive integer)

perfkitbenchmarker.linux_benchmarks.intel_hpc_wrf_benchmark:
  --[no]intel_hpc_wrf_CC: If benchmark runs or not with Cluster Checker
    (default: 'false')
  --intel_hpc_wrf_fss_type: File Shared System type: FSX or NFS
    (default: 'FSX')
  --intel_hpc_wrf_image_type: Image type for wrf
    (default: 'avx512')
  --intel_hpc_wrf_image_version: Image version for wrf
    (default: 'Mar2020')
  --intel_hpc_wrf_nodes: The number of nodes to use
    (default: '1')
    (a positive integer)

perfkitbenchmarker.linux_packages.intel_hpc_singularity:
  --intel_hpc_go_version: GO Version
    (default: '1.13')
  --intel_hpc_singularity_version: Singlarity Version
    (default: '3.5.0')
```
