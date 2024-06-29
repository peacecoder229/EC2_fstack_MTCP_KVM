## Intel AIBench Benchmark Guidelines

### Benchmark Description
AIBench is a collection of end to end data center-focused deep learning and machine learning use cases. AIBench benchmark attempts to implement an entire data processing pipeline similar to what might be encountered in a data center. A primary use of AIBench is to examine how the several workloads use system resources and what this tells us about building better hardware and software systems.

The AIBench workloads integrated into PKB are listed in <b>Table 1</b> below.

| <b>WORKLOAD</b> | <b>SCENARIO</b> | <b>OS </b> |
| --- | --- | ---
| Transformer Neural Machine Translation | transformer-nmt-standalone-inference <br> e2e-transformer-nmt | CentOS 7 |
| Google's Neural Machine Translation (GNMT) | gnmt-standalone-inference <br> gnmt-batch-inference <br> e2e-gnmt | CentOS 7 |
| Question Answering Network (QANet) | qanet-standalone-inference <br> qanet-batch-inference | CentOS 7 |
| Convolutional Neural Networks (CNN) - Resnet50 | cnn | CentOS 7 |
|  Object Detection (RCNN) | standalone-rcnn-videodecode <br> standalone-rcnn-inference <br> e2e-rcnn <br> | CentOS 7 |
| Face Recognition | standalone-face-decode-detection <br> throwaway-face-decode-detection <br> standalone-face-inference <br> e2e-face-recognition | CentOS 7 |
| Long-term Recurrent Convolutional Networks (LRCN) | lrcn-activity-recognition-batch-inference | CentOS 7 |
| Mozilla DeepSpeech (MZDeepSpeech) | mzdeepspeech | CentOS 7 |
| Text to Speech | text-to-speech-inference | CentOS 7 |
| Super Resolution Generative Adversarial Network (SRGAN) | srgan-inference | CentOS 7 |
| Wide and Deep Networks | wide-n-deep | Ubuntu 16.04 |
| UNet-3D | unet3d-inference | Ubuntu 16.04 |

<b>Table 1</b>: AIBench Workloads integrated into PKB

<br>

## How to run Intel AIBench on AWS
To run an AIBench scenario on AWS via PKB, the command is:

```
python2 pkb.py --cloud=AWS --image=<image> --os_type=<os_type> --zones="us-east-2" --benchmarks=intel_aibench 
--aibench_scenario=<aibench_scenario> 
--aibench_harness_yaml=perfkitbenchmarker/data/intel_aibench/harness-settings-<aibench_scenario>.yaml  
--machine_type=<machine_type> --aws_boot_disk_size=100

```
In this command:
* `--image` is the Amazon Machine Image (AMI). For CentOS 7, use image `ami-e0eac385`, and for Ubuntu 16.04 use `ami-0f93b5fd8f220e428`.
* `--os_type` is the type of OS. Set it to `centos7` for CentOS 7 workloads and `ubuntu1604` for Ubuntu 16.04 workloads. The OS required for workloads is listed in <b>Table 1<b>.
* `--aibench-scenario` is the AIBench scenario you want to run. All scenarios are listed in <b>Table 1<b>.
* `--aibench_harness_yaml` is the YAML file containing the run time settings for the scenario. The YAML file for scenario `x` is available at `perfkitbenchmarker/data/intel_aibench/harness-settings-x.yaml`
* `--machine_type` is an Amazon instance type. You could use `m5d.12xlarge` or `m5.24xlarge`.

For instance, to run scenario `transformer-nmt-standalone-inference` on AWS, the command would be:
```
 python2 pkb.py --cloud=AWS --image=ami-e0eac385 --os_type=centos7 --zones="us-east-1" --benchmarks=intel_aibench 
 --aibench_scenario=transformer-nmt-standalone-inference 
 --aibench_harness_yaml=perfkitbenchmarker/data/intel_aibench/harness-settings-transformer-nmt-standalone-inference.yaml 
 --machine_type=c5.12xlarge --aws_boot_disk_size=100

```

<br>

## How to run Intel AIBench on Azure
To run an AIBench scenario on Azure via PKB, the command is:

```
python2 pkb.py --cloud=Azure --image=<image> --os_type=<os_type> --zones="us-east-2" --benchmarks=intel_aibench 
--aibench_scenario=<aibench_scenario> 
--aibench_harness_yaml=perfkitbenchmarker/data/intel_aibench/harness-settings-<aibench_scenario>.yaml  
--machine_type=MACHINE_TYPE

```
In this command:
* `--image` is the Azure base image. For CentOS 7, use `OpenLogic:CentOS:7.4:7.4.20180704`, and for Ubuntu 16.04 use `Canonical:UbuntuServer:16.04-LTS:latest`.
* `--os_type` is the type of OS. Set it to `centos7` for CentOS 7 workloads and `ubuntu1604` for Ubuntu 16.04 workloads. The OS required for workloads is listed in <b>Table 1<b>.
* `--aibench-scenario` is the AIBench scenario you want to run. All scenarios are listed in <b>Table 1<b>.
* `--aibench_harness_yaml` is the YAML file containing the run time settings for the scenario. The YAML file for scenario `x` is available at `perfkitbenchmarker/data/intel_aibench/harness-settings-x.yaml`
* `--machine_type` is an Azure instance type. You could use `Standard_F48s_v2`.

For instance, to run scenario `unet3d-inference` on Azure, the command would be:
```
python2 pkb.py --cloud=Azure --image=Canonical:UbuntuServer:16.04-LTS:latest --os_type=ubuntu1604 --zones="eastus2" 
--benchmarks=intel_aibench --aibench_scenario=unet3d-inference 
--aibench_harness_yaml=perfkitbenchmarker/data/intel_aibench/harness-settings-unet3d-inference.yaml 
--machine_type=Standard_F48s_v2
```

<br>

## How to run Intel AIBench on Virtual Machines

To run an AIBench scenario on a VM, the command is:
```
python2 pkb.py --benchmark_config_file=perfkitbenchmarker/data/intel_aibench/wp_config.yml --benchmarks=intel_aibench 
--os_type=<os_type> --aibench_scenario=<aibench_scenario> 
--aibench_harness_yaml=perfkitbenchmarker/data/intel_aibench/harness-settings-<aibench_scenario>.yaml

```
In this command:
* `--benchmark_config_file` is the configuration file that PKB allows to pass while running on VMs. The `wp_config.yml` file is as below:
    ```
    static_vms:
        - &vm0
          ip_address: <IP_ADDRESS_OF_VM>
          user_name: pkb
          ssh_private_key: ~/.ssh/id_rsa
          internal_ip: <IP_ADDRESS_OF_VM>
          os_type: <OS_TYPE>     
     
    intel_aibench:
        vm_groups:
            target:
                static_vms:
                    - *vm0
    ```
    In the above `wp_config.yaml` file, set `ip_address` and `internal_ip` to the IP address of the VM, and set `os_type` to `rhel` for CentOS and `debian` for Ubuntu workloads. Also, the VM must be set up with user name `pkb` and must be configured to have passwordless sudo privileges. A scenario requires a dedicated VM for each of it's virtual instance. 
* `--os_type` is the type of OS. Set it to `rhel` for CentOS 7 workloads and `ubuntu1604` for Ubuntu 16.04 workloads. The OS required for workloads is listed in <b>Table 1<b>.
* `--aibench-scenario` is the AIBench scenario you want to run. All scenarios are listed in <b>Table 1<b>.
* `--aibench_harness_yaml` is the YAML file containing the run time settings for the scenario. The YAML file for scenario `x` is available at `perfkitbenchmarker/data/intel_aibench/harness-settings-x.yaml`

`Vagrant` could be used to set up VMs for testing purposes.

For instance, to run scenario `e2e-face-recognition` on VMs, the command would be:
```
python2 pkb.py --benchmark_config_file=./wp_config.yml --benchmarks=intel_aibench --os_type=rhel 
--aibench_scenario=e2e-face-recognition 
--aibench_harness_yaml=perfkitbenchmarker/data/intel_aibench/harness-settings-e2e-face-recognition.yaml

```
The `--aibench_harness_yaml` of this scenario is located at: `perfkitbenchmarker/data/intel_aibench/harness-settings-e2e-face-recognition.yaml`.
From this YAML, it is clear that this scenario has 3 virtual instances.
```
scenarios:
  e2e-face-recognition:
    virtual-instances: e2e-face-inference,e2e-face-decode-detection,e2e-kafkabroker
```
Hence, 3 VMs are required to run this scenario and the `wp_config.yml` file would look as follows:
```
static_vms:
    - &vm0
      ip_address: <IP_ADDRESS_OF_VM0>
      user_name: pkb
      ssh_private_key: ~/.ssh/id_rsa
      internal_ip: <IP_ADDRESS_OF_VM0>
      os_type: <OS_TYPE>   
    - &vm1
      ip_address: <IP_ADDRESS_OF_VM1>
      user_name: pkb
      ssh_private_key: ~/.ssh/id_rsa
      internal_ip: <IP_ADDRESS_OF_VM1>
      os_type: <OS_TYPE> 
    - &vm2
      ip_address: <IP_ADDRESS_OF_VM2>
      user_name: pkb
      ssh_private_key: ~/.ssh/id_rsa
      internal_ip: <IP_ADDRESS_OF_VM2>
      os_type: <OS_TYPE> 
     
intel_aibench:
    vm_groups:
        target:
            static_vms:
              - *vm0
              - *vm1
              - *vm2
```

<br>

## How to run AIbench on AWS EKS (Kubernetes environment)
To run an AIBench scenario on EKS via PKB, the command is:

```
python2 pkb.py --os_type=<os_type> --kubectl=<kubectl_binary_location> 
--kubeconfig=<kube config file of EKS cluster> --cloud=Kubernetes --container_cluster_cloud=AWS 
--benchmarks=intel_aibench_k8 --aibench_scenario=<aibench_scenario> --image=<container image of scenario> 
--aibench_harness_yaml=perfkitbenchmarker/data/intel_aibench/harness-settings-<aibench_scenario>.yaml

```
In this command:
* `--image` is the workload scenario image. It can be stored any docker registry preferably ECR registry, accessible by EKS cluster.
* `--os_type` is the type of OS. Set it to `centos7` for CentOS 7 workloads and `ubuntu1604` for Ubuntu 16.04 workloads. The OS required for workloads is listed in <b>Table 1<b>.
* `--aibench-scenario` is the AIBench scenario you want to run. All scenarios are listed in <b>Table 1<b>.
* `--aibench_harness_yaml` is the YAML file containing the run time settings for the scenario. The YAML file for scenario `x` is available at `perfkitbenchmarker/data/intel_aibench/harness-settings-x.yaml`

For instance, to run scenario `transformer-nmt-standalone-inference` on AWS, the command would be:
```
python2 pkb.py --os_type=rhel --kubectl=/usr/bin/kubectl --kubeconfig=kubefile-config-aws --cloud=Kubernetes 
--container_cluster_cloud=AWS --benchmarks=intel_aibench_k8 --aibench_scenario=transformer-nmt-standalone-inference 
--image=310062343207.dkr.ecr.us-east-1.amazonaws.com/aibench:nmt-inference.20190619131404787047 
--aibench_harness_yaml=perfkitbenchmarker/data/intel_aibench/harness-settings-transformer-nmt-standalone-inference.yaml

```

<br>

## How to run Intel AIBench on Azure AKS (Kubernetes environment)
To run an AIBench scenario on AKS via PKB, the command is:

```
python2 pkb.py --os_type=<os_type> --kubectl=<kubectl_binary_location> 
--kubeconfig=<kube config file of AKS cluster> --cloud=Kubernetes --container_cluster_cloud=Azure 
--benchmarks=intel_aibench_k8 --aibench_scenario=<aibench_scenario> --image=<container image of scenario> 
--aibench_harness_yaml=perfkitbenchmarker/data/intel_aibench/harness-settings-<aibench_scenario>.yaml

```
In this command:
* `--image` is the workload scenario image. It can be stored any docker registry preferably ACR registry, accessible by AKS cluster. It can use ECR registry as long as the AKS can access the ECR registry
* `--os_type` is the type of OS. Set it to `centos7` for CentOS 7 workloads and `ubuntu1604` for Ubuntu 16.04 workloads. The OS required for workloads is listed in <b>Table 1<b>.
* `--aibench-scenario` is the AIBench scenario you want to run. All scenarios are listed in <b>Table 1<b>.
* `--aibench_harness_yaml` is the YAML file containing the run time settings for the scenario. The YAML file for scenario `x` is available at `perfkitbenchmarker/data/intel_aibench/harness-settings-x.yaml`

<br>

## How to run Intel AIBench multi node workload on AKS/EKS environment

To run an AIBench multi node scenario on any AKS/EKS, the command is:
```
python2 pkb.py --os_type=<os_type> --kubectl=<kubectl_binary_location> 
--kubeconfig=<kube config file of EKS cluster> --cloud=Kubernetes --container_cluster_cloud=<cluster_cloud> --benchmarks=intel_aibench_k8 
--aibench_scenario=<aibench_scenario> --image=<container image of scenario> --benchmark_config_file <wp_config_file_for_multinode_workload>
--aibench_harness_yaml=perfkitbenchmarker/data/intel_aibench/harness-settings-<aibench_scenario>.yaml

```
In this command:
* `--benchmark_config_file` is the configuration file that PKB allows to pass while running multi node workload. It is defined for each multi node worklaod. It can be found in perfkitbenchmarker/data/intel_aibench. The `wp_face_recog_config.yml` file is as below:
    ```
    intel_aibench_k8:
      vm_groups:
        vm_kafka:
          vm_count: 1
          cloud: Kubernetes
          vm_spec:
            Kubernetes:
              image: <image_name of kafka container>
        target:
          vm_count: 1
          cloud: Kubernetes
          vm_spec:
            Kubernetes:
               image: <image_name of inference container>
        vm_producer:
          vm_count: 1
          cloud: Kubernetes
          vm_spec:
            Kubernetes:
               image: <image name of producer container>
    ```
* `--os_type` is the type of OS. Set it to `rhel` for CentOS 7 workloads and `ubuntu1604` for Ubuntu 16.04 workloads. The OS required for workloads is listed in <b>Table 1<b>.
* `--aibench-scenario` is the AIBench scenario you want to run. All scenarios are listed in <b>Table 1<b>.
* `--aibench_harness_yaml` is the YAML file containing the run time settings for the scenario. The YAML file for scenario `x` is available at `perfkitbenchmarker/data/intel_aibench/harness-settings-x.yaml`

<br>

## Containers available in ECR registry

| <b>WORKLOAD</b> | <b>SCENARIO</b> | <b>Image</b> |
| --- | --- | ---
| Transformer Neural Machine Translation | transformer-nmt-standalone-inference <br> e2e-transformer-nmt | 310062343207.dkr.ecr.us-east-1.amazonaws.com/aibench:nmt-inference.20190619131404787047 |
| Google's Neural Machine Translation (GNMT) | gnmt-standalone-inference <br> gnmt-batch-inference <br> e2e-gnmt | 310062343207.dkr.ecr.us-east-1.amazonaws.com/aibench:nmt-inference.20190619131404787047 |
| Question Answering Network (QANet) | qanet-standalone-inference <br> qanet-batch-inference | 310062343207.dkr.ecr.us-east-1.amazonaws.com/aibench:qanet-inference-va.20190627234336067588 |
| Convolutional Neural Networks (CNN) - Resnet50 | cnn | 310062343207.dkr.ecr.us-east-1.amazonaws.com/aibench:cnn-inference.20190620133032838932 |
| Object Detection (RCNN) | standalone-rcnn-videodecode <br> standalone-rcnn-inference <br> e2e-rcnn <br> | 310062343207.dkr.ecr.us-east-1.amazonaws.com/aibench:standalone-rcnn-videodecode.20190624165115707906 <br> 310062343207.dkr.ecr.us-east-1.amazonaws.com/aibench:standalone-rcnn-inference.20190624143522056546 |
| Face Recognition | standalone-face-decode-detection <br> throwaway-face-decode-detection <br> standalone-face-inference <br> e2e-face-recognition | 310062343207.dkr.ecr.us-east-1.amazonaws.com/aibench:e2e-face-decode-detection.20190621114459788429 <br> 310062343207.dkr.ecr.us-east-1.amazonaws.com/aibench:e2e-face-inference.20190624110430301439 |
| Long-term Recurrent Convolutional Networks (LRCN) | lrcn-activity-recognition-batch-inference | 310062343207.dkr.ecr.us-east-1.amazonaws.com/aibench:lrcn-activity-recognition-batch-inference.20190620150643774658 |
| Mozilla DeepSpeech (MZDeepSpeech) | mzdeepspeech | 310062343207.dkr.ecr.us-east-1.amazonaws.com/aibench:mzdeepspeech-inference.20190620154848955920 |
| Text to Speech | text-to-speech-inference | 310062343207.dkr.ecr.us-east-1.amazonaws.com/aibench:text-to-speech-inference.20190625095057279330 |
| Super Resolution Generative Adversarial Network (SRGAN) | srgan-inference | 310062343207.dkr.ecr.us-east-1.amazonaws.com/aibench:srgan-inference.20190621094851034871 |
| Wide and Deep Networks | wide-n-deep | 310062343207.dkr.ecr.us-east-1.amazonaws.com/aibench:wide-n-deep-inference.20190626113943988616 |
| UNet-3D | unet3d-inference | 310062343207.dkr.ecr.us-east-1.amazonaws.com/aibench:unet-3d.20190626115958775378 |

<b>Table 2</b>: AIBench Workloads Images on ECR registry

## How to select the number of cores of the machine to run on
The run time settings YAML file for all scenarios is available at: `perfkitbenchmarker/data/intel_aibench`. 
Edit the field `cores` in the scenario YAML to select the number of cores to run on.
```
cores: 12           # to run scenario on core 12

cores: 0-47         # to run scenario on 48 cores of machine

#cores: 0-55        # to run scenario on all available cores of machine, comment out/remove the field 'cores' 
```

<br>

## How to run multiple instances of scenario
The run time settings YAML file for all scenarios is available at: `perfkitbenchmarker/data/intel_aibench`. 
Set the field `repeat-count` in the scenario YAML file to the number of instances of the scenario you want to run and the field `cores` to the number of cores to use. The cores are assigned uniformly among all the instances. 
```
repeat-count: 1       # to run 1 instance of scenario on all cores
#cores: 0-47             

repeat-count: 12      # to run 12 instances of scenario, with each instance running on 4 cores
cores: 0-47

repeat-count: 3       # to run 3 instances of scenario, with each instance running on 14 cores
cores: 0-43
```