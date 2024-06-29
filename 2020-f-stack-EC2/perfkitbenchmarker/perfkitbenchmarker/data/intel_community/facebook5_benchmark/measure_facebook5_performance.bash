#!/usr/bin/env bash

rm -rf /opt/speccpu/result

mkdir /opt/speccpu/result
cd /opt/speccpu
./run-gcc5.3.1-default.sh
