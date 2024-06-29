#!/bin/bash

# check arguments
if [ "$#" -ne 8 ]
then
  echo "
        Error: Incorrect number of arguments supplied.
        Usage: ./run_ec2_exp_mlc.sh ProcessorType(intel/amd) InstanceType(e.g. c5.12xlarge, c5.4xlarge) NoOfCPUs(e.g. 8,12,24) CaseNo(case_1/case_2) VMType(primary/secondary) Mode(init/run) InstanceFile RunNo(1,2 ... etc.).
        "
  #todo: check if jq is installed.
  exit
fi

# Global variables
instance_processor=$1 # intel or amd
instance_type=$2 #'c5.12xlarge' # general purpose: m5.4xlarge (8 core), compute optimized: c5.4xlarge, c5.12xlarge
no_of_cores=$3
case_no=$4
vm_type=$5
mode=$6
instance_file=$7
run_no=$8

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
    echo "*** Creating intel instances ..."
    sub_id=$intel_sn
  else
    echo "*** Creating amd instances ..."
    sub_id=$amd_sn
  fi
  echo "*** subnet id is : $sub_id, instance type is: $instance_type."

  local instance_name='f-stack-3'
  local tag="'ResourceType=instance,Tags=[{Key=Name,Value=redis-mc-mb-1}]'"
  
  # the user script is run in sudo, so the user is root. 
  # If you log in as normal user you need to specify the user specific path
  local start_up_script='file://startup_script_nginx.sh'
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
  --user-data file://./startup_script_mlc.sh | jq -r '.Instances[0].InstanceId')

  echo "*** Instance $instance_id got created."
  echo "*** Installing required softwares ...."
  
  # wait for the start-up script to finish installing the pre-requisites
  sleep 5m
}

get_dns_host_name() {
  # global variable dns_host_name
  dns_host_name=$(aws ec2 describe-instances --instance-ids $instance_id --query 'Reservations[].Instances[].PublicDnsName' --output text)
  echo "*** Public DNS Host Name of the instance: $dns_host_name"
  
  # write instance id and dns hostname to instance file
  echo "$instance_id $dns_host_name" > $instance_file
}

scp_exp_script() {
  echo "*** Copying experiment script to $instance_id."
  
  local copy_dir='mlc/Linux'
  local remote_dir='/home/ubuntu/'
    
  scp -r -i "test-key-3.pem" -o "StrictHostKeyChecking no" -o ProxyCommand='nc --proxy-type socks5 --proxy proxy-us.intel.com:1080 %h %p' $copy_dir ubuntu@$dns_host_name:$remote_dir
}

run_exp_script() {
  echo "*** Running experiment script on $instance_id ...."
  
  local exp_script="pushd /home/ubuntu/Linux; sudo bash run_mlc.sh $case_no $vm_type $instance_id $run_no $no_of_cores > /home/ubuntu/output.log; popd"
  local full_command="$exp_script"
  
  ssh -i "test-key-3.pem" -o "StrictHostKeyChecking no" -o ProxyCommand='nc --proxy-type socks5 --proxy proxy-us.intel.com:1080 %h %p' ubuntu@$dns_host_name "${full_command}"
  
  echo "*** Experiment done ...."
  #sleep 10m  # wait for the experiment to finish
}

scp_exp_result() {
  local remote_dir="/home/ubuntu" 
  local local_dir="./ec2_exp_mlc_drc_res/"
  
  echo "*** Copying experiemnt result from $instance_id ($remote_dir) to ncc1-156T ($local_dir)"
  
  scp -r -i "test-key-3.pem" -o "StrictHostKeyChecking no" -o ProxyCommand='nc --proxy-type socks5 --proxy proxy-us.intel.com:1080 %h %p' ubuntu@$dns_host_name:$remote_dir/${result_dir_prefix}_* $local_dir
}

terminate_ec2() {
  echo "*** Terminating instance $instance_id."
  aws ec2 terminate-instances --instance-ids $instance_id

  sleep 1m
}

main() {
  case "$mode" in
    init)
      create_ec2
      get_dns_host_name
      scp_exp_script
    ;;
    run) 
      instance_id=$(cat $instance_file | awk '{print $1}')
      dns_host_name=$(cat $instance_file | awk '{print $2}')
      rm -f $instance_file
      echo "Instance id: $instance_id, DNS Host Name: $dns_host_name."
      
      run_exp_script
      scp_exp_result
      terminate_ec2
    ;;
    *)
      echo "Mode should be init or run."
      exit 1
  esac
}

# start executing the script
main


