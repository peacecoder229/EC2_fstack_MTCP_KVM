
if [ "$#" -ne 1 ]; then
  echo "Error. Usage: ./compile_data.sh <instance type>."
  exit
fi

instance_type=$1

exp_time=$(date -d 'today' | awk -F ' ' '{print $1$2$3$4$5$6}')

file_name=${exp_time}_${instance_type}.csv
#echo "Run No,Instance Id,Exp Time,Case No,VM Type,P-50,P-75,P-90,Avg RPS,TSC,Ref-Cycles,Instructions" > $file_name
echo "Run No,Instance Id,Exp Time,Case No,VM Type,P-50,P-75,P-90,Avg RPS,Avg User Utilization(%), Avg System Utilization(%)" > $file_name
for dir in drc_res_*; do
  echo $dir
  cd $dir
  cat result.csv >> ../$file_name
  cd ..
done
