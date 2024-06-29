#!/bin/bash

if [ "$#" -ne 5 ]
then
  echo "
        Error: Incorrect number of arguments supplied.
        Usage: ./run_ec2_exp_runner.sh ProcessorType(intel/amd) InstanceType(e.g. c5.12xlarge, c5.4xlarge) NoOfCPUs(e.g. 8,12,24) ExpType(redis/memcached).
        "
  exit
fi

processor_type=$1
instance_type=$2
no_of_cores=$3
exp_type=$4
instance_no=$5

for run_no in {1..24};
do
  echo "Running run #$run_no."
  
  case "$exp_type" in
    nginx)
      case_no="case_1" #case_1: primary active, secondary idle; case_2: both primary and secondary active
      
      echo "Initializing the vms ...."
      for i in {1..12}; do
        ./run_ec2_exp_nginx.sh $processor_type $instance_type $no_of_cores $case_no primary init instance_$i.txt run_${run_no} &
        cid[${i}]=$!
      done
      
      for runid in ${cid[*]};
      do
        wait $runid
        echo "Process $runid is finished."
      done
      
      echo "*** Running nginx exp: ./run_ec2_exp_nginx.sh $processor_type $instance_type $no_of_cores"
      ./run_ec2_exp_nginx.sh $processor_type $instance_type $no_of_cores $case_no primary run instance_1.txt run_${run_no} &
      for i in {2..11}; do
        ./run_ec2_exp_nginx.sh $processor_type $instance_type $no_of_cores $case_no secondary run instance_$i.txt run_${run_no} &
      done
      ./run_ec2_exp_nginx.sh $processor_type $instance_type $no_of_cores $case_no secondary run instance_12.txt run_${run_no}
    ;;
    
    memcached)
      echo "*** Running mc or redis: ./run_ec2_exp.sh $processor_type $instance_type $no_of_cores $exp_type $instance_no"
      ./run_ec2_exp.sh $processor_type $instance_type $no_of_cores $exp_type $instance_no &
      ./run_ec2_exp.sh $processor_type $instance_type $no_of_cores $exp_type $instance_no &
      ./run_ec2_exp.sh $processor_type $instance_type $no_of_cores $exp_type $instance_no &
      ./run_ec2_exp.sh $processor_type $instance_type $no_of_cores $exp_type $instance_no &
    ;;
    mlc)
      case_no="case_1"
      
      echo "Initializing the vms ...."
      
      #intialize the vms
      for i in {1..12}; do
        ./run_ec2_exp_mlc.sh $processor_type $instance_type $no_of_cores $case_no primary init instance_$i.txt run_${run_no} &
        cid[${i}]=$!
      done
     
      for runid in ${cid[*]};
      do
        echo "Waiting for process $runid"
        wait $runid
      done
      
      #sleep 3m
       
      echo "Done initializing all the vms. Now running the tests .... "
      echo "*** Running mlc: ./run_ec2_exp_mlc.sh $processor_type $instance_type $no_of_cores $case_no (primary/secondary) (run) instance_$i.txt run_${run_no}"
       
      # run the exp
      ./run_ec2_exp_mlc.sh $processor_type $instance_type $no_of_cores $case_no primary run instance_1.txt run_${run_no} &
      for i in {2..11}; do
        ./run_ec2_exp_mlc.sh $processor_type $instance_type $no_of_cores $case_no secondary run instance_$i.txt run_${run_no} &
      done
      ./run_ec2_exp_mlc.sh $processor_type $instance_type $no_of_cores $case_no secondary run instance_12.txt run_${run_no}
    ;;
    
    dsb)
      case_no="case_1"
      echo "
      ./run_ec2_exp_dsb.sh $processor_type $instance_type $no_of_cores $case_no primary init instance_$i.txt run_${run_no} &"
      ./run_ec2_exp_dsb.sh $processor_type $instance_type $no_of_cores $case_no primary init instance_$i.txt run_${run_no} &
    ;;
    *)
      echo "Wrong experiment name $exp."
      exit 1
  esac
    
  echo "Sleeping for 5 minutes."
  sleep 40m
done
