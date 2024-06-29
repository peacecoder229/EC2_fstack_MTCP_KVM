pushd /home/ubuntu/DeathStarBench/hotelReservation
ip_addr = $(uname -n | awk -F'-' '{print $2"."$3"."$4"."$5}')
sed -i 's/x.x.x.x/${ip_addr}/g' config.json
popd
