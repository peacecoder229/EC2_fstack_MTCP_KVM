#!/bin/bash
echo  case_ddio_tx2_rx2_d4 >> comp.txt | grep 99.99 case_ddio_tx2_rx2_d4/* | sort -nk2 | awk -F _  '{print $3 " "  $4 "   " $5 " " $6}' | tail -n 10 >> comp.txt
echo  case_ddio_tx4_rx2_ex_d4  >> comp.txt | grep 99.99 case_ddio_tx4_rx2_ex_d4/* | sort -nk2 | awk -F _  '{print $3 " "  $4 "   " $5 " " $6}' | tail -n 10 >> comp.txt
echo  case_ddio_tx7_rx4_ex_d4  >> comp.txt | grep 99.99 case_ddio_tx7_rx4_ex_d4/* | sort -nk2 | awk -F _  '{print $3 " "  $4 "   " $5 " " $6}' | tail -n 10 >> comp.txt
