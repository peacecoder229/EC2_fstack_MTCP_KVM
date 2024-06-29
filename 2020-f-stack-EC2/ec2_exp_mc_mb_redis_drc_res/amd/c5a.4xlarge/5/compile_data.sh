file_name=amd_c5a_4_5.csv
echo "Time,stc-edc,total core,instance,connections,reshup-min,reshup-max,reshup-avg,p10,p20,p30,p40,p50,p60,p75,p90,hpthrput,HT" > $file_name
for dir in */; do
  cd $dir
  cat memcached_d256b_instance_run_sweep.txt >> ../$file_name
  cd ..
done
