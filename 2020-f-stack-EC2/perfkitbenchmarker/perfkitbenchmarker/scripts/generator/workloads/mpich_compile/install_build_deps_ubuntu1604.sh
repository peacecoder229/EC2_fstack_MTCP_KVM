#!/usr/bin/env bash

#!/bin/bash

if [ $1 == 'install' ]
then
  sudo apt-get install -y wget build-tools git libtool autoconf automake
elif [ $1 == 'remove' ]
then
  sudo apt-get remove -y wget build-tools
fi

