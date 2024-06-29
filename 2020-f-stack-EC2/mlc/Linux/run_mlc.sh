case_no=$1
vm_type=$2
instance_id=$3
run_no=$4
core_no=$5

c_core=$(($core_no-1))
k_core_begin=0
k_core_end=$(($core_no-2))

echo "Running mlc exp for $case_no and $vm_type vm."

case "$vm_type" in
  primary)
    for i in {1..4}; do
       echo "Running ./mlc --loaded_latency -W12 -b200000 -t180 -c$c_core -k$k_core_begin-$k_core_end -d0 > /home/ubuntu/$i.txt"
      #./mlc --loaded_latency -W12 -t20  -c$c_core -k$k_core_begin-$k_core_end -d0  > /home/ubuntu/$i.txt
      ./mlc --loaded_latency -W12 -t180 -c7 -k0-6 -d0  > /home/ubuntu/$i.txt
      sleep 2
    done
    #./mlc --loaded_latency -W12 -b200000 -t180 -c7 -k0-6 -d0 > /home/ubuntu/result.txt
    ;;

  secondary)
    if [[ $case_no == "case_2" ]]; then
      echo "Running ./mlc --loaded_latency -W12 -b200000 -t180  -c7 -k0-6 -d0 > /home/ubuntu/$i.txt"
      for i in {1..4}; do
        #./mlc --loaded_latency -W12 -b200000 -t180  -c$c_core -k$k_core_begin-$k_core_end -d0 > /home/ubuntu/$i.txt
        ./mlc --loaded_latency -W12 -b200000 -t180  -c7 -k0-6 -d0 > /home/ubuntu/$i.txt
        sleep 2
      done
    else
      sleep 750s
    fi
    ;;
  *)
    echo "VM Type should be primary or secondary."
    exit 1
esac

totalLat=0
totalThrput=0
for i in {1..4}; do
  if [[ -f "/home/ubuntu/$i.txt" ]]; then
    l=$(tail -1 "/home/ubuntu/$i.txt" | awk '{print $2}')
    t=$(tail -1 "/home/ubuntu/$i.txt" | awk '{print $3}')
    totalLat=$(bc <<< "$l+$totalLat")
    totalThrput=$(bc <<< "$t+$totalThrput")
  fi
done

latency=$(bc <<< "$totalLat/4")
thrput=$(bc <<< "$totalThrput/4")
exp_time=$(date -d 'today' | awk -F ' ' '{print $1$2$3$4$5$6}')
file_name="/home/ubuntu/drc_res_${case_no}_${vm_type}_${instance_id}"
echo "$run_no,$instance_id,$exp_time,$case_no,$vm_type,$latency,$thrput" > $file_name
