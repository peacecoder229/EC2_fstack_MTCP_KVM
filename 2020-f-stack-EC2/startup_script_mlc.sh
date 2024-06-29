#!/bin/bash
# This script should be executed after the initialization of an instance,
# If it is not run, then need to look at the log (/var/log/cloud-init-output.log) in the instance

install_prereq() {
  apt-get update
  apt-get install -y build-essential
  apt-get install -y libevent-dev #mc
  apt-get install -y autoconf automake libpcre3-dev pkg-config zlib1g-dev libssl-dev # mb
  apt-get install -y numactl
  apt-get install -y python python3-pip
  pip3 install pandas
}


# go to "ubuntu" user directory
pushd /home/ubuntu

# install pre requisites for the experiment
install_prereq
