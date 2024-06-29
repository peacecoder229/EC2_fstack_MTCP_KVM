#!/bin/bash

if [ $1 == 'install' ]
then
  sudo yum install -y make automake libtool pkgconfig libaio-devel wget git numactl mysql-devel mysql
elif [ $1 == 'remove' ]
then
  sudo yum erase -y make automake libtool libaio-devel wget git numactl mysql-devel mysql 
fi