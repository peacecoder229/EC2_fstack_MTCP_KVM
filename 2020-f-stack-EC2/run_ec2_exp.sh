#!/bin/bash

# check arguments
if [ "$#" -ne 5 ]
then
  echo "
        Error: Incorrect number of arguments supplied.
        Usage: ./run_ec2_exp.sh ProcessorType(intel/amd) InstanceType(e.g. c5.12xlarge, c5.4xlarge) NoOfCPUs(e.g. 8,12,24) ExpType(redis/memcached) InstanceNo(optional).
        "
  #todo: check if jq is installed.
  exit
fi

# Global variables
instance_processor=$1 # intel or amd
instance_type=$2 #'c5.12xlarge' # general purpose: m5.4xlarge (8 core), compute optimized: c5.4xlarge, c5.12xlarge
no_of_cores=$3
exp_type=$4 # redis or memcached
instance_no=$5

intel_sn='subnet-0f7c796a123cfa8e9'
amd_sn='subnet-01681843f0d16633a'

result_dir_prefix="drc_res"

create_ec2() {
  local image_id='ami-08962a4068733a2b6'
  local n_instances=1
  
  # todo: local vpc_id=
  local key_name='test-key-3'
  local sec_grp_id='sg-0afe82bb2c91d28c9'
  
  local sub_id 
  if [[ "$instance_processor" == "intel" ]]
  then
    echo "Creating intel instances ..."
    sub_id=$intel_sn
  else
    echo "Creating amd instances ..."
    sub_id=$amd_sn
  fi
  echo "subnet id is : $sub_id, instance type is: $instance_type."

  local instance_name='f-stack-3'
  local tag="'ResourceType=instance,Tags=[{Key=Name,Value=redis-mc-mb-1}]'"
  
  # the user script is run in sudo, so the user is root. 
  # If you log in as normal user you need to specify the user specific path
  local start_up_script='file://startup_script.sh'
  local cpu_options="CoreCount=$no_of_cores,ThreadsPerCore=1"

  # --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=redis-mc-mb-1}]' \ 
  
  # global variable instance_id
  instance_id=$(aws ec2 run-instances \
  --image-id $image_id \
  --count $n_instances \
  --instance-type $instance_type \
  --key-name $key_name \
  --subnet-id $sub_id \
  --security-group-ids $sec_group_id \
  --cpu-options $cpu_options \
  --associate-public-ip-address \
  --user-data file://./startup_script.sh | jq -r '.Instances[0].InstanceId')

  echo "Instance $instance_id got created."

  # wait for the start-up script to finish installing the pre-requisites
  sleep 15m
}

get_dns_host_name() {
  # global variable dns_host_name
  dns_host_name=$(aws ec2 describe-instances --instance-ids $instance_id --query 'Reservations[].Instances[].PublicDnsName' --output text)
  echo "*** Public DNS Host Name of the instance: $dns_host_name"
}

scp_exp_script() {
  echo "*** Copying experiment script to $instance_id."
  
  local copy_dir='redis_memcachd_memtier_benchmark'
  local remote_dir='/home/ubuntu/'
  
  scp -r -i "test-key-3.pem" -o "StrictHostKeyChecking no" -o ProxyCommand='nc --proxy-type socks5 --proxy proxy-us.intel.com:1080 %h %p' $copy_dir ubuntu@$dns_host_name:$remote_dir 
}

run_exp_script() {
  echo "*** Running experiment script ...."
   
  local low_core=0
  local high_core=$((no_of_cores-1))
  local exp_script="./mc_or_redis_sweep_${no_of_cores}_core.sh" 
   
  ssh -i "test-key-3.pem" -o ProxyCommand='nc --proxy-type socks5 --proxy proxy-us.intel.com:1080 %h %p' ubuntu@$dns_host_name "export TZ=America/Los_Angeles && export runnuma="no" && pushd /home/ubuntu/redis_memcachd_memtier_benchmark && chmod +x *.sh *.py && pushd core_scale && chmod +x *.sh *.py && popd && ${exp_script} ${low_core}-${high_core} ${result_dir_prefix} 1 ${exp_type}"
  
  sleep 10m  # wait for the experiment to finish
}

scp_exp_result() {
  local remote_dir="/home/ubuntu/redis_memcachd_memtier_benchmark" 
  #local local_dir="./ec2_exp_mc_mb_redis_drc_res/$instance_processor/$instance_type/$instance_no"
  local local_dir="./ec2_exp_mc_mb_redis_drc_res/$instance_processor/$instance_type"
  
  echo "*** Copying experiemnt result from $instance_id ($remote_dir) to ncc1-156T ($local_dir)"
  
  scp -r -i "test-key-3.pem" -o "StrictHostKeyChecking no" -o ProxyCommand='nc --proxy-type socks5 --proxy proxy-us.intel.com:1080 %h %p' ubuntu@$dns_host_name:$remote_dir/${result_dir_prefix}_* $local_dir

  sleep 2m
}

terminate_ec2() {
  echo "*** Terminating instance $instance_id."
  aws ec2 terminate-instances --instance-ids $instance_id

  sleep 1m
}

main() {
  create_ec2

  get_dns_host_name

  scp_exp_script

  run_exp_script

  scp_exp_result

  terminate_ec2
}

# start executing the script
main
