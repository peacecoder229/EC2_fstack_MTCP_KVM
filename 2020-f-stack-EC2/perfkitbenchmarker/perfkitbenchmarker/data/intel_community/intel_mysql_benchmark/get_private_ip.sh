#!/bin/bash

sudo yum install -y iproute &> /dev/null || true
sudo ln -s /usr/sbin/ip /usr/bin/ip &> /dev/null || true
ip -o addr show scope global | awk '{print $4}' | cut -f1 -d '/' | head -n 1
