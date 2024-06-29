#!/bin/bash
#===============================================================================
# Copyright 2020 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

INSTALLATION_DIRECTORY=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CLUSTER_CONFIG="cluster_config.json"
ANSIBLE_PATH=/usr/local/bin

if [ "$SUDO_USER" == "" ]; then
    echo "You must run this script as sudo user!"
    exit 1
fi

# remove cluster
cd $INSTALLATION_DIRECTORY/kubespray
sudo -u "$SUDO_USER" $ANSIBLE_PATH/ansible-playbook -i inventory/cnb-cluster/inventory.yaml --become --become-user=root reset.yml --extra-vars "reset_confirmation=yes"

# reset master node hostname
cd $INSTALLATION_DIRECTORY
cp hostname.back /etc/hostname
hostname $(cat hostname.back)

echo "Kubernetes cluster has been removed"
