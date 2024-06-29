#!/usr/bin/env bash

WIDEDEEP_WL_GENERIC_NAME="wide_deep_large_ds"
WIDEDEEP_WL_PROVISION_FILE="widedeep_wlfiles"

WORKING_DIR=$(cd $(dirname "$0") && pwd)
WHOAMI=$(whoami)

ID_RSA_FILE=~/.ssh/id_rsa
SSH_CONFIG_FILE=~/.ssh/config
AUTH_KEYS_FILE=~/.ssh/authorized_keys
# generate ssh keys for localhost
if [ ! -f "$ID_RSA_FILE" ]; then
    yes y | ssh-keygen -t rsa -q -f "$ID_RSA_FILE" -N ''
fi
if [ -f "$SSH_CONFIG_FILE" ]; then
    mv "$SSH_CONFIG_FILE" "$SSH_CONFIG_FILE.widedeep.old"
fi
echo "Host *" > "$SSH_CONFIG_FILE"
echo "   StrictHostKeyChecking no" >> "$SSH_CONFIG_FILE"
cat "$ID_RSA_FILE.pub" >> "$AUTH_KEYS_FILE"

cat hosts | grep localhost
if [ $? -ne 0 ]; then
    sed -i "/^\[target\]/a localhost" hosts
fi
sed -i "s/^target_username=.*/target_username=$WHOAMI/g" hosts
sed -i "s/^base_dir=.*/base_dir=\"\/home\/{{target_username}}\/wide_deep_large_ds\"/g" hosts
if [ -z "$http_proxy" ]; then
    sed -i "s/^set_internal_proxy=.*/set_internal_proxy=no/g" hosts
fi

ansible-playbook -i hosts widedeep_workload.yml
#rm -r "$WORKING_DIR/$WIDEDEEP_WL_GENERIC_NAME"
if [ -f "$SSH_CONFIG_FILE.widedeep.old" ]; then
    mv "$SSH_CONFIG_FILE.widedeep.old" "$SSH_CONFIG_FILE"
fi

MODEL_WORK_DIR="/home/$WHOAMI/$WIDEDEEP_WL_GENERIC_NAME"
HOME_DIR="/home/$WHOAMI"
mkdir -pv $MODEL_WORK_DIR
tar xzf "$WIDEDEEP_WL_PROVISION_FILE.tar.gz" 
mv $WIDEDEEP_WL_PROVISION_FILE/* $MODEL_WORK_DIR
tar xzf model.tar.gz 
cd model/models
git checkout 5265de4727ed0969b59bae220b7d7ed46316a9d0
cd ../..
mv model/* $MODEL_WORK_DIR
mkdir -pv $MODEL_WORK_DIR/results

check_OS() {
	IS_UBUNTU=$(cat /etc/os-release | grep "^NAME" | grep Ubuntu | awk -F= '{print $2}')
	echo "Host OS is $IS_UBUNTU"
}

install_python3.6() {
	# install python 3.6
	sudo apt-get install build-essential checkinstall -y
	sudo apt-get install libreadline-gplv2-dev libncursesw5-dev libssl-dev -y
	sudo apt-get install libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev -y
	cd /usr/src
	sudo wget -c https://www.python.org/ftp/python/3.6.9/Python-3.6.9.tgz
	sudo tar xzf Python-3.6.9.tgz
	cd Python-3.6.9/
	sudo ./configure --enable-optimizations
	sudo make altinstall
	python3.6 -V
}

setup_python3.6() {
	# setup customized virtual python environment
	cd $HOME_DIR
	sudo apt install -y numactl
	sudo apt install -y virtualenv
	virtualenv --clear -p python3.6 --system-site-packages whl_with_3.6
#	source whl_with_3.6/bin/activate
}

check_OS
install_python3.6
setup_python3.6
#install_wheel_patch_1.14.0
#install_wheel_patch_1.14.1
#prepare_work_dir
#git_clone_model_directory
#install_wlfiles
#fetch_large_dataset
#fetch_eval_csv
#fetch_fp32_pretrained_data
#fetch_int8_pretrained_data
#preprocess_dataset
