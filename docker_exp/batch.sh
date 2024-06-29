# run just povray
FREQ=$1
echo "starting just povray"
/pnpdata/widedeep-povray.sh x xx 14 0-13 povray_14 $FREQ
#fun just infernece
echo "starting just mxnet inference"
/pnpdata/widedeep-povray.sh 14 0-13 x xx wnd_14 $FREQ
#run 50-50 povray and infernece
echo "starting 14 threads each inference and povray"
/pnpdata/widedeep-povray.sh 14 0-13 14 14-27 wnd_14_povray_14 $FREQ
#run 75% 25% inference 21 and povray 7
echo "starting 21 inference and 7 povray"
/pnpdata/widedeep-povray.sh 21 0-20 7 21-27 wnd_21_povray_7 $FREQ
#run 25% inferece  and 75% povray
echo "starting 7 inference and 21 povray"
/pnpdata/widedeep-povray.sh 7 0-6 21 7-27 wnd_7_povray_21  $FREQ
echo "finished all runs"

