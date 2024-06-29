#!/usr/bin/env bash

FACEBOOK5_WL_GENERIC_NAME="facebook5"
FACEBOOK5_WL_PROVISION_FILE="facebook5"

WORKING_DIR=$(cd $(dirname "$0") && pwd)
WHOAMI=$(whoami)

ID_RSA_FILE=~/.ssh/id_rsa
SSH_CONFIG_FILE=~/.ssh/config
AUTH_KEYS_FILE=~/.ssh/authorized_keys

if [ ! -f "$ID_RSA_FILE" ]; then
    yes y | ssh-keygen -t rsa -q -f "$ID_RSA_FILE" -N ''
fi
if [ -f "$SSH_CONFIG_FILE" ]; then
    mv "$SSH_CONFIG_FILE" "$SSH_CONFIG_FILE.facebook5.old"
fi
echo "Host *" > "$SSH_CONFIG_FILE"
echo "   StrictHostKeyChecking no" >> "$SSH_CONFIG_FILE"
cat "$ID_RSA_FILE.pub" >> "$AUTH_KEYS_FILE"

cat hosts | grep localhost
if [ $? -ne 0 ]; then
    sed -i "/^\[target\]/a localhost" hosts
fi
sed -i "s/^target_username=.*/target_username=$WHOAMI/g" hosts
sed -i "s/^base_dir=.*/base_dir=\"\/home\/{{target_username}}\/facebook5\"/g" hosts
if [ -z "$http_proxy" ]; then
    sed -i "s/^set_internal_proxy=.*/set_internal_proxy=no/g" hosts
fi

ansible-playbook -i hosts facebook5_workload.yml
if [ -f "$SSH_CONFIG_FILE.facebook5.old" ]; then
    mv "$SSH_CONFIG_FILE.facebook5.old" "$SSH_CONFIG_FILE"
fi

MODEL_WORK_DIR="/home/$WHOAMI/$FACEBOOK5_WL_GENERIC_NAME"
HOME_DIR="/home/$WHOAMI"

sudo tar xzf "$FACEBOOK5_WL_PROVISION_FILE.tar.gz" -C /opt
sudo chown -R pkb:sudo /opt/speccpu
