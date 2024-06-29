#!/usr/bin/env bash

WIDEDEEP_WL_GENERIC_NAME="wide_deep_large_ds"

WORKING_DIR=$(cd $(dirname "$0") && pwd)
WHOAMI=$(whoami)

install_tensorflow1.14.0() {
	echo "-I- Running Tensorflow 1.14.0"
	install_python3.6
	install_wheel_patch_1.14.0
}

install_tensorflow1.14.1() {
	echo "-I- Running Tensorflow 1.14.1"
	install_python3.6
	install_wheel_patch_1.14.1
}

install_python3.6() {
	sudo apt-get install build-essential checkinstall -y
	sudo apt-get install libreadline-gplv2-dev libncursesw5-dev libssl-dev -y
	sudo apt-get install libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev -y
	cd /usr/src
	sudo wget -c https://www.python.org/ftp/python/3.6.9/Python-3.6.9.tgz
	sudo tar xzf Python-3.6.9.tgz
	cd Python-3.6.9/
	sudo ./configure --enable-optimizations
	sudo make altinstall
	python3.6 -V
}

setup_python3.6() {
	cd ~
	sudo apt install virtualenv
	virtualenv --clear -p python3.6 --system-site-packages whl_with_3.6
	source whl_with_3.6/bin/activate
	sudo apt install numactl
}

install_wheel_patch_1.14.0() {
	cd ~
	sudo apt install virtualenv
	virtualenv --clear -p python3.6 --system-site-packages whl_with_3.6
	source whl_with_3.6/bin/activate
	rm -rf ~/.local/lib/python3.6/site-packages/tensor*
	pip install -U pip
	pip install -U setuptools
	pip install tensorflow==1.14.0
	pip list
}

install_wheel_patch_1.14.1() {
	cd ~
	sudo apt install virtualenv
	virtualenv --clear -p python3.6 --system-site-packages whl_with_3.6
	source whl_with_3.6/bin/activate
	rm -rf ~/.local/lib/python3.6/site-packages/tensor*
	pip install -U pip
	pip install -U setuptools
	pip install $MODEL_WORK_DIR/tensorflow-1.14.1-cp36-cp36m-linux_x86_64.whl
	pip list
}

fetch_fp32_pretrained_data() {
	cd $MODEL_WORK_DIR
	wget -c https://storage.googleapis.com/intel-optimized-tensorflow/models/v1_5/wide_deep_int8_pretrained_model.pb
}

fetch_int8_pretrained_data() {
	cd $MODEL_WORK_DIR
	wget -c https://storage.googleapis.com/intel-optimized-tensorflow/models/v1_5/wide_deep_fp32_pretrained_model.pb
}

run_inference() {
	mkdir -p $MODEL_WORK_DIR/results
	cd $MODEL_WORK_DIR/models/benchmarks

	WORKING_DIR=/opt/pkb
	mkdir -pv $WORKING_DIR/results
	rm -f $WORKING_DIR/results/*

	echo RUNNING python launch_benchmark.py \
	--model-name wide_deep_large_ds \
	--precision $PRECISION \
	--mode inference \
	--framework tensorflow \
	--$BENCHMARK_MODE \
	--batch-size $BATCH_SIZE \
	--in-graph "$MODEL_WORK_DIR/wide_deep_"$PRECISION"_pretrained_model.pb" \
	--data-location $MODEL_WORK_DIR/eval_preprocessed_eval.tfrecords \
	--num-intra-threads $INTRA_THREADS \
	--num-inter-threads $INTER_THREADS \
	--num-cores $NUM_CORES \
	--socket-id 0 \
	--verbose \
	--disable-tcmalloc=False \
	--num_omp_threads=$OMP_THREADS \
	--output-dir=$WORKING_DIR/results \
	KMP_BLOCKTIME=1 
	
	python launch_benchmark.py \
	--model-name wide_deep_large_ds \
	--precision $PRECISION \
	--mode inference \
	--framework tensorflow \
	--$BENCHMARK_MODE \
	--batch-size $BATCH_SIZE \
	--in-graph "$MODEL_WORK_DIR/wide_deep_"$PRECISION"_pretrained_model.pb" \
	--data-location $MODEL_WORK_DIR/eval_preprocessed_eval.tfrecords \
	--num-intra-threads $INTRA_THREADS \
	--num-inter-threads $INTER_THREADS \
	--num-cores $NUM_CORES \
	--socket-id 0 \
	--verbose \
	--disable-tcmalloc=False \
	--num_omp_threads=$OMP_THREADS \
	--output-dir=$WORKING_DIR/results \
	KMP_BLOCKTIME=1 \
	2>&1  
}

run_max_inference() {
	mkdir -p $MODEL_WORK_DIR/results
	cd $MODEL_WORK_DIR/models/benchmarks

	WORKING_DIR=/opt/pkb
	mkdir -pv $WORKING_DIR/results
	rm -f $WORKING_DIR/results/*

	DATAFILE="$WORKING_DIR"/inference_throughput_"$PRECISION".txt
	touch $DATAFILE

	for N_OMP in `seq 1 1 $NUM_CORES`
		do
		for N_INTRA in `seq 1 1 $NUM_CORES`
			do
				echo -n "PRECISION:$PRECISION, BATCH:$BATCH_SIZE, NCORES:$NUM_CORES, N_INTRA:$N_INTRA, N_INTER:2, N_OMP:$N_OMP, "  >> $DATAFILE
	
				python launch_benchmark.py \
				--model-name wide_deep_large_ds \
				--precision $PRECISION \
				--mode inference \
				--framework tensorflow \
				--$BENCHMARK_MODE \
				--batch-size $BATCH_SIZE \
				--in-graph "$MODEL_WORK_DIR/wide_deep_"$PRECISION"_pretrained_model.pb" \
				--data-location $MODEL_WORK_DIR/eval_preprocessed_eval.tfrecords \
				--num-intra-threads $INTRA_THREADS \
				--num-inter-threads $INTER_THREADS \
				--num-cores $NUM_CORES \
				--socket-id 0 \
				--verbose \
				--disable-tcmalloc=False \
				--num_omp_threads=$OMP_THREADS \
				--output-dir=$WORKING_DIR/results \
				KMP_BLOCKTIME=1 \
				2>&1  | grep Throughput >> $DATAFILE
			
			done
	    done
}  

MODEL_WORK_DIR="$HOME/wide_deep_large_ds"

rm -f /opt/pkb/results/*

while [ "$1" != "" ]; do
    PARAM=`echo $1 | awk -F= '{print $1}'`
    VALUE=`echo $1 | awk -F= '{print $2}'`
    case $PARAM in
		--run_mode)
			RUN_MODE=$VALUE
			;;
		--benchmark_mode)
			BENCHMARK_MODE=$VALUE
			;;
		--vcpu)
			VCPU=$VALUE
			NUM_CORES=$(( $VCPU/2 ))
			;;
		--framework)
			FRAMEWORK=$VALUE
			;;
		--precision)
			PRECISION=$VALUE
			;;		
		--batchsize)
			BATCH_SIZE=$VALUE
			;;		
		--intra_threads)
			INTRA_THREADS=$VALUE
			;;		
		--inter_threads)
			INTER_THREADS=$VALUE
			;;		
		--omp_threads)
			OMP_THREADS=$VALUE
			;;	
        *)
            echo "ERROR: unknown COMMAND LINE parameter \"$PARAM\""
            exit 1
            ;;
    esac
    shift
done

case $FRAMEWORK in
	tensorflow-1.14.0)  
		echo "FRAMEWORK = $FRAMEWORK selected."
		install_tensorflow1.14.0
		;;
	tensorflow-1.14.1)
		echo "FRAMEWORK = $FRAMEWORK selected."
		install_tensorflow1.14.1
		;;
	*)
        echo "ERROR: unknown FRAMEWORK parameter \"$FRAMEWORK\""
        exit 1
        ;;
esac

case $RUN_MODE in
	default)  
		echo "RUN_MODE = $RUN_MODE selected."
		BATCH_SIZE=512
		NUM_CORES=$(( $VCPU/2 ))
		INTRA_THREADS=$(( $VCPU/2 ))
		INTER_THREADS=2
		OMP_THREADS=$(( $VCPU/2 ))
		run_inference
		;;
	custom)
		echo "RUN_MODE = $RUN_MODE selected."
		run_inference
		;;
	optimize)
		echo "RUN_MODE = $RUN_MODE selected."
		run_max_inference
		;;
	*)
        echo "ERROR: unknown RUN_MODE parameter \"$RUN_MODE\""
        exit 1
        ;;
esac
