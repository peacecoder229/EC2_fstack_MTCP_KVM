#!/bin/bash

if [ $1 == 'install' ]
then
  sudo apt-get install -y zip unzip python-setuptools
elif [ $1 == 'remove' ]
then
  sudo apt-get remove -y zip unzip python-setuptools
fi
