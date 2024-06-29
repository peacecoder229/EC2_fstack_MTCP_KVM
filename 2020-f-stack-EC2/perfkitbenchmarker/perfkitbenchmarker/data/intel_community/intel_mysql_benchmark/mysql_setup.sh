#!/bin/bash

echo "$0 path"
if [ $# -ne 1 ];
then
	echo $#
	exit
fi

ps -ef | grep mysqld | grep -v grep | cut -c 9-15 | xargs sudo kill -9

path=$1
cd $path
sudo rm -rf mysql-5.7

echo "-----------------------------Starting to install MySQL------------------------------"
if [ ! -e "mysql-5.7.22-linux-glibc2.12-x86_64.tar.gz" ]; then
	wget  https://dev.mysql.com/get/Downloads/MySQL-5.7/mysql-5.7.22-linux-glibc2.12-x86_64.tar.gz
fi
tar zxmvf mysql-5.7.22-linux-glibc2.12-x86_64.tar.gz
mv mysql-5.7.22-linux-glibc2.12-x86_64 mysql-5.7
mkdir -p mysql-5.7/data
mkdir -p mysql-5.7/log
cp $path/intel_mysql_benchmark/my.cnf mysql-5.7/
cd mysql-5.7
sudo bin/mysqld --defaults-file=$path/mysql-5.7/my.cnf --initialize --user=root --basedir=$path/mysql-5.7 --datadir=$path/mysql-5.7/data 
sudo nohup bin/mysqld_safe --defaults-file=$path/mysql-5.7/my.cnf --user=root >mysqld_safe.log 2>&1 &
sleep 5
passwd=`sudo grep 'temporary password' log/mysqld.log | awk '{print $11}'`
echo "Old passwd="$passwd

newpasswd=123456
host=127.0.0.1
port=6306
socket=$path/mysql-5.7/mysqld.sock
echo "bin/mysqladmin -uroot -p password '$newpasswd' -P$port -S$socket"
sudo bin/mysqladmin -uroot -p$passwd password 123456 -P$port -S$socket

sudo bin/mysql -h$host -uroot -p$newpasswd -P$port -e "ALTER USER 'root'@'localhost' PASSWORD EXPIRE NEVER;"
result1=$?
sudo bin/mysql -h$host -uroot -p$newpasswd -P$port -e "GRANT ALL ON *.* TO 'root'@'%' IDENTIFIED BY '$newpasswd';"
result2=$?
sudo bin/mysql -h$host -uroot -p$newpasswd -P$port -e "flush privileges;"
result3=$?
sudo bin/mysql -h$host -uroot -p$newpasswd -P$port -e "create database sbtest;"
result4=$?
echo $result1" "$result2" "$result3" "$result4
if [ $result1 -ne 0 ] || [ $result2 -ne 0 ] || [ $result3 -ne 0 ] || [ $result4 -ne 0 ]
then
        echo "MySQL preparing Env Failed!" >>mysqld_safe.log 2>&1
else
        echo "MySQL preparing Env Done!" >>mysqld_safe.log 2>&1
fi
