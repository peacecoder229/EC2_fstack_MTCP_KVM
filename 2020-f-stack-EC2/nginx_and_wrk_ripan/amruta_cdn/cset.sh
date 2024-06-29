#!/bin/bash

CGNAME="nginx"
MEMCG="/sys/fs/cgroup/memory/${CGNAME}"
CPUSET="/sys/fs/cgroup/cpuset/${CGNAME}"

#cset shield --cpu 1-8 --userset=${CGNAME}
cset set --cpu 1-9,65-73 --set=nginx
echo 1 > ${CPUSET}/cpuset.mems
mkdir ${MEMCG}
echo 64G > ${MEMCG}/memory.limit_in_bytes

cset proc ${CGNAME} -e /bin/bash
# /root/stop_nginx.sh
# /root/start_nginx.sh
cat ${CPUSET}/tasks | xargs -i {} echo {} > ${MEMCG}/tasks
#cat ${CPUSET}/tasks | xargs -I {} echo {} > ${MEMCG}/tasks

