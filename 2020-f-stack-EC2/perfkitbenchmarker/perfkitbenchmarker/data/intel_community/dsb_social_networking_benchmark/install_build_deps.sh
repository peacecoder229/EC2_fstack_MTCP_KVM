#!/usr/bin/env bash

sudo apt-get update &&
git clone https://github.com/delimitrou/DeathStarBench.git &&
sudo apt-get -y install apt-transport-https ca-certificates curl software-properties-common &&
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add - &&

arch=$(arch)
if [[ $arch = "x86_64" ]]
then
    sudo add-apt-repository  "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" 
fi

sudo apt-get -y update &&
sudo apt-get -y install docker-ce &&
sudo service docker restart && 
sudo docker run hello-world &&
sudo curl -L https://github.com/docker/compose/releases/download/1.25.0/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose &&
sudo chmod +x /usr/local/bin/docker-compose &&
docker-compose --version 
