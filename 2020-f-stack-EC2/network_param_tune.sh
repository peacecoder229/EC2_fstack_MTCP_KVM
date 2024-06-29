#!/bin/bash

sysctl -w net.ipv4.tcp_max_syn_backlog=6553600
sysctl -w net.core.wmem_max=838860800
sysctl -w net.core.rmem_max=838860080
sysctl -w net.core.somaxconn=51200
sysctl -w net.core.optmem_max=8192000
