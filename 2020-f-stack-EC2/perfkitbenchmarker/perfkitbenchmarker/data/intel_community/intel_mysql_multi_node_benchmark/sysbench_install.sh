echo "$0 path"
if [ $# -ne 1 ];
then
	echo $#
	exit
fi

path=$1

sudo echo "-----------------------------Starting to install sysbench------------------------------"
cd $path
sudo git clone https://github.com/akopytov/sysbench.git
cd sysbench
sudo ./autogen.sh
sudo ./configure
sudo make -j
sudo make install