
instance_id=$(cat instance_id.txt)
subnet_2_id='subnet-0be3f3ca2f4fccd6d'
sec_grp='sg-08d0ef5fadfcb0c5d'

interface_id=$(aws ec2 create-network-interface \
--subnet-id $subnet_2_id \
--description "fstack3-sn2" --groups $sec_grp | jq -r '.NetworkInterface[0].NetworkInterfaceId')

wait 2

aws ec2 attach-network-interface --network-interface-id $interface_id --instance-id $instance_id --device-index 1

#sudo apt-get update
#sudo apt-get install build-essential
#git clone https://github.com/F-Stack/f-stack

