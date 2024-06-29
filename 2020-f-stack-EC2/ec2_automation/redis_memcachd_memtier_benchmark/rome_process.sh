#/bin/bash
cd $2
grep "${1}     " ip192.168.100.180* |  awk '($3 > 90 ) && ($3 < 91) {print $0}' | sort -nk2 | tail -n 15
