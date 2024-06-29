inference_threads=$1
inference_cpuset=$2
povray_threads=$3
povray_cpuset=$4

#cpu set example : 0-13 (use core 0 to core 13 to pin process to these threads)
result_path=$5
dir_save=$6
mkdir -p res/${dir_save}_$result_path-povray
mkdir -p res/${dir_save}_$result_path
# Set Cstat
#for cstat in `seq 1 3`
#do
#        cpupower idle-set -d $cstat
#done

#wait 60 second and collect emon save results in results_path 
#/pnpdata/Nizar/emon_run.sh 65 ${result_path}_2 $dir_save &
# Lock CPU frequency
#./hwpdesire.sh -f 2100000


docker run --cpuset-cpus=$povray_cpuset -v `pwd`/res/${dir_save}_$result_path-povray:/SPECcpu/result --cpuset-mems=0  -e INSTANCES=$povray_threads -e WORKLOAD=povray povray:latest &

docker run --cpuset-cpus=$inference_cpuset --cpuset-mems=0 -e OMP_NUM_THREADS=$inference_threads  -it --privileged wnd_nizar:latest &>res/${dir_save}_$result_path/wide_povray-ten.out

sleep 100
docker rm -f $(docker ps -aq)

#emon -stop
