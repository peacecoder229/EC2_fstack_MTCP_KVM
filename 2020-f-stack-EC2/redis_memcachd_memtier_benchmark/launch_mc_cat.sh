#!/bin/bash


for i in {2..2};
do
	lp=$(( i*14 ))
	lpc=$(( lp/4 ))
	hp=$(( 56-lp ))
#	echo "./rdt_mixcomborun.sh $hp deepsjeng_r $lp deepsjeng_r deepsjeng${hp}_deepsjeng${lp}_static_rdt"
if [ ${!#} == "qos" ]
then
	#qosarr=( ["100"]="0x7ff" ["60"]="0xf" ["30"]="0x3" ["10"]="0x3" )
	#qosarr=( ["60"]="0xf" ["10"]="x3" )
	#qosarr=( ["10"]="0x3" ["10"]="0xf" ["10"]="0x3f" ["30"]="0x3" ["30"]="0xf" ["30"]="0x3f" ["80"]="0x3" ["80"]="0xf" ["80"]="0x3f" )
	#qosarr2=( ["10"]="0x3" ["10"]="0xf" ["10"]="0x3f" ["30"]="0x3" ["30"]="0xf" ["30"]="0x3f" ["80"]="0x3" ["80"]="0xf" ["80"]="0x3f" )
        #cat=( ["0x3"]="0x7fc" ["0xf"]="0x7f0" ["0x3f"]="0x7c0" )
        #cat=( ["0x7ff"]="0x7ff" )
	cat=( ["0x3"]="0x7fc" )	
	#for mba in  "40" "100";
	for mba in "100";
	do
		for lpcat in ${!cat[@]};
		do
			hpt=$(( ${lp}/2 ))
			export LPW=${lpcat}
			export HPW=${cat[${lpcat}]}
			export LPMB=${mba}
			export LP_CORES=${hpt}-27,$(( 56+hpt ))-83
			source /root/hwdrc-validation-framework/controller.inc.sh
			set_mba_llc  >> pqos.log
			#for work in "x264_r";
			./sweep_mc_con_collect_stat.sh "on"
	done
done


else
	pqos -R
	./mixcomborun.sh $hp x264_r $lp mcf_r  x264${hp}_mcf${lp}_noqos
fi
done



