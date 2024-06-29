#!/bin/bash
val=$1
size=$2
dir_name=$3
if [[ $size == "B" ]];then
	total_size=$val
elif [[ $size == "K" ]];then
	total_size=$((val*1024))
elif [[ $size == "M" ]];then
	total_size=$((val*1024*1024))
elif [[ $size == "G" ]];then
	total_size=$((val*1024*1024*1024))
fi
echo "Total size is $total_size"
#mod_size=$((total_size-246-2))
#echo "$mod_size"
#if [[ $mod_size < "0" ]];then
#	break
#fi

string="a"
char="a"
for PF in $(seq 0 $total_size);do
	string=$string$char
	#PF=$((PF+1))
done

echo $string

#mkdir -p /usr/share/nginx/html/$dir_name
mkdir -p  /pnpdata/2020-f-stack-muktadir/nginx_fstack/html/$dir_name
cp /pnpdata/2020-f-stack-muktadir/nginx_exp/index.html /pnpdata/2020-f-stack-muktadir/nginx_fstack/html/$dir_name/
sed -i "s/<p>/<p>$string/g" /pnpdata/2020-f-stack-muktadir/nginx_fstack/html/$dir_name/index.html
#touch $file_name
#echo "$string" >> $file_name
#echo "string is $string"
