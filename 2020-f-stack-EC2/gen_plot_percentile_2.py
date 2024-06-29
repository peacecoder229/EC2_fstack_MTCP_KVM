import matplotlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.pyplot import figure
from labellines import *

dir_prefix = "/pnpdata/2020-f-stack-muktadir/ec2_exp_mc_mb_redis_drc_res"
intel_c5_12_data = pd.read_csv("{}/intel/c5.12xlarge/intel_c5_12.csv".format(dir_prefix));
intel_c5_4_data = pd.read_csv("{}/intel/c5.4xlarge/intel_c5_4.csv".format(dir_prefix));

amd_c5a_4_data = pd.read_csv("{}/amd/c5a.4xlarge/amd_c5a_4.csv".format(dir_prefix));
amd_c5a_12_data = pd.read_csv("{}/amd/c5a.12xlarge/amd_c5a_12.csv".format(dir_prefix));

intel_c5_12_percentile = []
intel_c5_4_percentile = []
amd_c5_12_percentile = []
amd_c5_4_percentile = []

percentiles = ['p10', 'p20', 'p30', 'p40', 'p50', 'p60', 'p75', 'p90']

for p in percentiles:
    intel_c5_4_percentile.append(intel_c5_4_data[p].median());
    intel_c5_12_percentile.append(intel_c5_12_data[p].median());
    amd_c5_4_percentile.append(amd_c5a_4_data[p].median());
    amd_c5_12_percentile.append(amd_c5a_12_data[p].median());

fig = plt.figure()
ax = fig.add_subplot(111)

ax.plot(percentiles, intel_c5_12_percentile, marker="v", ls='--', label='intel(c5_12)', color='black')
ax.plot(percentiles, intel_c5_4_percentile, marker="x", ls='--', label='intel(c5_4)', color='black')
ax.plot(percentiles, amd_c5_12_percentile, marker="v", ls='-', label='amd(c5a_12)', color='blue')
ax.plot(percentiles, amd_c5_4_percentile, marker="x", ls='-', label='amd(c5a_4)', color='blue')
ax.grid()
plt.xlabel('Median of Percentiles', fontsize=12)
plt.ylabel('Delay(ms)', fontsize=12)
plt.legend(loc='upper left')
fig.savefig('4_29_2021_all_percentile_median.pdf')
