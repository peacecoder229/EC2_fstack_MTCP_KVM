import matplotlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.pyplot import figure

intel_c5_12_data = pd.read_csv("/pnpdata/2020-f-stack-muktadir/ec2_exp_nginx_drc_res/intel/c5.12xlarge/nginx_intel_c5_12_compiled.csv");

amd_c5a_12_data = pd.read_csv("/pnpdata/2020-f-stack-muktadir/ec2_exp_nginx_drc_res/amd/c5a.12xlarge/nginx_amd_c5a_12_compiled.csv");

time = ["16:20", "16:50", "17:10", "17:30", "17:50", "18:10", "18:30", "18:50", "19:10", "19:30", "19:50"]

def create_plot(m, time, file_name):
    metric = m 
    x_label = time
    
    fig=plt.figure()
    ax=fig.add_subplot(111)
    ax.plot(time, intel_data[metric], marker="v", ls='--', label='intel', color='black')
    ax.plot(time, amd_data[metric], marker="x", ls='--', label='amd', color='black')

    #ax.set_ylim(ymin=0)
    ax.grid()
    plt.xlabel(x_label, fontsize=6)
    plt.ylabel(metric, fontsize=12)
    plt.legend(loc='upper left')
    fig.savefig(file_name)

#create_plot('reshup-min', '3/31/2021', '4_5_2021_memcached_c5_min.pdf')


# p50 
fig=plt.figure()
ax=fig.add_subplot(111)
ax.plot(time, intel_c5_12_data["p50"], marker="v", ls='--', label='intel(c5_12)', color='black')
ax.plot(time, amd_c5a_12_data["p50"], marker="x", ls='--', label='amd(c5a_12)', color='blue')
ax.grid()
plt.xlabel('Time (15thApril)(PDT)', fontsize=12)
plt.ylabel('Latency p50 (ms)', fontsize=12)
plt.legend(loc='upper left')
fig.savefig('4_15_2021_nginx_c5_p_50.pdf')

# p75 
fig=plt.figure()
ax=fig.add_subplot(111)
ax.plot(time, intel_c5_12_data["p75"], marker="v", ls='--', label='intel(c5_12)', color='black')
ax.plot(time, amd_c5a_12_data["p75"], marker="x", ls='--', label='amd(c5a_12)', color='blue')
ax.grid()
plt.xlabel('Time (15th April)(PDT)', fontsize=12)
plt.ylabel('Latency p75 (ms)', fontsize=12)
plt.legend(loc='upper left')
fig.savefig('4_15_2021_nginx_c5_p_75.pdf')

# p90
fig=plt.figure()
ax=fig.add_subplot(111)
ax.plot(time, intel_c5_12_data["p90"], marker="v", ls='--', label='intel(c5_12)', color='black')
ax.plot(time, amd_c5a_12_data["p90"], marker="x", ls='--', label='amd(c5a_12)', color='blue')
ax.grid()
plt.xlabel('Time (15th April)(PDT)', fontsize=12)
plt.ylabel('Latency p90 (ms)', fontsize=12)
plt.legend(loc='upper left')
fig.savefig('4_15_2021_nginx_c5_p_90.pdf')
