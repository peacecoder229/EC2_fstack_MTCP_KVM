#!/bin/bash

set -euo pipefail
#set -x

if [ ! "$#" == 2 ] ; then
  echo "Usage: $0 clusters_nr out_dir"
  exit 1
fi

eval "clusters_nr=$1"

eval "out_dir=$2"

fn_out="$out_dir/multiple_instance_config.json"

echo "[" > $fn_out
for i in  $(seq 0 $((clusters_nr - 1))); do
  echo " {" >> $fn_out
  echo "  \"server_ip\":\"127.0.0.1\"," >> $fn_out
  echo "  \"server_port\":\"$((i + 9001))\"," >> $fn_out
  echo "  \"db_name\":\"node-els-db$((i+1))\"," >> $fn_out
  echo "  \"db_ip\":\"127.0.0.1\"," >> $fn_out
  echo "  \"db_port\":\"$((i + 27018))\"" >> $fn_out
  echo " }" >> $fn_out
  if [ "$i" -lt "$((clusters_nr - 1))" ]; then
    echo " ," >> $fn_out
  fi
done
echo "]" >> $fn_out

