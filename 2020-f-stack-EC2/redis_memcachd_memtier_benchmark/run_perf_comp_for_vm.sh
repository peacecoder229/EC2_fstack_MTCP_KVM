#./change_msr.py 0x199 0x1600 write
#echo "current cpu frequency is:"
#cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_cur_freq

echo "Test case",  "set_qps", "set_lat", "get_qps", "get_lat" >> memtier_total.csv
for cmd in disable_all3.sh 
do  sh $cmd
    sleep 1
    for ratio in "1:0" "1:4"
	do 
	if [ $1 -eq 1 ]; then		
         ./run_memtier_updated.py --ratio $ratio --mark host --host 127.0.0.1
        #do ./run_memtier_updated.py --ratio $ratio --mark VMNopatch$cmd --remote 1
        elif [ $1 -eq 2 ]; then
	./run_memtier_updated.py --ratio $ratio --mark sriov --host 192.168.5.47

	elif [ $1 -eq 3 ]; then
	./run_memtier_updated.py --ratio $ratio --mark virtio --host 192.168.122.42
	fi
        done
done
#taskset -c 5 memtier_benchmark -p 6379 --ratio=1:4 --pipeline=20 -d 1024 -c 100 --key-maximum 1000000 --key-pattern G:G -n 1000000

