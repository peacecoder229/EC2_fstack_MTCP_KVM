#!/bin/bash
IP=$1
scp -r memtier_benchmark-master/ root@${IP}:/root/
ssh $IP "apt-get -y install build-essential autoconf automake libpcre3-dev libevent-dev pkg-config zlib1g-dev libssl-dev"
ssh $IP "cd /root/memtier_benchmark-master ; autoreconf -ivf ; ./configure ; make ; make install"


