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

install_mc() {
  version=$1
  wget http://memcached.org/files/memcached-$version.tar.gz
  tar -zxvf memcached-$version.tar.gz
  pushd memcached-$version
  ./configure && make && make test && make install
  popd 
}

install_redis() {
  wget http://download.redis.io/redis-stable.tar.gz
  tar -xvzf redis-stable.tar.gz
  pushd redis-stable
  make && make install
  popd
}

install_mb() {
  git clone --depth 1 https://github.com/RedisLabs/memtier_benchmark
  pushd memtier_benchmark
  autoreconf -ivf
  ./configure
  make && make install
  popd
}

install_nginx() {
  wget http://nginx.org/download/nginx-1.16.1.tar.gz
  tar -xzf nginx-1.16.1.tar.gz
  cd nginx-1.16.1
  ./configure --prefix=/home/ubuntu/nginx
  make
  make install
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

# install memcached, pass the version no 
# list of release: (https://github.com/memcached/memcached/wiki/ReleaseNotes)
install_mc 1.6.9 

# install redis
install_redis

# install memtier benchmark
install_mb

# install nginx
install_nginx

# install wrk2
install wrk2
