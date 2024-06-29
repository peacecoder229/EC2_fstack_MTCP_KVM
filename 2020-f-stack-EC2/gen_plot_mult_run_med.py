import matplotlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.pyplot import figure
from statistics import mean

dir_prefix = "/pnpdata/2020-f-stack-muktadir/ec2_exp_nginx_drc_res"
intel_c5_12_data = pd.read_csv("{}/intel/c5.12xlarge/intel_c5_12.csv".format(dir_prefix));
intel_c5_4_data = pd.read_csv("{}/intel/c5.4xlarge/intel_c5_4.csv".format(dir_prefix));

amd_c5a_4_data = pd.read_csv("{}/amd/c5a.4xlarge/amd_c5a_4.csv".format(dir_prefix));
amd_c5a_12_data = pd.read_csv("{}/amd/c5a.12xlarge/amd_c5a_12.csv".format(dir_prefix));

time = ['TueMay2515', 'TueMay2516', 'TueMay2517', 'TueMay2518', 'TueMay2519', 'TueMay2520', 'TueMay2521', 'TueMay2522', 'TueMay2523', 'WedMay2600']
hours = ['15', '16', '17', '18', '19', '20', '21', '22', '23', '00' ]
date = 'TueMay25'
percentiles = ['p10', 'p20', 'p30', 'p40', 'p50', 'p60', 'p75', 'p90']

'''
    Returns list of means according to 'time' and 'date'
'''
def getMeanList(data, col_name):
    p_all = []
    for tp in time:
        #print(amd_c5a_12_data[amd_c5a_12_data.Time.str.match('{}:*'.format(tp))])
        p_all.append(data[data.Time.str.match('{}:*'.format(tp))][col_name])
    
    p_mean = []
    for p in p_all:
        #print(p)
        p_mean.append(mean(p))

    return p_mean

def create_plot(x_label, y_label, intel_c5_4, intel_c5_12, amd_c5a_4, amd_c5a_12, x_axis, file_name):
    fig=plt.figure()
    ax=fig.add_subplot(111)
    
    ax.plot(x_axis, intel_c5_12, marker="v", ls='--', label='intel(c5_12)', color='black')
    ax.plot(x_axis, intel_c5_4, marker="x", ls='--', label='intel(c5_4)', color='black')
    ax.plot(x_axis, amd_c5a_12, marker="v", ls='-', label='amd(c5a_12)', color='blue')
    ax.plot(x_axis, amd_c5a_4, marker="x", ls='-', label='amd(c5a_4)', color='blue')

    #ax.set_ylim(ymin=0)
    ax.grid()
    plt.xlabel(x_label, fontsize=10)
    plt.ylabel(y_label, fontsize=10)
    plt.legend(loc='upper left')
    fig.savefig(file_name)

'''
    Plot all percentiles
'''
intel_c5_4_all_percentiles = []
intel_c5_12_all_percentiles = []
amd_c5a_4_all_percentiles = []
amd_c5a_12_all_percentiles = []

for p in percentiles:
    intel_c5_4_all_percentiles.append(mean(getMeanList(intel_c5_4_data, p)))
    intel_c5_12_all_percentiles.append(mean(getMeanList(intel_c5_12_data, p)))
    amd_c5a_4_all_percentiles.append(mean(getMeanList(amd_c5a_4_data, p)))
    amd_c5a_12_all_percentiles.append(mean(getMeanList(amd_c5a_12_data, p)))

create_plot('Delay(ms)', 'Mean of Percentiles', intel_c5_4_all_percentiles, intel_c5_12_all_percentiles, amd_c5a_4_all_percentiles, amd_c5a_12_all_percentiles, percentiles, '5_25_2021_all_perc_mean.pdf')

'''
amd_c5a_4_p_10_mean = getMeanList(amd_c5a_4_data, 'p10') 
print(amd_c5a_4_p_10_mean)
amd_c5a_12_p_10_mean = getMeanList(amd_c5a_12_data, 'p10')
print(amd_c5a_12_p_10_mean)
intel_c5_12_p_10_mean = getMeanList(intel_c5_12_data, 'p10')
print(intel_c5_12_p_10_mean)
intel_c5_4_p_10_mean = getMeanList(intel_c5_4_data, 'p10')
print(intel_c5_4_p_10_mean)
'''

'''
Plot mean throughput
'''
amd_c5a_4_thrput_mean = getMeanList(amd_c5a_4_data, 'hpthrput') 
amd_c5a_12_thrput_mean = getMeanList(amd_c5a_12_data, 'hpthrput')
intel_c5_12_thrput_mean = getMeanList(intel_c5_12_data, 'hpthrput')
intel_c5_4_thrput_mean = getMeanList(intel_c5_4_data, 'hpthrput')

create_plot('Mean Throughput(Request/Sec)', 'Timeline', intel_c5_4_thrput_mean, intel_c5_12_thrput_mean, amd_c5a_4_thrput_mean, amd_c5a_12_thrput_mean, hours, '5_25_2021_thrput_mean.pdf')
