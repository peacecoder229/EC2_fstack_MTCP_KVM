#!/usr/local/bin/python3.5
import os
import csv
import sys
import optparse
import subprocess
import time
#from pexpect import pxssh

def get_opts():
    """
    read user params
    :return: option object
    """
    parser = optparse.OptionParser()
    parser.add_option("--keypattern", dest="keys_pat",
                      help="read and write key pattern", default="S:S")
    parser.add_option("--keymin", dest="key_min",
                      help="minimum key number", default="1")
    parser.add_option("--ratio", dest="ratio",
                      help="write and read ratio", default="1")
    parser.add_option("--keymax", dest="key_max",
                      help="maximum key number", default="100000000")

    parser.add_option("--host", dest="host_ip",
                      help="host ip that redie server run", default="127.0.0.1")
    parser.add_option("-n", "--request_num", dest="num",
                      help="redis-benchmark request number", default="100000")

    parser.add_option("-l", "--loop_num", dest="loop",
                      help="redis-benchmark request number", default="8")

    parser.add_option("--mark",  dest="mark_name",
                      help="save report name", default="memtier")

    (options, args) = parser.parse_args()

    return options

def run_redis_server(options):
    """
    start redis server on the host
    """
    core = 1 
    if(options.ratio=="1:4" or options.ratio=="1:0"):
        if(options.host_ip == "127.0.0.1"):
            os.system("pkill redis")
        else:
            send_cmd_to_remote(options.host_ip, "pkill redis")
    time.sleep(3)
    for port in range(9001, 9001+int(options.loop)):
        cmd = "taskset -c %s redis-server --bind %s --port %s --save "" &"  % (core,options.host_ip,port)
        if(options.host_ip != "127.0.0.1"):
            send_cmd_to_remote(options.host_ip, cmd)
            time.sleep(1)
        else:
            os.system(cmd)
            time.sleep(1)
        core += 1

def send_cmd_to_remote(ip, cmd):
    #s = pxssh.pxssh(timeout=100)
    #s.login(remote_ip, 'root', '123456')
    #s.sendline(cmd)   # run a command
    #s.prompt()             # match the prompt
    #print(s.before)        # print everything before the prompt.
    #s.logout()
    os.system("ssh %s  %s " % (ip, cmd))

def run_memtier(options):
    #emon_name = options.mark_name+ options.ratio
    #print(emon_name)
    #os.system("/root/emon/run_emon.sh %s &" % emon_name )
    core = 22
    os.system("rm -rf output*.txt")
    benchmark_process = []
    for port in range(9001, 9001+int(options.loop)):
        core += 1
        cmd = "taskset -c %s memtier_benchmark -p %s -s %s -d 1024 -c 20 --ratio=%s --key-pattern G:G --pipeline=16 --key-maximum 100000 -n 500000 --thread=1" % (core, port, options.host_ip,  options.ratio)
        with open("output"+str(port)+".txt", "w") as outfile:
            benchmark_process.append(subprocess.Popen(cmd, stdout=outfile, shell=True))

    return benchmark_process

def csv_write_row(filename, header, row):
    with open(filename, 'a') as csvfile:
        csvWriter = csv.DictWriter(csvfile, fieldnames=header)
        csvWriter.writerow(row)

def csv_write_header(filename, header):
    with open(filename, 'a') as csvfile:
        fieldnames = header
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()


def generate_report(process_group, options):
    """
    generate result csv
    """
    header = ["instances","set_qps", "set_lat", "sbw","get_qps", "get_lat", "gbw", "IP", "port"]
    summary_report_name = "memtier_" + options.mark_name + options.ratio + ".csv"
    csv_write_header(summary_report_name, header)
    index = 0
    data =[]
    while len(process_group) > 0 :
        for process in process_group:
            if (process.poll()!=None):
                cmd = format(process.args).split(" ")
                print("*******************"+format(process.args))
                port_num = cmd[5]
                server = cmd[7]
                print(port_num)
                with open("output"+port_num+".txt") as logfile:
                    data_per_instance = {}
                    for line in logfile:
                        if line.find("Sets ") > -1 :
                            operation = line.split()[1]
                            lat = line.split()[4]
                            bw = line.split()[5]
                            data_per_instance['set_qps'] = operation
                            data_per_instance['set_lat'] = lat
                            data_per_instance['sbw'] = bw
                        if line.find("Gets ") > -1 :
                            operation = line.split()[1]
                            lat = line.split()[4]
                            bw = line.split()[5]
                            data_per_instance['get_qps'] = operation
                            data_per_instance['get_lat'] = lat
                            data_per_instance['gbw'] = bw

                    index = index + 1
                    data_per_instance["instances"] = index
                    data_per_instance["IP"] = server
                    data_per_instance["port"] = port_num

                    data.append(data_per_instance)
                    csv_write_row(summary_report_name,header,  data_per_instance)
                    print(data_per_instance)

                    process_group.remove(process)
            else:
                time.sleep(1)
                #pass

    #os.system("/root/emon/stop_emon.sh")
    data_total = {}
    data_total["get_qps"] = sum(float(i["get_qps"]) for i in data)
    data_total["set_qps"] = sum(float(i["set_qps"]) for i in data)
    data_total["set_lat"] = sum([float(i["set_lat"]) for i in data])/float(len(data))
    data_total["get_lat"] = sum([float(i["get_lat"]) for i in data])/float(len(data))
    data_total["instances"] = summary_report_name + options.mark_name
    header = ["instances",  "set_qps", "set_lat", "get_qps", "get_lat"]
    csv_write_row(summary_report_name, header, data_total)
    csv_write_row("memtier_total.csv", header, data_total)


if __name__ == "__main__": 
    options = get_opts()
    if(options.ratio!="0:1"):
        run_redis_server(options)
    process = run_memtier(options)
    generate_report(process, options)



