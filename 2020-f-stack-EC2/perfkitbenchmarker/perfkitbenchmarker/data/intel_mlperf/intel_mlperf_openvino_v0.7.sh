#!/bin/bash

error() {
    local code="${3:-1}"
    if [[ -n "$2" ]];then
        echo "Error on or near line $1: $2; exiting with status ${code}"
    else
        echo "Error on or near line $1; exiting with status ${code}"
    fi
    exit "${code}"
}
trap 'error ${LINENO}' ERR

if [ "$1" != "" ]; then
    ncores=$1
else
    ncores=24
fi

sudo apt update
sudo apt-get install -y libtbb-dev python3-dev python3-pip cmake

CUR_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
# Update cmake to newer version required by openvino
sudo apt-get purge -y cmake
version=3.14
build=3
CMAKE_DIR=${CUR_DIR}/cmake-src
mkdir ${CMAKE_DIR}
cd ${CMAKE_DIR}
wget https://cmake.org/files/v$version/cmake-$version.$build.tar.gz
tar xfz cmake-$version.$build.tar.gz
cd cmake-$version.$build/
./bootstrap
make -j4
sudo make install
sudo ln -s /usr/local/bin/cmake /usr/bin/cmake
cmake --version
# End of update cmake version

SKIPS=" "
DASHES="================================================"

MLPERF_DIR=${CUR_DIR}/Local-MLPerf-Build
DEPS_DIR=${MLPERF_DIR}/dependencies

#====================================================================
# Build OpenVINO library (If not using publicly available openvino)
#====================================================================

echo " ========== Building OpenVINO libraries ==========="
echo ${SKIPS}

OPENVINO_DIR=${DEPS_DIR}/openvino-repo
git clone https://github.com/openvinotoolkit/openvino.git ${OPENVINO_DIR}

cd ${OPENVINO_DIR}
git checkout 8347556
git submodule update --init --recursive
mkdir build && cd build
cmake -DENABLE_VPU=OFF -DTHREADING=OMP \
    	-DENABLE_CLDNN=OFF \
    	-DENABLE_GNA=OFF \
    	-DENABLE_DLIA=OFF \
    	-DENABLE_TESTS=OFF \
    	-DENABLE_VALIDATION_SET=OFF \
    	-DNGRAPH_ONNX_IMPORT_ENABLE=OFF \
    	-DNGRAPH_DEPRECATED_ENABLE=FALSE \
        ..

TEMPCV_DIR=${OPENVINO_DIR}/inference-engine/temp/opencv_4*
OPENCV_DIRS=$(ls -d -1 ${TEMPCV_DIR} )
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${OPENCV_DIRS[0]}/opencv/lib


#make -j$(nproc)
make -j$ncores

#=============================================================
#       Build gflags
#=============================================================
echo ${SKIPS}
echo " ============ Building Gflags ==========="
echo ${SKIPS}

GFLAGS_DIR=${DEPS_DIR}/gflags

git clone https://github.com/gflags/gflags.git ${GFLAGS_DIR}
cd ${GFLAGS_DIR}
mkdir gflags-build && cd gflags-build
cmake .. && make


# Build boost
echo ${SKIPS}
echo "========= Building boost =========="
echo ${SKIPS}

BOOST_DIR=${DEPS_DIR}/boost
if [ ! -d ${BOOST_DIR} ]; then
        mkdir ${BOOST_DIR}
fi

cd ${BOOST_DIR}
wget https://dl.bintray.com/boostorg/release/1.72.0/source/boost_1_72_0.tar.gz
tar -xzf boost_1_72_0.tar.gz
cd boost_1_72_0
./bootstrap.sh --with-libraries=filesystem
./b2 --with-filesystem

#===============================================================

# Build loadgen
#===============================================================
echo ${SKIPS}
echo " =========== Building mlperf loadgenerator =========="
echo ${SKIPS}

MLPERF_INFERENCE_REPO=${DEPS_DIR}/mlperf-inference

if [ -d ${MLPERF_INFERENCE_REPO} ]; then
        rm -r ${MLPERF_INFERENCE_REPO}
fi

pip3 install absl-py numpy pybind11
#pip install absl-py numpy pybind11

git clone --recurse-submodules https://github.com/mlcommons/inference.git ${MLPERF_INFERENCE_REPO}

cd ${MLPERF_INFERENCE_REPO}/loadgen
git checkout 8507b86bb
mkdir build && cd build
cmake -DPYTHON_EXECUTABLE=`which python3` \
	..

make

cp libmlperf_loadgen.a ../

# =============================================================
#        Build ov_mlperf
#==============================================================

echo ${SKIPS}
echo " ========== Building ov_mlperf ==========="
echo ${SKIPS}

SOURCE_DIR=${MLPERF_DIR}/src
if [ -d ${SOURCE_DIR} ]; then
        sudo rm -r ${SOURCE_DIR}
fi

#git clone https://gitlab.devtools.intel.com/tattafos/mlperf-inference-v0.7-mobile-ov.git ${SOURCE_DIR}
SOURCE_DIR=$HOME/mlperf_v7_ov_cpp/closed/Intel/code/resnet/resnet-ov/

cd ${SOURCE_DIR}

if [ -d build ]; then
	rm -r build
fi

mkdir build && cd build

cmake -DInferenceEngine_DIR=${OPENVINO_DIR}/build/ \
                -DOpenCV_DIR=${OPENCV_DIRS[0]}/opencv/cmake/ \
		-DLOADGEN_DIR=${MLPERF_INFERENCE_REPO}/loadgen \
		-DBOOST_INCLUDE_DIRS=${BOOST_DIR}/boost_1_72_0 \
		-DBOOST_FILESYSTEM_LIB=${BOOST_DIR}/boost_1_72_0/stage/lib/libboost_filesystem.so \
		-DCMAKE_BUILD_TYPE=Release \
		-Dgflags_DIR=${GFLAGS_DIR}/gflags-build/ \
		..

make

echo ${SKIPS}
echo ${DASHES}
if [ -e ${SOURCE_DIR}/Release/ov_mlperf ]; then
        echo -e "\e[1;32m ov_mlperf built at ${SOURCE_DIR}/ov_mlperf \e[0m"
else
        echo -e "\e[0;31m ov_mlperf not built. Please check logs on screen\e[0m"
fi
echo ${DASHES}
