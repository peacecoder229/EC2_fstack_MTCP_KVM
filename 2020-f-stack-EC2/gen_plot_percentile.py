import matplotlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.pyplot import figure
from labellines import *

intel_c5_4_data = pd.read_csv("/pnpdata/2020-f-stack-muktadir/ec2_exp_mc_mb_redis_drc_res/intel/c5.4xlarge/intel_c5_4.csv");

amd_c5a_4_data = pd.read_csv("/pnpdata/2020-f-stack-muktadir/ec2_exp_mc_mb_redis_drc_res/amd/c5a.4xlarge/amd_c5a_4.csv");

time = ["22", "22.5", "23", "23.5", "0", "0.5", "1", "1.5", "2", "2.5", "3", "3.5", "4", "4.5", "5", "5.5", "6", "6.5", "7", "7.5"]

fig, axs = plt.subplots(2, sharex=True)
axs[0].plot(time, intel_c5_4_data["p10"], marker="x", ls='--', label='p10', color='blue')
axs[0].plot(time, intel_c5_4_data["p20"], marker="x", ls='--', label='p20', color='orange')
axs[0].plot(time, intel_c5_4_data["p30"], marker="x", ls='--', label='p30', color='green')
axs[0].plot(time, intel_c5_4_data["p40"], marker="x", ls='--', label='p40', color='red')
axs[0].plot(time, intel_c5_4_data["p50"], marker="x", ls='--', label='p50', color='purple')
axs[0].plot(time, intel_c5_4_data["p60"], marker="x", ls='--', label='p60', color='brown')
axs[0].plot(time, intel_c5_4_data["p75"], marker="x", ls='--', label='p70', color='pink')
axs[0].plot(time, intel_c5_4_data["p90"], marker="x", ls='--', label='p90', color='olive')
axs[0].set_title("EC2 c5a.4x(Intel) instance ");
#labelLines(axs[0].get_lines(),zorder=2.5)

axs[1].plot(time, amd_c5a_4_data["p10"], marker="x", ls='--', label='p10', color='blue')
axs[1].plot(time, amd_c5a_4_data["p20"], marker="x", ls='--', label='p20', color='orange')
axs[1].plot(time, amd_c5a_4_data["p30"], marker="x", ls='--', label='p30', color='green')
axs[1].plot(time, amd_c5a_4_data["p40"], marker="x", ls='--', label='p40', color='red')
axs[1].plot(time, amd_c5a_4_data["p50"], marker="x", ls='--', label='p50', color='purple')
axs[1].plot(time, amd_c5a_4_data["p60"], marker="x", ls='--', label='p60', color='brown')
axs[1].plot(time, amd_c5a_4_data["p75"], marker="x", ls='--', label='p70', color='pink')
axs[1].plot(time, amd_c5a_4_data["p90"], marker="x", ls='--', label='p90', color='olive')
axs[1].set_title("EC2 c5a.4x(AMD) instance ");
#labelLines(axs[1].get_lines(),zorder=2.5)

for ax in axs.flat:
    ax.set(xlabel= 'Time (6th April)(PDT)', ylabel='Percentile Delays')

for ax in axs.flat:
    ax.label_outer()

axLine, axLabel = axs[0].get_legend_handles_labels()

fig.legend(axLine, axLabel, loc = 'upper right')

fig.savefig('4_7_2021_memcached_delay_percentile.pdf')
