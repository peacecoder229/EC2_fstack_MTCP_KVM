#!/bin/bash

# check arguments
if [ "$#" -ne 3 ]
then
  echo "
        Error: Incorrect number of arguments supplied.
        Usage: ./run_ec2_exp.sh ProcessorType(intel/amd) InstanceType(e.g. c5.12xlarge, c5.4xlarge) NoOfCPUs(e.g. 8,12,24) .
        "
  #todo: check if jq is installed.
  exit
fi

# Global variables
instance_processor=$1 # intel or amd
instance_type=$2 #'c5.12xlarge' # general purpose: m5.4xlarge (8 core), compute optimized: c5.4xlarge, c5.12xlarge
no_of_cores=$3

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

  # --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=redis-mc-mb-1}]' \ 
  
  # global variable instance_id
  instance_id=$(aws ec2 run-instances \
  --image-id $image_id \
  --count $n_instances \
  --instance-type $instance_type \
  --key-name $key_name \
  --subnet-id $sub_id \
  --security-group-ids $sec_group_id \
  --associate-public-ip-address | jq -r '.Instances[0].InstanceId')

  echo "Instance $instance_id got created."

  # wait for the start-up script to finish installing the pre-requisites
  sleep 15m
}

get_dns_host_name() {
  # global variable dns_host_name
  dns_host_name=$(aws ec2 describe-instances --instance-ids $instance_id --query 'Reservations[].Instances[].PublicDnsName' --output text)
  echo "*** Public DNS Host Name of the instance: $dns_host_name"
}


terminate_ec2() {
  echo "*** Terminating instance $instance_id."
  aws ec2 terminate-instances --instance-ids $instance_id

  sleep 1m
}

main() {
  create_ec2

  terminate_ec2
}


# start executing the script
main
