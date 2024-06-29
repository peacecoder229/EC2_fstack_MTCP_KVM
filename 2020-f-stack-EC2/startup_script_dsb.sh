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

  sudo apt install -y luarocks luasocket
}

install_docker() {
  # update the packages index and install the dependencies necessary to add a new HTTPS repository
  sudo apt install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common
  
  # Import the repository’s GPG key using the following curl command:
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

  # Add the Docker APT repository to your system:
  sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
  
  # install the latest version of Docker
  sudo apt install -y docker-ce docker-ce-cli containerd.io
}

install_docker_compose() {
  sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

  sudo chmod +x /usr/local/bin/docker-compose
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

install_dsb() {
  git clone https://github.com/delimitrou/DeathStarBench
  #pushd /home/ubuntu/DeathStarBench/hotelReservation
  #ip_addr = $(uname -n | awk -F'-' '{print $2"."$3"."$4"."$5}')
  #sed -i 's/x.x.x.x/${ip_addr}/g' config.json
  #popd
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

install_docker
install_docker_compose

install_dsb

# install nginx
install_nginx

# install wrk2
install_wrk2

popd
