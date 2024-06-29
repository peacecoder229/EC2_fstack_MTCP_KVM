#!/bin/bash

IS_UBUNTU=$(cat /etc/os-release | grep "^NAME" | grep Ubuntu)
if [ ! -z "$IS_UBUNTU" ]; then
    echo "This is Ubuntu. Adding Ansible ppa"
    sudo apt-add-repository -y ppa:ansible/ansible
    sudo apt-get update
    sudo apt-get install -y ansible
fi
