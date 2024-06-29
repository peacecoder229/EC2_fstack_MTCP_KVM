import matplotlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.pyplot import figure

intel_c5_4_data_1 = pd.read_csv("/pnpdata/2020-f-stack-muktadir/ec2_exp_mc_mb_redis_drc_res/intel/c5.4xlarge/1/intel_c5_4_1.csv");
intel_c5_4_data_2 = pd.read_csv("/pnpdata/2020-f-stack-muktadir/ec2_exp_mc_mb_redis_drc_res/intel/c5.4xlarge/2/intel_c5_4_2.csv");
intel_c5_4_data_3 = pd.read_csv("/pnpdata/2020-f-stack-muktadir/ec2_exp_mc_mb_redis_drc_res/intel/c5.4xlarge/3/intel_c5_4_3.csv");
intel_c5_4_data_4 = pd.read_csv("/pnpdata/2020-f-stack-muktadir/ec2_exp_mc_mb_redis_drc_res/intel/c5.4xlarge/4/intel_c5_4_4.csv");
intel_c5_4_data_5 = pd.read_csv("/pnpdata/2020-f-stack-muktadir/ec2_exp_mc_mb_redis_drc_res/intel/c5.4xlarge/5/intel_c5_4_5.csv");

amd_c5a_4_data_1 = pd.read_csv("/pnpdata/2020-f-stack-muktadir/ec2_exp_mc_mb_redis_drc_res/amd/c5a.4xlarge/1/amd_c5a_4_1.csv");
amd_c5a_4_data_2 = pd.read_csv("/pnpdata/2020-f-stack-muktadir/ec2_exp_mc_mb_redis_drc_res/amd/c5a.4xlarge/2/amd_c5a_4_2.csv");
amd_c5a_4_data_3 = pd.read_csv("/pnpdata/2020-f-stack-muktadir/ec2_exp_mc_mb_redis_drc_res/amd/c5a.4xlarge/3/amd_c5a_4_3.csv");
amd_c5a_4_data_4 = pd.read_csv("/pnpdata/2020-f-stack-muktadir/ec2_exp_mc_mb_redis_drc_res/amd/c5a.4xlarge/4/amd_c5a_4_4.csv");
amd_c5a_4_data_5 = pd.read_csv("/pnpdata/2020-f-stack-muktadir/ec2_exp_mc_mb_redis_drc_res/amd/c5a.4xlarge/5/amd_c5a_4_5.csv");

time = ["13", "14", "14.5", "15", "15.5", "16", "16.5", "17", "18", "19"]
 
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

# min
fig, axs = plt.subplots(2, sharex=True)
axs[0].plot(time, intel_c5_4_data_1["reshup-min"], marker="1", ls='--', label='Instance 1', color='black')
axs[0].plot(time, intel_c5_4_data_2["reshup-min"], marker="|", ls='--', label='Instance 2', color='blue')
axs[0].plot(time, intel_c5_4_data_3["reshup-min"], marker="+", ls='--', label='Instance 3', color='green')
axs[0].plot(time, intel_c5_4_data_4["reshup-min"], marker="x", ls='--', label='Instance 4', color='orange')
axs[0].plot(time, intel_c5_4_data_5["reshup-min"], marker="4", ls='--', label='Instance 5', color='red')
axs[0].set_title("5 EC2 c5a.4x(Intel) instances ");
axs[1].plot(time, amd_c5a_4_data_1["reshup-min"], marker="1", ls='--', label='Instance 1', color='black')
axs[1].plot(time, amd_c5a_4_data_2["reshup-min"], marker="|", ls='--', label='Instance 2', color='blue')
axs[1].plot(time, amd_c5a_4_data_3["reshup-min"], marker="+", ls='--', label='Instance 3', color='green')
axs[1].plot(time, amd_c5a_4_data_4["reshup-min"], marker="x", ls='--', label='Instance 4', color='orange')
axs[1].plot(time, amd_c5a_4_data_5["reshup-min"], marker="4", ls='--', label='Instance 5', color='red')
axs[1].set_title("5 EC2 c5a.4x(AMD) instances ");

for ax in axs.flat:
    ax.set(xlabel= 'Time (6th April)(PDT)', ylabel='Min Delay')

for ax in axs.flat:
    ax.label_outer()

#for ax in axs.flat:
#    ax.legend(loc='upper left')

fig.savefig('4_7_2021_memcached_c5_min.pdf')

# max
fig, axs = plt.subplots(2, sharex=True)
axs[0].plot(time, intel_c5_4_data_1["reshup-max"], marker="1", ls='--', label='Instance 1', color='black')
axs[0].plot(time, intel_c5_4_data_2["reshup-max"], marker="|", ls='--', label='Instance 2', color='blue')
axs[0].plot(time, intel_c5_4_data_3["reshup-max"], marker="+", ls='--', label='Instance 3', color='green')
axs[0].plot(time, intel_c5_4_data_4["reshup-max"], marker="x", ls='--', label='Instance 4', color='orange')
axs[0].plot(time, intel_c5_4_data_5["reshup-max"], marker="4", ls='--', label='Instance 5', color='red')
axs[0].set_title("5 EC2 c5a.4x(Intel) instances ");
axs[1].plot(time, amd_c5a_4_data_1["reshup-max"], marker="1", ls='--', label='Instance 1', color='black')
axs[1].plot(time, amd_c5a_4_data_2["reshup-max"], marker="|", ls='--', label='Instance 2', color='blue')
axs[1].plot(time, amd_c5a_4_data_3["reshup-max"], marker="+", ls='--', label='Instance 3', color='green')
axs[1].plot(time, amd_c5a_4_data_4["reshup-max"], marker="x", ls='--', label='Instance 4', color='orange')
axs[1].plot(time, amd_c5a_4_data_5["reshup-max"], marker="4", ls='--', label='Instance 5', color='red')
axs[1].set_title("5 EC2 c5a.4x(AMD) instances ");

for ax in axs.flat:
    ax.set(xlabel= 'Time (6th April)(PDT)', ylabel='Max Delay')

for ax in axs.flat:
    ax.label_outer()

#for ax in axs.flat:
#    ax.legend(loc='upper left')

fig.savefig('4_7_2021_memcached_c5_max.pdf')

# avg
fig, axs = plt.subplots(2, sharex=True)
axs[0].plot(time, intel_c5_4_data_1["reshup-avg"], marker="1", ls='--', label='Instance 1', color='black')
axs[0].plot(time, intel_c5_4_data_2["reshup-avg"], marker="|", ls='--', label='Instance 2', color='blue')
axs[0].plot(time, intel_c5_4_data_3["reshup-avg"], marker="+", ls='--', label='Instance 3', color='green')
axs[0].plot(time, intel_c5_4_data_4["reshup-avg"], marker="x", ls='--', label='Instance 4', color='orange')
axs[0].plot(time, intel_c5_4_data_5["reshup-avg"], marker="4", ls='--', label='Instance 5', color='red')
axs[0].set_title("5 EC2 c5a.4x(Intel) instances ");
axs[1].plot(time, amd_c5a_4_data_1["reshup-avg"], marker="1", ls='--', label='Instance 1', color='black')
axs[1].plot(time, amd_c5a_4_data_2["reshup-avg"], marker="|", ls='--', label='Instance 2', color='blue')
axs[1].plot(time, amd_c5a_4_data_3["reshup-avg"], marker="+", ls='--', label='Instance 3', color='green')
axs[1].plot(time, amd_c5a_4_data_4["reshup-avg"], marker="x", ls='--', label='Instance 4', color='orange')
axs[1].plot(time, amd_c5a_4_data_5["reshup-avg"], marker="4", ls='--', label='Instance 5', color='red')
axs[1].set_title("5 EC2 c5a.4x(AMD) instances ");

for ax in axs.flat:
    ax.set(xlabel= 'Time (6th April)(PDT)', ylabel='Average Delay')

for ax in axs.flat:
    ax.label_outer()

#for ax in axs.flat:
#    ax.legend(loc='upper left')

fig.savefig('4_7_2021_memcached_c5_avg.pdf')

# throughput
fig, axs = plt.subplots(2, sharex=True)
axs[0].plot(time, intel_c5_4_data_1["hpthrput"], marker="1", ls='--', label='Instance 1', color='black')
axs[0].plot(time, intel_c5_4_data_2["hpthrput"], marker="|", ls='--', label='Instance 2', color='blue')
axs[0].plot(time, intel_c5_4_data_3["hpthrput"], marker="+", ls='--', label='Instance 3', color='green')
axs[0].plot(time, intel_c5_4_data_4["hpthrput"], marker="x", ls='--', label='Instance 4', color='orange')
axs[0].plot(time, intel_c5_4_data_5["hpthrput"], marker="4", ls='--', label='Instance 5', color='red')
axs[0].set_title("5 EC2 c5a.4x(Intel) instances ");
axs[1].plot(time, amd_c5a_4_data_1["hpthrput"], marker="1", ls='--', label='Instance 1', color='black')
axs[1].plot(time, amd_c5a_4_data_2["hpthrput"], marker="|", ls='--', label='Instance 2', color='blue')
axs[1].plot(time, amd_c5a_4_data_3["hpthrput"], marker="+", ls='--', label='Instance 3', color='green')
axs[1].plot(time, amd_c5a_4_data_4["hpthrput"], marker="x", ls='--', label='Instance 4', color='orange')
axs[1].plot(time, amd_c5a_4_data_5["hpthrput"], marker="4", ls='--', label='Instance 5', color='red')
axs[1].set_title("5 EC2 c5a.4x(AMD) instances ");

for ax in axs.flat:
    ax.set(xlabel= 'Time (6th April)(PDT)', ylabel='Throughput')

for ax in axs.flat:
    ax.label_outer()

#for ax in axs.flat:
#    ax.legend(loc='upper left')

fig.savefig('4_7_2021_memcached_c5_thruput.pdf')

# p20
fig, axs = plt.subplots(2, sharex=True)
axs[0].plot(time, intel_c5_4_data_1["p20"], marker="1", ls='--', label='Instance 1', color='black')
axs[0].plot(time, intel_c5_4_data_2["p20"], marker="|", ls='--', label='Instance 2', color='blue')
axs[0].plot(time, intel_c5_4_data_3["p20"], marker="+", ls='--', label='Instance 3', color='green')
axs[0].plot(time, intel_c5_4_data_4["p20"], marker="x", ls='--', label='Instance 4', color='orange')
axs[0].plot(time, intel_c5_4_data_5["p20"], marker="4", ls='--', label='Instance 5', color='red')
axs[0].set_title("5 EC2 c5a.4x(Intel) instances ");
axs[1].plot(time, amd_c5a_4_data_1["p20"], marker="1", ls='--', label='Instance 1', color='black')
axs[1].plot(time, amd_c5a_4_data_2["p20"], marker="|", ls='--', label='Instance 2', color='blue')
axs[1].plot(time, amd_c5a_4_data_3["p20"], marker="+", ls='--', label='Instance 3', color='green')
axs[1].plot(time, amd_c5a_4_data_4["p20"], marker="x", ls='--', label='Instance 4', color='orange')
axs[1].plot(time, amd_c5a_4_data_5["p20"], marker="4", ls='--', label='Instance 5', color='red')
axs[1].set_title("5 EC2 c5a.4x(AMD) instances ");

for ax in axs.flat:
    ax.set(xlabel= 'Time (6th April)(PDT)', ylabel='p20')

for ax in axs.flat:
    ax.label_outer()

#for ax in axs.flat:
#    ax.legend(loc='upper left')

fig.savefig('4_7_2021_memcached_c5_p20.pdf')


# p50
fig, axs = plt.subplots(2, sharex=True)
axs[0].plot(time, intel_c5_4_data_1["p50"], marker="1", ls='--', label='Instance 1', color='black')
axs[0].plot(time, intel_c5_4_data_2["p50"], marker="|", ls='--', label='Instance 2', color='blue')
axs[0].plot(time, intel_c5_4_data_3["p50"], marker="+", ls='--', label='Instance 3', color='green')
axs[0].plot(time, intel_c5_4_data_4["p50"], marker="x", ls='--', label='Instance 4', color='orange')
axs[0].plot(time, intel_c5_4_data_5["p50"], marker="4", ls='--', label='Instance 5', color='red')
axs[0].set_title("5 EC2 c5a.4x(Intel) instances ");
axs[1].plot(time, amd_c5a_4_data_1["p50"], marker="1", ls='--', label='Instance 1', color='black')
axs[1].plot(time, amd_c5a_4_data_2["p50"], marker="|", ls='--', label='Instance 2', color='blue')
axs[1].plot(time, amd_c5a_4_data_3["p50"], marker="+", ls='--', label='Instance 3', color='green')
axs[1].plot(time, amd_c5a_4_data_4["p50"], marker="x", ls='--', label='Instance 4', color='orange')
axs[1].plot(time, amd_c5a_4_data_5["p50"], marker="4", ls='--', label='Instance 5', color='red')
axs[1].set_title("5 EC2 c5a.4x(AMD) instances ");

for ax in axs.flat:
    ax.set(xlabel= 'Time (6th April)(PDT)', ylabel='p50')

for ax in axs.flat:
    ax.label_outer()

#for ax in axs.flat:
#    ax.legend(loc='upper left')

fig.savefig('4_7_2021_memcached_c5_p50.pdf')

# p75
fig, axs = plt.subplots(2, sharex=True)
axs[0].plot(time, intel_c5_4_data_1["p75"], marker="1", ls='--', label='Instance 1', color='black')
axs[0].plot(time, intel_c5_4_data_2["p75"], marker="|", ls='--', label='Instance 2', color='blue')
axs[0].plot(time, intel_c5_4_data_3["p75"], marker="+", ls='--', label='Instance 3', color='green')
axs[0].plot(time, intel_c5_4_data_4["p75"], marker="x", ls='--', label='Instance 4', color='orange')
axs[0].plot(time, intel_c5_4_data_5["p75"], marker="4", ls='--', label='Instance 5', color='red')
axs[0].set_title("5 EC2 c5a.4x(Intel) instances ");
axs[1].plot(time, amd_c5a_4_data_1["p75"], marker="1", ls='--', label='Instance 1', color='black')
axs[1].plot(time, amd_c5a_4_data_2["p75"], marker="|", ls='--', label='Instance 2', color='blue')
axs[1].plot(time, amd_c5a_4_data_3["p75"], marker="+", ls='--', label='Instance 3', color='green')
axs[1].plot(time, amd_c5a_4_data_4["p75"], marker="x", ls='--', label='Instance 4', color='orange')
axs[1].plot(time, amd_c5a_4_data_5["p75"], marker="4", ls='--', label='Instance 5', color='red')
axs[1].set_title("5 EC2 c5a.4x(AMD) instances ");

for ax in axs.flat:
    ax.set(xlabel= 'Time (6th April)(PDT)', ylabel='p75')

for ax in axs.flat:
    ax.label_outer()

#for ax in axs.flat:
#    ax.legend(loc='upper left')

fig.savefig('4_7_2021_memcached_c5_p75.pdf')

# p90
fig, axs = plt.subplots(2, sharex=True)
axs[0].plot(time, intel_c5_4_data_1["p90"], marker="1", ls='--', label='Instance 1', color='black')
axs[0].plot(time, intel_c5_4_data_2["p90"], marker="|", ls='--', label='Instance 2', color='blue')
axs[0].plot(time, intel_c5_4_data_3["p90"], marker="+", ls='--', label='Instance 3', color='green')
axs[0].plot(time, intel_c5_4_data_4["p90"], marker="x", ls='--', label='Instance 4', color='orange')
axs[0].plot(time, intel_c5_4_data_5["p90"], marker="4", ls='--', label='Instance 5', color='red')
axs[0].set_title("5 EC2 c5a.4x(Intel) instances ");
axs[1].plot(time, amd_c5a_4_data_1["p90"], marker="1", ls='--', label='Instance 1', color='black')
axs[1].plot(time, amd_c5a_4_data_2["p90"], marker="|", ls='--', label='Instance 2', color='blue')
axs[1].plot(time, amd_c5a_4_data_3["p90"], marker="+", ls='--', label='Instance 3', color='green')
axs[1].plot(time, amd_c5a_4_data_4["p90"], marker="x", ls='--', label='Instance 4', color='orange')
axs[1].plot(time, amd_c5a_4_data_5["p90"], marker="4", ls='--', label='Instance 5', color='red')
axs[1].set_title("5 EC2 c5a.4x(AMD) instances ");

for ax in axs.flat:
    ax.set(xlabel= 'Time (6th April)(PDT)', ylabel='p90')

for ax in axs.flat:
    ax.label_outer()

#for ax in axs.flat:
#    ax.legend(loc='upper left')

fig.savefig('4_7_2021_memcached_c5_p90.pdf')


