#!/bin/bash

echo "$0 path"
if [ $# -ne 1 ];
then
        echo $#
        exit
fi

path=$1

sudo echo "-----------------------------Starting to install sysbench------------------------------"
cd $path
git clone https://github.com/akopytov/sysbench.git
cd sysbench
./autogen.sh
./configure --with-mysql-includes=$path/mysql-5.7/include --with-mysql-libs=$path/mysql-5.7/lib
if [ -n "$LD_LIBRARY_PATH" ];
then
    echo "export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$path/mysql-5.7/lib" >> /opt/pkb/bashrc
else
    echo "export LD_LIBRARY_PATH=$path/mysql-5.7/lib" >> /opt/pkb/bashrc
fi
sudo su -c "source /opt/pkb/bashrc"
sudo make -j
sudo make install
