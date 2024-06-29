#!/bin/bash

if [ $1 == 'install' ]
then
  sudo apt-get install -y make automake libtool pkg-config libssl-dev libaio1 wget git numactl
elif [ $1 == 'remove' ]
then
  sudo apt-get remove -y make automake libtool pkg-config libssl-dev libaio1 wget git numactl
fi

