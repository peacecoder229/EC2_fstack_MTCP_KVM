#!/bin/bash
source /etc/bash.bashrc
BOOST_ROOT=$HOME/boost_1_72_0
MKLROOT_PATH=$HOME/mkl2019_3
DATASET_PATH="/opt/pkb/MLPERF_DIR/dataset-imagenet-ilsvrc2012-val/"
EULER_PATH=$HOME/mlperf_submit/pytorch/third_party/ideep/euler
LD_LIB_PATH=$LD_LIBRARY_PATH:/opt/intel/lib/intel64:/opt/intel/mkl/lib/intel64:$HOME/mlperf_submit/pytorch/build/lib/
LD_PRELOAD_PATH=/opt/intel/compilers_and_libraries/linux/lib/intel64/libiomp5.so
CAFFE2_DIR_PATH=$HOME/mlperf_submit/pytorch
LOADGEN_DIR_PATH=$HOME/mlperf_submit/pytorch/third_party/mlperf_inference
images="/lustre/dataset/imagenet/img_raw/ILSVRC2012_img_val/"
ICC_PATH=/opt/intel/compilers_and_libraries_2019.5.281/linux/bin/compilervars.sh
GCC7_PATH=/opt/rh/devtoolset-7/enable
if [ "$1" != "" ]; then
    ncores=$1
else
    ncores=24
fi
export BOOST_ROOT=$BOOST_ROOT
export MKLROOT=$MKLROOT_PATH
export PATH=/usr/local/bin:/usr/local/bin:/usr/bin:$HOME/bin
source /opt/intel/mkl/bin/mklvars.sh intel64
export PATH=/opt/intel/bin:/usr/local/bin:/usr/bin
export LD_LIBRARY_PATH=$LD_LIB_PATH
source $ICC_PATH -arch intel64 -platform linux
export LD_PRELOAD=$LD_PRELOAD_PATH
export PYTHONPATH=$HOME/mlperf_submit/pytorch/build/

image_net_2012_label_file=/opt/pkb/MLPERF_DIR
mkdir -p $HOME/mlperf_submit
cd $HOME/mlperf_submit

checkout_pytorch(){
echo "Prepare Pytorch source code"
pip install pyyaml numpy typing
git clone https://github.com/pytorch/pytorch.git
cd $HOME/mlperf_submit/pytorch
git fetch origin pull/25235/head:mlperf
git checkout mlperf
git submodule update --init --recursive
}

build_pytorch_mkldnn(){
echo "Check Pytorch build"
cd $HOME/mlperf_submit/pytorch
make clean
git submodule update --init --recursive
export MKLROOT=$MKLROOT_PATH
export CAFFE2_USE_MKLDNN=ON
export MKLDNN_USE_CBLAS=ON
export USE_OPENMP=ON
export CAFFE2_USE_EULER=OFF
python setup.py build
}

build_euler(){
echo "Build Euler kernel"
export BOOST_ROOT=$BOOST_ROOT
source $ICC_PATH -arch intel64 -platform linux
cd $HOME/mlperf_submit/pytorch
cd third_party/ideep/euler/
make clean
mkdir build; cd build
source $GCC7_PATH
cmake .. -DCMAKE_C_COMPILER=icc -DCMAKE_CXX_COMPILER=icpc -DWITH_VNNI=2
make -j
}

build_pytorch_euler(){
echo "Build Pytorch with Euler kernel"
cd $HOME/mlperf_submit/pytorch
git submodule update --init --recursive
make clean
source $GCC7_PATH
export MKLROOT=$MKLROOT_PATH
export CAFFE2_USE_MKLDNN=ON
export MKLDNN_USE_CBLAS=ON
export USE_OPENMP=ON
export CAFFE2_USE_EULER=ON
python setup.py build
}

build_mlperf(){
echo "Build mlperf inference_v0.5"
cd $HOME/mlperf_submit/pytorch
git clone https://github.com/mlperf/inference_results_v0.5.git
cp -r inference_results_v0.5/closed/Intel/code/resnet/pytorch-caffe2 mlperf-inference-loadgen-app-cpp
chmod u+x mlperf-inference-loadgen-app-cpp/scripts/*.sh
chmod u+x mlperf-inference-loadgen-app-cpp/loadrun/*.sh
copy_int8models
cd $HOME/mlperf_submit/pytorch/mlperf-inference-loadgen-app-cpp/scripts
sed -i -e "s@$images@$DATASET_PATH@" run_mlperf.sh test_tools.sh
sed -i -e "s@EULER_ROOT=.*@EULER_ROOT=$EULER_PATH@" run_mlperf.sh
sed -i -e "s@export LD_LIBRARY_PATH=.*@export LD_LIBRARY_PATH=$LD_LIB_PATH@" run_mlperf.sh test_tools.sh
sed -i -e "s@export LD_PRELOAD=.*@export LD_PRELOAD=$LD_PRELOAD_PATH@" test_tools.sh
sed -i -e "s@CAFFE2_DIR=.*@CAFFE2_DIR=$CAFFE2_DIR_PATH@" test_tools.sh Makefile
sed -i -e "s@BOOST_DIR=.*@BOOST_DIR=$BOOST_ROOT@" Makefile
cp $image_net_2012_label_file/val.txt ./val.txt
source $GCC7_PATH
make clean; make -j
NTHREADS=$ncores ./run_mlperf.sh -i1 -b1 -r50000 -Eeuler -tresnet50 -s1
}

copy_int8models(){
echo "using pre-built int8 models"
cd $HOME/mlperf_submit/pytorch/mlperf-inference-loadgen-app-cpp && mkdir -p models/resnet50
models_src=/opt/pkb/MLPERF_DIR/models.euler/resnet50
models_dest=$HOME/mlperf_submit/pytorch/mlperf-inference-loadgen-app-cpp/models/resnet50
cp $models_src/init_net_int8_euler.pb $models_dest/init_net_int8_euler.pb
cp $models_src/predict_net_int8_euler_lat.pbtxt $models_dest/predict_net_int8_euler_lat.pbtxt
cp $models_src/predict_net_int8_euler.pbtxt $models_dest/predict_net_int8_euler.pbtxt
}

build_pytorch_backend(){
echo "Build Pytorch backend"
export MKLROOT=$MKLROOT_PATH
cd $HOME/mlperf_submit/pytorch/mlperf-inference-loadgen-app-cpp/scripts/backend
sed -i -e "s@BOOST_DIR=.*@BOOST_DIR=$BOOST_ROOT@" Makefile
sed -i -e "s@CAFFE2_DIR=.*@CAFFE2_DIR=$CAFFE2_DIR_PATH@" Makefile
make clean
make -j
}

build_loadgen(){
echo "Build loadgen version 55c0ea4e772634107f3e67a6d0da61e6a2ca390d"
source $GCC7_PATH
cd $HOME/mlperf_submit/
pip install absl-py numpy wheel
git clone --recurse-submodules https://github.com/mlperf/inference.git  $HOME/mlperf_submit/pytorch/third_party/mlperf_inference
git checkout 55c0ea4e772634107f3e67a6d0da61e6a2ca390d
cd $HOME/mlperf_submit/pytorch/third_party/mlperf_inference/loadgen
git apply mlperf_submit/pytorch/mlperf-inference-loadgen-app-cpp/mlperf_inference.patch
CFLAGS="-std=c++14 -O3" python setup.py bdist_wheel
pip install --force-reinstall dist/mlperf_loadgen-*.whl
cd build
cmake .. && cmake --build .
cp libmlperf_loadgen.a ../
cp libmlperf_loadgen.a ../../
}

build_loadrun(){
echo "Build loadrun"
export MKLROOT=$MKLROOT_PATH
cd $HOME/mlperf_submit/pytorch/mlperf-inference-loadgen-app-cpp/scripts/backend
make clean
make -j
cd ../../loadrun
sed -i -e "s@BOOST_DIR=.*@BOOST_DIR=$BOOST_ROOT@" Makefile
sed -i -e "s@MKLROOT=.*@MKLROOT=$MKLROOT_PATH@" Makefile
sed -i -e "s@CAFFE2_DIR=.*@CAFFE2_DIR=$CAFFE2_DIR_PATH@" Makefile netrun.sh loadrun.sh single_stream.sh
sed -i -e "s@LOADGEN_DIR=.*@LOADGEN_DIR=$LOADGEN_DIR_PATH@" Makefile
sed -i -e "s@export LD_PRELOAD=.*@export LD_PRELOAD=$LD_PRELOAD_PATH@" netrun.sh single_stream.sh
sed -i -e "s@$images@$DATASET_PATH@" netrun.sh single_stream.sh loadrun.sh
make clean
make -j
cp ${image_net_2012_label_file}/val.txt ./val.txt
cp $HOME/mlperf_submit/pytorch/third_party/mlperf_inference/v0.5/mlperf.conf ./
}

checkout_pytorch
build_euler
build_pytorch_euler
build_mlperf
build_pytorch_backend
build_loadgen
build_loadrun
