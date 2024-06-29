#!/bin/bash

# vcpus in the system
num_cores=0
num_nodes=$(kubectl get node --no-headers -o custom-columns=NAME:.metadata.name | wc -l)
nodes=$(kubectl get nodes | awk 'FNR > 1')
while read -r node; do
    node_name=$(echo $node | awk '{print $1}')
    node_role=$(echo $node | awk '{print $3}')
    cores=$(kubectl describe node $node_name | grep cpu: | head -n 1 | awk '{print $2}')
    #if master has more than 1 core, account it.
    if [ "$node_role" = "master" ] || [ "$node_role" = "Master" ]; then
        if [ $(($cores)) -gt 2 ]; then
            num_cores=$(($num_cores + $cores))
        fi
    else
        num_cores=$(($num_cores + $cores))
    fi
done <<<"$nodes"

echo "Number of nodes in cluster:" $num_nodes
echo "Total number of cores: "$num_cores

# assume 4 vcpus per pod!
cpuperpod=4
clients=$(($num_cores / $cpuperpod))

if [ $(($clients)) -gt 6 ]; then
    clients=$(($clients - 5))
    sed -i 's/"initialclients":.*",/"initialclients": "'$clients'",/' config.json
fi
