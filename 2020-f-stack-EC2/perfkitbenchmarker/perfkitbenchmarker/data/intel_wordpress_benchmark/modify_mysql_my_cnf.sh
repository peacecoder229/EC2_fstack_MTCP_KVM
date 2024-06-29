#!/bin/bash

if [ "$#" -le 1 ] ; then
  echo "Usage: $0 full_path_my.cnf [param_name param_value | ...]"
  exit 1
fi

arr_mysql_params_names=()
arr_mysql_params_values=()
arr_mysql_params_found=()
params_number=$#

echo "params_number=$params_number"

eval file_name=$1
file_name_tmp="$file_name"_tmp

echo "file_name = $file_name"
echo "file_name_tmp = $file_name_tmp"

idx=2
while [ $idx -le $# ]; do
  arr_mysql_params_names=("${arr_mysql_params_names[@]}" "${!idx}")
  idx=$(($idx + 1))
  arr_mysql_params_values=("${arr_mysql_params_values[@]}" "${!idx}")
  idx=$(($idx + 1))
  arr_mysql_params_found=("${arr_mysql_params_found[@]}" 0)
done

wp_params_nr=${#arr_mysql_params_names[@]}

while IFS= read -r line
do

  b_found=0;
  for idx in $(seq 0 $(($wp_params_nr - 1))); do

    mysql_params_name=${arr_mysql_params_names[$idx]}
    mysql_params_value=${arr_mysql_params_values[$idx]}
    #echo "$line"
    if [[ $line == "$mysql_params_name"* ]]; then
      echo "New: $mysql_params_name = $mysql_params_value"
      echo "$mysql_params_name = $mysql_params_value" >> "$file_name_tmp"
      arr_mysql_params_found[$idx]=1
      b_found=1
    fi

  done

  if [ "$b_found" == 0 ]; then
    echo "$line" >> "$file_name_tmp"
  fi

done < $file_name

for idx in $(seq 0 $(($wp_params_nr - 1))); do
  value_found=${arr_mysql_params_found[$idx]}
  if [ $value_found == 0 ]; then
    mysql_params_name=${arr_mysql_params_names[$idx]}
    mysql_params_value=${arr_mysql_params_values[$idx]}
    echo "$mysql_params_name = $mysql_params_value" >> "$file_name_tmp"
  fi
done

mv $file_name_tmp $file_name

