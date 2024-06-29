Memcached BKM

Memtier_benchmark installation in clients

vim install_memtier.sh
#!/bin/bash
IP=$1
scp -r memtier_benchmark-master/ root@${IP}:/root/
ssh $IP "apt-get -y install build-essential autoconf automake libpcre3-dev libevent-dev pkg-config zlib1g-dev libssl-dev"
ssh $IP "cd /root/memtier_benchmark-master ; autoreconf -ivf ; autoreconf -ivf ; make ; make install"

for i in {11..17} {20..20}; do ./install_memtier.sh 192.168.100.$((200+i)); done

Run Memtier_benchmark  on redis or memcached servers


./redis_memcache_combo_pm_client.sh 250000 192.168.100.200 1:0 rajiv_redis_22serv redis 0-3 /root/redis_sriov launchserver

<no_of_request>  <SUT IP>   <ratio>   <tag_name>   <protocol>  <client_cores>  <client dir>  <lauch_servers of not>
<no_of_request>  : no of keys to be read or written   <allkeys  for writing all of the keys in min-max range>
<SUT IP> : interface IP  where the servers will be launched.
<ratio>   read: write ratio
<protocol> :  redis  or memcache_text
<client_cores>  : no of memtier_benchmarks to be launched   
<client_dir>  Need  to cd inside this dir before executing client_memt.sh  script


How the no of launched memtier_benchmark  is controlled

For each server ( servercore):
 For each client core:
Launch a memtier_benchmark with tasket set to the client core.

So total lnauched benchmark  per client machine = server cores * client cores.

