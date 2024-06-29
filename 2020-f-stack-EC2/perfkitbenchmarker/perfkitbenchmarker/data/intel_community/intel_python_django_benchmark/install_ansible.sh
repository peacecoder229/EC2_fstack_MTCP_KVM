#!/bin/bash

# exit when any command fails
set -e

IS_UBUNTU=$(cat /etc/os-release | grep "^NAME" | grep Ubuntu)
if [ ! -z "$IS_UBUNTU" ]; then
    echo "This is Ubuntu. Adding Ansible ppa"
    sudo apt install -y	python3-pip
    sudo pip3 install ansible
fi
