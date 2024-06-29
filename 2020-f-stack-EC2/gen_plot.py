import matplotlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.pyplot import figure

dir_prefix = "/pnpdata/2020-f-stack-muktadir/ec2_exp_mc_mb_redis_drc_res"
intel_c5_12_data = pd.read_csv("{}/intel/c5.12xlarge/intel_c5_12.csv".format(dir_prefix));
intel_c5_4_data = pd.read_csv("{}/intel/c5.4xlarge/intel_c5_4.csv".format(dir_prefix));

amd_c5a_4_data = pd.read_csv("{}/amd/c5a.4xlarge/amd_c5a_4.csv".format(dir_prefix));
amd_c5a_12_data = pd.read_csv("{}/amd/c5a.12xlarge/amd_c5a_12.csv".format(dir_prefix));

time = ["13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23"]

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
print(intel_c5_12_data["reshup-min"])

# min
fig=plt.figure()
ax=fig.add_subplot(111)
ax.plot(time, intel_c5_12_data["reshup-min"], marker="v", ls='--', label='intel(c5_12)', color='black')
ax.plot(time, intel_c5_4_data["reshup-min"], marker="x", ls='--', label='intel(c5_4)', color='black')
ax.plot(time, amd_c5a_12_data["reshup-min"], marker="v", ls='-', label='amd(c5a_12)', color='blue')
ax.plot(time, amd_c5a_4_data["reshup-min"], marker="x", ls='-', label='amd(c5a_4)', color='blue')
ax.grid()
plt.xlabel('Time (7th April)(PDT)', fontsize=12)
plt.ylabel('Min Delay', fontsize=12)
plt.legend(loc='upper left')
fig.savefig('4_29_2021_memcached_c5_min.pdf')

# max
fig=plt.figure()
ax=fig.add_subplot(111)
ax.plot(time, intel_c5_12_data["reshup-max"], marker="v", ls='--', label='intel(c5_12)', color='black')
ax.plot(time, intel_c5_4_data["reshup-max"], marker="x", ls='--', label='intel(c5_4)', color='black')
ax.plot(time, amd_c5a_12_data["reshup-max"], marker="v", ls='-', label='amd(c5a_12)', color='blue')
ax.plot(time, amd_c5a_4_data["reshup-max"], marker="x", ls='-', label='amd(c5a_4)', color='blue')
ax.grid()
plt.xlabel('Time (29th April)(PDT)', fontsize=12)
plt.ylabel('Max Delay(ms)', fontsize=12)
plt.legend(loc='upper left')
fig.savefig('4_29_2021_memcached_c5_max.pdf')

# avg
fig=plt.figure()
ax=fig.add_subplot(111)
ax.plot(time, intel_c5_12_data["reshup-avg"], marker="v", ls='--', label='intel(c5_12)', color='black')
ax.plot(time, intel_c5_4_data["reshup-avg"], marker="x", ls='--', label='intel(c5_4)', color='black')
ax.plot(time, amd_c5a_12_data["reshup-avg"], marker="v", ls='-', label='amd(c5a_12)', color='blue')
ax.plot(time, amd_c5a_4_data["reshup-avg"], marker="x", ls='-', label='amd(c5a_4)', color='blue')
ax.grid()
plt.xlabel('Time (29th April)(PDT)', fontsize=12)
plt.ylabel('Average Delay (ms)', fontsize=12)
plt.legend(loc='upper left')
fig.savefig('4_29_2021_memcached_c5_avg.pdf')

# throughput
fig=plt.figure()
ax=fig.add_subplot(111)
ax.plot(time, intel_c5_12_data["hpthrput"], marker="v", ls='--', label='intel(c5_12)', color='black')
ax.plot(time, intel_c5_4_data["hpthrput"], marker="x", ls='--', label='intel(c5_4)', color='black')
ax.plot(time, amd_c5a_12_data["hpthrput"], marker="v", ls='-', label='amd(c5a_12)', color='blue')
ax.plot(time, amd_c5a_4_data["hpthrput"], marker="x", ls='-', label='amd(c5a_4)', color='blue')
ax.grid()
plt.xlabel('Time (29th April)(PDT)', fontsize=12)
plt.ylabel('Througput (Request/Second)', fontsize=12)
plt.legend(loc='upper left')
fig.savefig('4_29_2021_memcached_c5_thrput.pdf')

# p50 
fig=plt.figure()
ax=fig.add_subplot(111)
ax.plot(time, intel_c5_12_data["p50"], marker="v", ls='--', label='intel(c5_12)', color='black')
ax.plot(time, intel_c5_4_data["p50"], marker="x", ls='--', label='intel(c5_4)', color='black')
ax.plot(time, amd_c5a_12_data["p50"], marker="v", ls='-', label='amd(c5a_12)', color='blue')
ax.plot(time, amd_c5a_4_data["p50"], marker="x", ls='-', label='amd(c5a_4)', color='blue')
ax.grid()
plt.xlabel('Time (29th April)(PDT)', fontsize=12)
plt.ylabel('50th Percentile Delay (ms)', fontsize=12)
plt.legend(loc='upper left')
fig.savefig('4_29_2021_memcached_c5_p50.pdf')

# p75 
fig=plt.figure()
ax=fig.add_subplot(111)
ax.plot(time, intel_c5_12_data["p75"], marker="v", ls='--', label='intel(c5_12)', color='black')
ax.plot(time, intel_c5_4_data["p75"], marker="x", ls='--', label='intel(c5_4)', color='black')
ax.plot(time, amd_c5a_12_data["p75"], marker="v", ls='-', label='amd(c5a_12)', color='blue')
ax.plot(time, amd_c5a_4_data["p75"], marker="x", ls='-', label='amd(c5a_4)', color='blue')
ax.grid()
plt.xlabel('Time (29th April)(PDT)', fontsize=12)
plt.ylabel('75th Percentile Delay (ms)', fontsize=12)
plt.legend(loc='upper left')
fig.savefig('4_29_2021_memcached_c5_p75.pdf')

# p90
fig=plt.figure()
ax=fig.add_subplot(111)
ax.plot(time, intel_c5_12_data["p90"], marker="v", ls='--', label='intel(c5_12)', color='black')
ax.plot(time, intel_c5_4_data["p90"], marker="x", ls='--', label='intel(c5_4)', color='black')
ax.plot(time, amd_c5a_12_data["p90"], marker="v", ls='-', label='amd(c5a_12)', color='blue')
ax.plot(time, amd_c5a_4_data["p90"], marker="x", ls='-', label='amd(c5a_4)', color='blue')
ax.grid()
plt.xlabel('Time (29th April)(PDT)', fontsize=12)
plt.ylabel('90th Percentile Delay (ms)', fontsize=12)
plt.legend(loc='upper left')
fig.savefig('4_29_2021_memcached_c5_p90.pdf')


