#!/bin/bash
# This script should be executed after the initialization of an instance,
# If it is not run, then need to look at the log (/var/log/cloud-init-output.log) in the instance
# This script is run as root.

install_prereq() {
  apt-get update
  apt-get install -y build-essential
  apt-get install -y linux-tools-common
  apt-get install -y inux-tools-$(uname -r)
  apt-get install -y libevent-dev #mc
  apt-get install -y autoconf automake libpcre3-dev pkg-config zlib1g-dev libssl-dev # mb
  apt-get install -y numactl
  apt-get install -y python python3-pip
  pip3 install pandas

  sudo apt install -y sysstat # mpstat
}

install_nginx() {
  wget http://nginx.org/download/nginx-1.16.1.tar.gz
  tar -xzf nginx-1.16.1.tar.gz
  pushd nginx-1.16.1
  ./configure --prefix=/home/ubuntu/nginx
  make
  make install
  popd
}

install_wrk2() {
  git clone https://github.com/giltene/wrk2
  pushd wrk2
  make
  popd
}

# go to "ubuntu" user directory
pushd /home/ubuntu

# install pre requisites for the experiment
install_prereq

# install nginx
install_nginx

# install wrk2
install_wrk2

popd
