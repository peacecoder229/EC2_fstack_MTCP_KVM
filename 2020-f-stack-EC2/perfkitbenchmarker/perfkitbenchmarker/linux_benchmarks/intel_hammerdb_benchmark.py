import functools
import logging
import math
import posixpath
import time
import os
import re

from perfkitbenchmarker import configs
from perfkitbenchmarker import data
from perfkitbenchmarker import errors
from absl import flags
from perfkitbenchmarker import regex_util
from perfkitbenchmarker import sample
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import flag_util
from perfkitbenchmarker.linux_packages import INSTALL_DIR
from perfkitbenchmarker.linux_packages import intel_hammerdb

FLAGS = flags.FLAGS

# These are not directly tied to HammerDB or Postgres and are for dynamic tuning
flags.DEFINE_float('intel_hammerdb_tpcc_postgres_shared_buffers_ratio', 0.75, 'Amount of '
                   'memory to be used for shared buffers for postgres')
flags.DEFINE_float('intel_hammerdb_tpcc_postgres_memlock_ratio', 0.80, 'Amount of memory to lock for pkb user')
flags.DEFINE_integer('intel_hammerdb_tpcc_postgres_num_hugepages', 100, 'Number of huge pages for postgres')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_num_hugepages', 100, 'Number of huge pages for mysql')
flags.DEFINE_float('intel_hammerdb_tpcc_mysql_innodb_buffers_ratio', 0.75, 'Amount of memory to be used for mysql')

flags.DEFINE_boolean('intel_hammerdb_run_single_node', True, 'Run Server & Client on same'
                     'machine or different machines')
flags.DEFINE_string('intel_hammerdb_platform', 'None', 'Mention if its an ARM platform or None for others')

# Flags for MySQL configuration
flags.DEFINE_string('intel_hammerdb_tpcc_mysql_hugepages', 'off', 'hugepage settings can be on or off')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_num_warehouse', 256, 'num of warehouses')
flags.DEFINE_string('intel_hammerdb_tpcc_mysql_innodb_buffer_pool_size', '6400M', 'buffer pool size')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_buffer_pool_instances', 16,
                     'Instances of buffer pool')
flags.DEFINE_string('intel_hammerdb_tpcc_mysql_innodb_log_buffer_size', '64M', 'size of log buffer')

flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_doublewrite', 0, 'Stores data twice to the'
                     ' buffer and to actual data files')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_thread_concurrency', 0, 'Limit for OS threads'
                     ' running concurrently inside InnoDB')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_flush_log_at_trx_commit', 0, 'Determines how '
                     'logs are written and flush to disk')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_max_dirty_pages_pct', 90, 'Limit for % of dirty'
                     ' pages which is maintained by Innodb by flushing data from the buffer pool')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_max_dirty_pages_pct_lwm', 10, 'Defines a low '
                     'water mark representing the percentage of dirty pages at which preflushing'
                     'is enabled to control the dirty page ratio')
flags.DEFINE_string('intel_hammerdb_tpcc_mysql_join_buffer_size', '32K', 'The minimum size of the '
                    ' buffer that is used for plain index scans, range index scans, and joins'
                    '  that do not use indexes and thus perform full table scans.')
flags.DEFINE_string('intel_hammerdb_tpcc_mysql_sort_buffer_size', '32K', 'Each session that must '
                    ' perform a sort allocates a buffer of this size')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_use_native_aio', 1, 'Indicates if Linux '
                     'asynchronous I/O subsytem should be used. On by default')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_stats_persistent', 1, 'Specifies if InnoDB'
                     ' index statistics are persisted to disk')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_spin_wait_delay', 6, 'The maximum delay'
                     ' between polls for a spin lock. Min Val 0, Max Val (2^32)-1')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_max_purge_lag_delay', 300000, 'Specifies the '
                     ' maximum delay in microseconds for the delay imposed when the '
                     ' innodb_max_purge_lag threshold is exceeded')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_max_purge_lag', 0, 'If this value is exceeded,'
                     ' a delay is imposed on INSERT, UPDATE, and DELETE operations to allow time'
                     ' for purge to catch up')
flags.DEFINE_string('intel_hammerdb_tpcc_mysql_innodb_flush_method', 'O_DIRECT_NO_FSYNC', 'Defines'
                    ' the method used to flush data to InnoDB data files and log files, which'
                    ' can affect I/O throughput.')
flags.DEFINE_string('intel_hammerdb_tpcc_mysql_innodb_checksum_algorithm', 'none', 'Specifies how '
                    ' to generate and verify the checksum stored in the disk blocks of InnoDB'
                    ' tablespaces.')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_io_capacity', 4000, 'number of I/O operations'
                     ' per second (IOPS) available to InnoDB background tasks. Min Val 100, '
                     ' Max Val (2^64)-1')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_io_capacity_max', 20000, 'A maximum number '
                     ' of IOPS performed by InnoDB background task')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_lru_scan_depth', 9000, ' It specifies, per '
                     ' buffer pool instance, how far down the buffer pool LRU page list the page '
                     ' cleaner thread scans looking for dirty pages to flush.')
flags.DEFINE_string('intel_hammerdb_tpcc_mysql_innodb_change_buffering', 'none', 'Whether InnoDB '
                    ' performs change buffering, an optimization that delays write operations '
                    ' to secondary indexes so that the I/O operations can be performed'
                    ' sequentially')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_read_only', 0, 'Starts Innodb in read-only '
                     ' mode')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_page_cleaners', 4, 'The number of page cleaner'
                     ' threads that flush dirty pages from buffer pool instances. Min Val 1, '
                     ' Max Val 64')
flags.DEFINE_string('intel_hammerdb_tpcc_mysql_innodb_undo_log_truncate', 'off', 'When enabled,'
                    ' undo tablespaces that exceed the threshold value defined by '
                    ' innodb_max_undo_log_size are marked for truncation.')
# Flags for MySQL Innodb perf special
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_adaptive_flushing', 1, 'Specifies whether to'
                     ' dynamically adjust the rate of flushing dirty pages in the buffer pool '
                     ' to avoid bursts of I/O activity.')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_flush_neighbors', 0, ' Specifies whether '
                     ' flushing a page from the InnoDB buffer pool also flushes other dirty '
                     ' pages in the same extent')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_read_io_threads', 16, 'The number of I/O '
                     ' threads for read operations in InnoDB. Min Val 1, Max Val 64')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_write_io_threads', 16, 'The number of I/O '
                     ' threads for write operations in InnoDB. Min Val 1, Max Val 64')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_purge_threads', 4, 'The number of background '
                     ' threads devoted to the InnoDB purge operation. Min Val 1, Max Val 32')
flags.DEFINE_integer('intel_hammerdb_tpcc_mysql_innodb_adaptive_hash_index', 0, 'Enable/Disable '
                     ' adaptive hash indexing to improve query performance')


# Flags for Postgres configuration
flags.DEFINE_integer('intel_hammerdb_tpcc_postgres_num_warehouse', 256, 'num of warehouses')
flags.DEFINE_string('intel_hammerdb_tpcc_postgres_allwarehouse', 'false', 'use all warehouses or not')
flags.DEFINE_integer('intel_hammerdb_tpcc_postgres_max_connections', 256, 'number of max connections')
flags.DEFINE_string('intel_hammerdb_tpcc_postgres_hugepages', 'off', 'hugepage settings can be on, off, or try')
flags.DEFINE_string('intel_hammerdb_tpcc_postgres_shared_buffers', '6400MB', 'Default size for memory')
flags.DEFINE_string('intel_hammerdb_tpcc_postgres_temp_buffers', '4096MB', 'Sets the maximum number of'
                    'temporary buffers used by each database session,min 800kB')
flags.DEFINE_string('intel_hammerdb_tpcc_postgres_work_mem', '4096MB', 'Memory to be used by internal'
                    'sort operations and hash tables before writing to temporary disk files,'
                    'min 64kB')
flags.DEFINE_string('intel_hammerdb_tpcc_postgres_maintenance_work_mem', '512MB', 'Maximum amount of '
                    'memory to be used by maintenance operations,min 1MB')
flags.DEFINE_string('intel_hammerdb_tpcc_postgres_autovacuum_work_mem', '-1',
                    'min 1MB, or -1 to use maintenance_work_mem')
flags.DEFINE_string('intel_hammerdb_tpcc_postgres_max_stack_depth', '7MB', 'maximum safe depth of the'
                    'server execution stack, min 100kB')
flags.DEFINE_string('intel_hammerdb_tpcc_postgres_dynamic_shared_memory_type', 'posix',
                    'posix,sysv,windows,mmap or none to disable it')
flags.DEFINE_integer('intel_hammerdb_tpcc_postgres_max_files_per_process', 4000, 'maximum number of '
                     'simultaneously open files allowed to each server subprocess min 25')
flags.DEFINE_integer('intel_hammerdb_tpcc_postgres_io_concur', 32, '1-1000; 0 disables prefetching')
flags.DEFINE_integer('intel_hammerdb_tpcc_postgres_max_worker_process', 72, 'max # of worker processes')
flags.DEFINE_string('intel_hammerdb_tpcc_postgres_wal_level', 'minimal', 'can be minimal, replica, or logical')
flags.DEFINE_string('intel_hammerdb_tpcc_postgres_syn_commit', 'off',
                    'synchronization level, can be  off, local, remote_write, remote_apply, or on')
flags.DEFINE_string('intel_hammerdb_tpcc_postgres_wal_buffers', '-1', 'mount of shared memory used'
                    'for WAL data that has not yet been written to disk,'
                    'min 32kB, -1 sets based on shared_buffers')
flags.DEFINE_integer('intel_hammerdb_tpcc_postgres_max_wal_senders', 0, 'maximum number of concurrent'
                     'connections from standby servers')
flags.DEFINE_string('intel_hammerdb_tpcc_postgres_log_timezone', 'UTC', 'timezone for the logs')
flags.DEFINE_string('intel_hammerdb_tpcc_postgres_timezone', 'UTC', 'timezone')
flags.DEFINE_integer('intel_hammerdb_tpcc_postgres_max_locks_per_transaction', 64, 'Controls the number'
                     'of shared locks allocated for each transaction, min 10')
flags.DEFINE_integer('intel_hammerdb_tpcc_postgres_max_pred_locks_per_transaction', 64, 'Controls the '
                     'number of shared predicate locks allocated for each transaction, min 10')
flags.DEFINE_integer('intel_hammerdb_tpcc_postgres_min_wal_size', 262144, 'If WAL disk usage stays '
                     'below this setting, old WAL files are always recycled for future use at '
                     'a checkpoint')
flags.DEFINE_integer('intel_hammerdb_tpcc_postgres_max_wal_size', 524288, 'Maximum size to let the WAL'
                     'grow to between automatic WAL checkpoints')
flags.DEFINE_float('intel_hammerdb_tpcc_postgres_checkpoint_completion_target', 0.9, 'Specifies '
                   'the target of checkpoint completion as a fraction of total time between'
                   'checkpoints')
flags.DEFINE_integer('intel_hammerdb_tpcc_postgres_checkpoint_warning', 1, 'Enables warnings if'
                     'checkpoint segments are filled more frequently than this')
flags.DEFINE_float('intel_hammerdb_tpcc_postgres_random_page_cost', 1.1, 'Sets the planner\'s '
                   'estimate of the cost of a nonsequentially fetched disk page')
flags.DEFINE_float('intel_hammerdb_tpcc_postgres_cpu_tuple_cost', 0.03, 'Sets the planner\'s '
                   'estimate of the cost of processing each row during a query.')
flags.DEFINE_string('intel_hammerdb_tpcc_postgres_effective_cache_size', '350GB', 'Sets the '
                    'planner\'s assumption about the total size of the data caches')
flags.DEFINE_string('intel_hammerdb_tpcc_postgres_autovacuum', 'on', 'Starts the autovacuum'
                    'subprocess')
flags.DEFINE_integer('intel_hammerdb_tpcc_postgres_autovacuum_max_workers', 10, 'Sets the maximum'
                     'number of simultaneously running autovacuum worker processes')
flags.DEFINE_integer('intel_hammerdb_tpcc_postgres_autovacuum_freeze_max_age', 1000000000, 'Age at'
                     'which to autovacuum a table to prevent transaction ID wraparound')
flags.DEFINE_integer('intel_hammerdb_tpcc_postgres_autovacuum_vacuum_cost_limit', 3000, 'Vacuum '
                     'cost amount available before napping, for autovacuum')
flags.DEFINE_integer('intel_hammerdb_tpcc_postgres_vacuum_freeze_min_age', 10000000, 'Minimum '
                     'age at which VACUUM should freeze a table row')


# Flags for HammerDB configuration
flags.DEFINE_integer('intel_hammerdb_port', 5432, 'port at which the db is up and listening')
flags.DEFINE_integer('intel_hammerdb_enable_timestamps', 1, 'Write timestamps to log file')
flags.DEFINE_string('intel_hammerdb_tpcc_hammer_num_virtual_users', '16', 'num of virtual users for '
                    'running hammerdb')
flags.DEFINE_integer('intel_hammerdb_tpcc_threads_build_schema', 16, 'num of threads used for '
                     'building dataset')
flags.DEFINE_string('intel_hammerdb_db_type', 'pg', 'db type is pg or mysql')
flags.DEFINE_string('intel_hammerdb_benchmark_type', 'TPC-C', 'benchmark type')
flags.DEFINE_integer('intel_hammerdb_tpcc_rampup', 2, 'ramp up time of the workload')
flags.DEFINE_integer('intel_hammerdb_tpcc_runtime', 5, 'run time of the workload')
flags.DEFINE_boolean('intel_hammerdb_enable_timeprofile', False, 'time profile logs')


BENCHMARK_NAME = 'intel_hammerdb'
BENCHMARK_CONFIG = """
server_worker: &server_worker
    AWS:
        machine_type: c5.24xlarge
        zone: us-east-1
    GCP:
       machine_type: n1-standard-96
       zone: us-central1-a
       image: null
    Azure:
       machine_type: Standard_F72s_v2
       zone: eastus2
       image: null
    Tencent:
       machine_type: S5.LARGE16
       zone: ap-nanjing-1
       image: null

server_disk: &server_disk
    AWS:
        disk_type: standard
        disk_size: 500
        mount_point: /scratch
    GCP:
        disk_type: standard
        disk_size: 500
        mount_point: /scratch
    Azure:
        disk_type: Premium_LRS
        disk_size: 500
        mount_point: /scratch
    Tencent:
        disk_type: CLOUD_SSD
        disk_size: 500
        mount_point: /scratch

client_machine: &client_machine
    AWS:
        machine_type: c5.24xlarge
        zone: us-east-1
        image: null
    GCP:
        machine_type: n1-standard-96
        zone: us-central1-a
        image: null
    Azure:
        machine_type: Standard_F72s_v2
        zone: eastus2
        image: null
    Tencent:
        machine_type: S5.LARGE16
        zone: ap-nanjing-2
        image: null

intel_hammerdb:
  description: Benchmark hammerdb
  vm_groups:
    workers:
      os_type: ubuntu2004
      vm_spec: *server_worker
      disk_spec: *server_disk
    client:
      os_type: ubuntu2004
      vm_spec: *client_machine
"""
BENCHMARK_DATA = {}

DB = 'workers'
HAMMER = 'client'
RESULTS_METRICS = ('PostgreSQL TPM', 'NOPM')

HAMMERDB_HOME = "~/HammerDB_pkb"
HUGEPAGES_TMP_FILE = "~/hugepages.tmp"

FIREWALL_CHECK_FILE = "~/firewall_check"
POSTGRES_INSTALL_DIR = "~/Postgres_pkb"


def GetConfig(user_config):
  config = configs.LoadConfig(BENCHMARK_CONFIG, user_config, BENCHMARK_NAME)
  if FLAGS.intel_hammerdb_run_single_node:
    config["vm_groups"]["workers"]["vm_count"] = 1
    config["vm_groups"]["client"]["vm_count"] = 0
  else:
    config["vm_groups"]["workers"]["vm_count"] = 1
    config["vm_groups"]["client"]["vm_count"] = 1

  return config


def _GetDBThreadsForBuildSchema(vm):
  if "intel_hammerdb_tpcc_threads_build_schema" in flag_util.GetProvidedCommandLineFlags():
    db_threads = FLAGS.intel_hammerdb_tpcc_threads_build_schema
  else:
    db_threads = vm.num_cpus
  return db_threads


def _GetHammerNumUsers(vm):
  if "intel_hammerdb_tpcc_hammer_num_virtual_users" in flag_util.GetProvidedCommandLineFlags():
    hammer_users = FLAGS.intel_hammerdb_tpcc_hammer_num_virtual_users
  else:
    hammer_users = _GetDefaultRangeForHammerUsers(vm)
  return hammer_users


def _GetNumWarehouses(vm):
  if (FLAGS.intel_hammerdb_db_type == 'pg' and "intel_hammerdb_tpcc_postgres_num_warehouse" in
      flag_util.GetProvidedCommandLineFlags()):
    num_warehouses = FLAGS.intel_hammerdb_tpcc_postgres_num_warehouse
  elif (FLAGS.intel_hammerdb_db_type == 'mysql' and "intel_hammerdb_tpcc_mysql_num_warehouse" in
        flag_util.GetProvidedCommandLineFlags()):
    num_warehouses = FLAGS.intel_hammerdb_tpcc_mysql_num_warehouse
  else:
    num_logical_cores = vm.num_cpus
    num_warehouses = 800
    if num_logical_cores <= 32:
      num_warehouses = 400
  return num_warehouses


def _GetDefaultRangeForHammerUsers(vm):
  # If user does not mention the num of virutal users, we will then calculate a range like :
  # If num of cores = 96 we try a list with cores-5, cores-10 , cores+5 ,cores+10
  # [ 66 76 86 91 96 101 106 116 126 144 ]
  num_logical_cores = vm.num_cpus
  maxRange = int(1.5 * num_logical_cores)
  minRange = 1
  hammer_users_list = []
  hammer_users = ""
  hammer_users_list.append(vm.num_cpus)
  loop = 0
  step = -6
  step_adjust = 1

  while loop < 2:
    index = 0
    while index < 4:
      if index == 2:
        step = (step + step_adjust) * 2
      num_logical_cores += step
      if num_logical_cores >= minRange and num_logical_cores <= maxRange:
        hammer_users_list.append(num_logical_cores)
      index += 1
    loop += 1
    step = 6
    step_adjust = -1
    num_logical_cores = vm.num_cpus

  if maxRange not in hammer_users_list:
    hammer_users_list.append(maxRange)

  hammer_users_list.sort()
  for num in hammer_users_list:
    hammer_users += str(num)
    hammer_users += ' '

  return hammer_users


def _ConfigureClientForPGDataSet(db_vm, hammer_vm):
  # updating build_pgdb.tcl script
  context = {'ip_address': db_vm.internal_ip,
             'db_type': FLAGS.intel_hammerdb_db_type,
             'bm_type': FLAGS.intel_hammerdb_benchmark_type,
             'pg_threads': _GetDBThreadsForBuildSchema(hammer_vm),
             'pg_ware': _GetNumWarehouses(db_vm),
             'enable_timestamps': FLAGS.intel_hammerdb_enable_timestamps}
  local_path = data.ResourcePath("intel_hammerdb/build_pgdb.tcl.j2")
  remote_path = posixpath.join("{0}".format(HAMMERDB_HOME),
                               os.path.splitext(os.path.basename("intel_hammerdb/"
                                                                 "build_pgdb.tcl.j2"))[0])
  hammer_vm.RenderTemplate(local_path, remote_path, context=context)


def _GetMySQLHostAddr(db_vm):
  if FLAGS.intel_hammerdb_run_single_node:
    if db_vm.BASE_OS_TYPE == "debian":
      host_addr = "localhost"
    elif db_vm.BASE_OS_TYPE == "rhel":
      host_addr = "127.0.0.1"
  else:
     host_addr = db_vm.internal_ip
  return host_addr


def _ConfigureClientForMYSQLDataSet(db_vm, hammer_vm):
  host_addr = _GetMySQLHostAddr(db_vm)
  # updating build_mysql.tcl script
  context = {'mysql_threads': _GetDBThreadsForBuildSchema(hammer_vm),
             'mysql_addr': host_addr,
             'mysql_pass': FLAGS.intel_hammerdb_mysql_password,
             'mysql_ware': _GetNumWarehouses(db_vm),
             'enable_timestamps': FLAGS.intel_hammerdb_enable_timestamps}
  local_path = data.ResourcePath("intel_hammerdb/mysql/build_mysql.tcl.j2")
  remote_path = posixpath.join("{0}".format(HAMMERDB_HOME),
                               os.path.splitext(os.path.basename("intel_hammerdb/"
                                                                 "build_mysql.tcl.j2"))[0])
  hammer_vm.RenderTemplate(local_path, remote_path, context=context)

  if FLAGS.intel_hammerdb_version == "4.0":
    if hammer_vm.BASE_OS_TYPE == "debian":
      hammer_vm.RemoteCommand("sed -i 's/tmp\/mysql.sock/var\/run\/mysqld\/mysqld.sock/'"
                              " {0}/config/mysql.xml".format(HAMMERDB_HOME))
    elif hammer_vm.BASE_OS_TYPE == "rhel":
      hammer_vm.RemoteCommand("sed -i 's/tmp\/mysql.sock/scratch\/data\/mysql\/mysql.sock/'"
                              " {0}/config/mysql.xml".format(HAMMERDB_HOME))


def _ConfigureClientForHammerRun(db_vm, hammer_vm):

  convert_log_txt_file = "convert_hammer_log_txt.tcl"
  srcPath = posixpath.join(BENCHMARK_NAME, convert_log_txt_file)

  if FLAGS.intel_hammerdb_db_type == 'pg':
    hammer_users_list = _GetHammerNumUsers(db_vm)
    # updating run_hammer.tcl script
    context = {'ip_address': db_vm.internal_ip,
               'db_type': FLAGS.intel_hammerdb_db_type,
               'bm_type': FLAGS.intel_hammerdb_benchmark_type,
               'hm_vus': hammer_users_list,
               'pg_rampup': FLAGS.intel_hammerdb_tpcc_rampup,
               'pg_allwh': FLAGS.intel_hammerdb_tpcc_postgres_allwarehouse,
               'pg_duration': FLAGS.intel_hammerdb_tpcc_runtime,
               'enable_timestamps': FLAGS.intel_hammerdb_enable_timestamps,
               'pg_timeprofile': FLAGS.intel_hammerdb_enable_timeprofile}

    local_path = data.ResourcePath("intel_hammerdb/run_hammer.tcl.j2")
    remote_path = posixpath.join("{0}".format(HAMMERDB_HOME),
                                 os.path.splitext(os.path.basename("intel_hammerdb/"
                                                                   "run_hammer.tcl.j2"))[0])
    hammer_vm.RenderTemplate(local_path, remote_path, context=context)

    hammer_vm.PushFile(data.ResourcePath(srcPath), "{0}/".format(HAMMERDB_HOME))
  elif FLAGS.intel_hammerdb_db_type == 'mysql':
    hammer_users_list = _GetHammerNumUsers(db_vm)
    host_addr = _GetMySQLHostAddr(db_vm)
    # updating run_hammer.tcl script
    context = {'mysql_hammer_vus': hammer_users_list,
               'mysql_rampup': FLAGS.intel_hammerdb_tpcc_rampup,
               'mysql_duration': FLAGS.intel_hammerdb_tpcc_runtime,
               'host_addr': host_addr,
               'mysql_pass': FLAGS.intel_hammerdb_mysql_password,
               'mysql_timeprofile': FLAGS.intel_hammerdb_enable_timeprofile}

    local_path = data.ResourcePath("intel_hammerdb/mysql/run_hammer_mysql.tcl.j2")
    remote_path = posixpath.join("{0}".format(HAMMERDB_HOME),
                                 os.path.splitext(os.path.basename("intel_hammerdb/"
                                                                   "run_hammer_mysql.tcl.j2"))[0])
    hammer_vm.RenderTemplate(local_path, remote_path, context=context)

    hammer_vm.PushFile(data.ResourcePath(srcPath), "{0}/".format(HAMMERDB_HOME))
  else:
    raise Exception("Incorrect choice of database !!! ")


def _SetHugePages(vm):

  PGDB_MNT_DIR = vm.GetScratchDir()
  # Save original hugepages setting
  vm.RemoteCommand("/sbin/sysctl -n vm.nr_hugepages > {0}".format(HUGEPAGES_TMP_FILE))

  hugepagesz = vm.RemoteCommand("cat /proc/meminfo | grep Hugepagesize | "
                                "awk -F' ' '{print $2}'")[0].rstrip("\n")

  mem_available = int(vm.RemoteCommand("cat /proc/meminfo | grep MemAvailable | "
                                       "awk -F' ' '{print $2}'")[0].rstrip("\n"))

  mem_75GB_in_KB = 75 * 1024 * 1024
  # If users decides the num of huge pages use as is
  if "intel_hammerdb_tpcc_postgres_num_hugepages" in flag_util.GetProvidedCommandLineFlags():
    numOfHugePages = FLAGS.intel_hammerdb_tpcc_postgres_num_hugepages
  # If user has not mentioned this & system has more than 75GB available memory, then use 35000
  elif mem_available > mem_75GB_in_KB:
    numOfHugePages = 35000
  # Otherwise calculate the value
  else:
    hugepagesz = vm.RemoteCommand("cat /proc/meminfo | grep Hugepagesize | "
                                  "awk -F' ' '{print $2}'")[0].rstrip("\n")
    PG_pid = vm.RemoteCommand("sudo -u postgres head -1 {0}/data/postmaster.pid"
                              . format(PGDB_MNT_DIR))[0].rstrip()
    memPeak = vm.RemoteCommand("cat /proc/{0}/status | grep VmPeak | awk -F' ' '{{print $2}}'"
                               . format(PG_pid))[0].rstrip("\n")

    numOfHugePages = int(int(memPeak) / int(hugepagesz))
    # Reserving more hugepages for other postgres memory needs
    bufHugePages = int(numOfHugePages * 0.05)
    numOfHugePages = numOfHugePages + bufHugePages

  hugePgMem = numOfHugePages * int(hugepagesz)

  if hugePgMem > int(mem_available):
    raise Exception("Memory for Num of Huge pages cannot exceed the available memory!")

  hp_off = "huge_pages = off"

  if FLAGS.intel_hammerdb_tpcc_postgres_hugepages == "on":
    hp_option = "huge_pages = on"
  else:
    hp_option = "huge_pages = try"

  vm.RemoteCommand('sudo -u postgres sed -i "s/{hp_off}/{hp_option}/" '
                   '{0}/data/postgresql.conf'. format(PGDB_MNT_DIR, hp_off=hp_off,
                                                      hp_option=hp_option))

  cmd = "sudo sysctl -w vm.nr_hugepages={0}".format(numOfHugePages)
  vm.RemoteCommand(cmd)

  hugepagesTotal = int(vm.RemoteCommand("cat /proc/meminfo | grep HugePages_Total | "
                                        "awk -F' ' '{print $2}'")[0].rstrip("\n"))
  if hugepagesTotal != numOfHugePages:
    raise Exception("Requested number of Hugepages have not been allocated by the system")


def _GetSharedBuffers(vm):
  mem_total = vm.RemoteCommand("cat /proc/meminfo | grep MemTotal | "
                               "awk -F' ' '{print $2}'")[0].rstrip("\n")
  shrd_buff = int(round(FLAGS.intel_hammerdb_tpcc_postgres_shared_buffers_ratio * int(mem_total)))
  shrd_buff_mb = int(shrd_buff / (1024))
  shared_buffers = str(shrd_buff_mb) + "MB"
  return shared_buffers


def _SetKernelParams(vm):

  vm.RemoteCommand('sudo cp /etc/sysctl.conf /etc/hammerdb_sysctl_tmp.conf')

  settings = "kernel.sem = 250 32000 100 128 \n"
  settings += "net.ipv4.ip_local_port_range = 9000 65500 \n"
  settings += "net.core.rmem_default = 262144 \n"
  settings += "net.core.rmem_max = 4194304 \n"
  settings += "net.core.wmem_default = 262144 \n"
  settings += "net.core.wmem_max = 1048576 \n"
  settings += "fs.aio-max-nr = 1048576 \n"
  settings += "fs.file-max = 6815744 \n"

  vm.RemoteCommand('echo -e "{0}" | sudo tee -a /etc/sysctl.conf'. format(settings))
  vm.RemoteCommand('sudo sysctl -p')


def _ClearCache(vm):
  vm.RemoteCommand("sync && echo 3 | sudo tee /proc/sys/vm/drop_caches")


def _VmConfig(vm):

  _SetKernelParams(vm)
  _ClearCache(vm)

  mem_total = vm.RemoteCommand("cat /proc/meminfo | grep MemTotal | "
                               "awk -F' ' '{print $2}'")[0].rstrip("\n")
  mem_available = vm.RemoteCommand("cat /proc/meminfo | grep MemAvailable | "
                                   "awk -F' ' '{print $2}'")[0].rstrip("\n")

  memlock = int(round(FLAGS.intel_hammerdb_tpcc_postgres_memlock_ratio * int(mem_total)))

  vm.RemoteCommand('echo -e "postgres soft memlock {0}" | sudo tee -a /etc/security/limits.conf'
                   .format(memlock))
  vm.RemoteCommand('echo -e "postgres hard memlock {0}" | sudo tee -a /etc/security/limits.conf'
                   .format(memlock))

  max_locked_mem = vm.RemoteCommand("sudo su postgres -c 'ulimit -a' | grep 'max locked memory'",
                                    ignore_failure=True)[0].rstrip("\n")
  if max_locked_mem:
    retVal = vm.RemoteCommand("sudo su postgres -c 'ulimit -a' | grep 'max locked memory'"
                              " | awk -F' ' '{print $6}'")[0].rstrip("\n")
  else:
    retVal = vm.RemoteCommand("sudo su postgres -c 'ulimit -a' | grep 'locked memory'"
                              " | awk -F' ' '{print $3}'")[0].rstrip("\n")
  if memlock != int(retVal):
    raise Exception("Memlock value has not been set correctly!")

  if "intel_hammerdb_tpcc_postgres_shared_buffers" not in flag_util.GetProvidedCommandLineFlags():
    shrd_buff = int(round(FLAGS.intel_hammerdb_tpcc_postgres_shared_buffers_ratio * int(mem_total)))

    if shrd_buff > memlock:
      raise Exception("Shared buffers cannot exceed user memlock value!")
    if shrd_buff > int(mem_available):
      raise Exception("Shared buffers cannot exceed the available memory!")

  if "intel_hammerdb_tpcc_postgres_max_worker_process" not in flag_util.GetProvidedCommandLineFlags():
    FLAGS.intel_hammerdb_tpcc_postgres_max_worker_process = vm.num_cpus


def _CheckFirewall(vm):
  enableStatus, _ = vm.RemoteCommand('sudo systemctl is-enabled firewalld', ignore_failure=True,
                                     suppress_warning=True)
  if "enabled" in enableStatus:
    runStatus, _ = vm.RemoteCommand('sudo systemctl status firewalld',
                                    ignore_failure=True, suppress_warning=True)
    if runStatus.find("active (running)") != -1:
      vm.RemoteCommand("touch {0}".format(FIREWALL_CHECK_FILE))
      vm.RemoteCommand("sudo systemctl stop firewalld")


def _ConfigurePGDatabase(vm):
  # updating the database settings specifically postgres settings below with the user issued values
  PGDB_DIR = "/usr/local/pgsql/bin"
  _CheckFirewall(vm)

  PGDB_MNT_DIR = vm.GetScratchDir()
  cmds = ['cd /',
          'sudo mkdir -p {0}/data'.format(PGDB_MNT_DIR),
          'sudo useradd postgres || true',
          'sudo chown postgres {0}/data'.format(PGDB_MNT_DIR),
          'sudo -u postgres {0}/initdb -D {1}/data'.format(PGDB_DIR, PGDB_MNT_DIR)]

  vm.RobustRemoteCommand(" && ".join(cmds))

  mem_available = int(vm.RemoteCommand("cat /proc/meminfo | grep MemAvailable | "
                                       "awk -F' ' '{print $2}'")[0].rstrip("\n"))

  mem_75GB_in_KB = 75 * 1024 * 1024

  shared_buffers = FLAGS.intel_hammerdb_tpcc_postgres_shared_buffers
  # If shared buffers is not mentioned by user
  if "intel_hammerdb_tpcc_postgres_shared_buffers" not in flag_util.GetProvidedCommandLineFlags():
    if mem_available > mem_75GB_in_KB:
      shared_buffers = "64GB"
    else:
      shared_buffers = _GetSharedBuffers(vm)

  _VmConfig(vm)

  # If the user wants to use huge pages, we start the database with this option off and then
  # calculate the num of hugepages ans turn this option on.
  if FLAGS.intel_hammerdb_tpcc_postgres_hugepages == "on" or FLAGS.intel_hammerdb_tpcc_postgres_hugepages == "try":
    hugepages_start_val = "off"
  # If user wants try or off , use that directly in the postgres options
  else:
    hugepages_start_val = FLAGS.intel_hammerdb_tpcc_postgres_hugepages

  context = {'port': FLAGS.intel_hammerdb_port,
             'max_connections': FLAGS.intel_hammerdb_tpcc_postgres_max_connections,
             'shared_buffers': shared_buffers,
             'hugepages': hugepages_start_val,
             'temp_buffers': FLAGS.intel_hammerdb_tpcc_postgres_temp_buffers,
             'work_mem': FLAGS.intel_hammerdb_tpcc_postgres_work_mem,
             'maintenance_work_mem': FLAGS.intel_hammerdb_tpcc_postgres_maintenance_work_mem,
             'autovacuum_work_mem': FLAGS.intel_hammerdb_tpcc_postgres_autovacuum_work_mem,
             'max_stack_depth': FLAGS.intel_hammerdb_tpcc_postgres_max_stack_depth,
             'dynamic_shared_memory_type': FLAGS.intel_hammerdb_tpcc_postgres_dynamic_shared_memory_type,
             'max_files_per_process': FLAGS.intel_hammerdb_tpcc_postgres_max_files_per_process,
             'io_concur': FLAGS.intel_hammerdb_tpcc_postgres_io_concur,
             'max_worker_process': FLAGS.intel_hammerdb_tpcc_postgres_max_worker_process,
             'wal_level': FLAGS.intel_hammerdb_tpcc_postgres_wal_level,
             'syn_commit': FLAGS.intel_hammerdb_tpcc_postgres_syn_commit,
             'wal_buffers': FLAGS.intel_hammerdb_tpcc_postgres_wal_buffers,
             'max_wal_senders': FLAGS.intel_hammerdb_tpcc_postgres_max_wal_senders,
             'log_timezone': FLAGS.intel_hammerdb_tpcc_postgres_log_timezone,
             'timezone': FLAGS.intel_hammerdb_tpcc_postgres_timezone,
             'max_locks_per_transaction': FLAGS.intel_hammerdb_tpcc_postgres_max_locks_per_transaction,
             'max_pred_locks_per_transaction': FLAGS.intel_hammerdb_tpcc_postgres_max_pred_locks_per_transaction,
             'min_wal_size': FLAGS.intel_hammerdb_tpcc_postgres_min_wal_size,
             'max_wal_size': FLAGS.intel_hammerdb_tpcc_postgres_max_wal_size,
             'checkpoint_completion_target':
             FLAGS.intel_hammerdb_tpcc_postgres_checkpoint_completion_target,
             'checkpoint_warning': FLAGS.intel_hammerdb_tpcc_postgres_checkpoint_warning,
             'random_page_cost': FLAGS.intel_hammerdb_tpcc_postgres_random_page_cost,
             'cpu_tuple_cost': FLAGS.intel_hammerdb_tpcc_postgres_cpu_tuple_cost,
             'effective_cache_size': FLAGS.intel_hammerdb_tpcc_postgres_effective_cache_size,
             'autovacuum': FLAGS.intel_hammerdb_tpcc_postgres_autovacuum,
             'autovacuum_max_workers': FLAGS.intel_hammerdb_tpcc_postgres_autovacuum_max_workers,
             'autovacuum_freeze_max_age':
             FLAGS.intel_hammerdb_tpcc_postgres_autovacuum_freeze_max_age,
             'autovacuum_vacuum_cost_limit':
             FLAGS.intel_hammerdb_tpcc_postgres_autovacuum_vacuum_cost_limit,
             'vacuum_freeze_min_age': FLAGS.intel_hammerdb_tpcc_postgres_vacuum_freeze_min_age
             }

  local_path = data.ResourcePath("intel_hammerdb/postgresql.conf.j2")
  remote_path = posixpath.join('{0}'.format(vm_util.VM_TMP_DIR),
                               os.path.splitext(os.path.basename("intel_hammerdb"
                                                                 "/postgresql.conf.j2"))[0])
  vm.RenderTemplate(local_path, remote_path, context=context)
  vm.PushFile(data.ResourcePath("intel_hammerdb/pg_hba.conf"), "{0}".format(vm_util.VM_TMP_DIR))

  cmds = ['sudo cp {0}/pg_hba.conf {1}/data'.format(vm_util.VM_TMP_DIR, PGDB_MNT_DIR),
          'sudo cp {0}/postgresql.conf {1}/data'.format(vm_util.VM_TMP_DIR, PGDB_MNT_DIR)]
  vm.RemoteCommand(" && ".join(cmds))

  cmd = ['cd {0} && sudo -u postgres {1}/pg_ctl -D {2}/data -l {3}/data/pgdblog start'
         . format(vm_util.VM_TMP_DIR, PGDB_DIR, PGDB_MNT_DIR, PGDB_MNT_DIR)]

  pg_start_stdout, pg_start_stderr = vm.RobustRemoteCommand(cmd, ignore_failure=True)
  if pg_start_stderr:
    pgdblog_stdout, pgdblog_stderr = vm.RemoteCommand('sudo cat {0}/data/pgdblog'
                                                      .format(PGDB_MNT_DIR))
    logging.info("\nThe pgdblog output is {0}\n".format(pgdblog_stdout))
    raise Exception("{0} \n {1}". format(pg_start_stdout, pg_start_stderr))

  if (FLAGS.intel_hammerdb_tpcc_postgres_hugepages == "on" or
      FLAGS.intel_hammerdb_tpcc_postgres_hugepages == "try"):
    _SetHugePages(vm)

    cmds = ['cd {0} && sudo -u postgres {1}/pg_ctl -D {2}/data -l {3}/data/pgdblog restart'
            . format(vm_util.VM_TMP_DIR, PGDB_DIR, PGDB_MNT_DIR, PGDB_MNT_DIR)]
    pg_restart_stdout, pg_restart_stderr = vm.RobustRemoteCommand(cmds, ignore_failure=True)
    if pg_restart_stderr:
      pgdblog_stdout, pgdblog_stderr = vm.RemoteCommand('sudo cat {0}/data/pgdblog'
                                                        .format(PGDB_MNT_DIR))
      logging.info("\nThe pgdblog output is {0}\n".format(pgdblog_stdout))
      raise Exception("Examine the pgdblog")


def _GetMySQLBufferPoolSize(vm):
  mem_available = int(vm.RemoteCommand("cat /proc/meminfo | grep MemAvailable | "
                                       "awk -F' ' '{print $2}'")[0].rstrip("\n"))
  mem_75GB_in_KB = 75 * 1024 * 1024
  innodb_buffer_pool_size = FLAGS.intel_hammerdb_tpcc_mysql_innodb_buffer_pool_size
  # If buffer pool size is not mentioned by user
  if ("intel_hammerdb_tpcc_mysql_innodb_buffer_pool_size" not in
      flag_util.GetProvidedCommandLineFlags()):
    if mem_available > mem_75GB_in_KB:
      innodb_buffer_pool_size = "64000M"
    else:
      mem_total = vm.RemoteCommand("cat /proc/meminfo | grep MemTotal | "
                                   "awk -F' ' '{print $2}'")[0].rstrip("\n")
      innodb_buffer_pool_size = int(round(FLAGS.intel_hammerdb_tpcc_mysql_innodb_buffers_ratio *
                                          int(mem_total)))
      # Change the buffer size from KB to Bytes
      innodb_buffer_pool_size = innodb_buffer_pool_size * 1024
  else:
    if int(innodb_buffer_pool_size) > (mem_available * 1024):
      raise Exception("Innodb buffer pool size is greater than available memory")
  return innodb_buffer_pool_size


def _ConfigureMYSQLDebDatabase(vm):

  MYSQL_MNT_DIR = vm.GetScratchDir()
  MYSQL_DIR = "{0}/mysql".format(MYSQL_MNT_DIR)
  MYSQL_CNF = "/etc/mysql/mysql.conf.d/mysqld.cnf"
  MYSQL_DEFAULT_DIR = "/var/lib/mysql"

  context = _GetContextForMySQL(vm)

  cmds = ['sudo mkdir -p {0}'.format(MYSQL_DIR),
          'sudo chown mysql:mysql {0}'.format(MYSQL_DIR),
          'sudo chmod 755 {0}'.format(MYSQL_DIR),
          'sudo rsync -av {0} {1}'.format(MYSQL_DEFAULT_DIR, MYSQL_MNT_DIR),
          'sudo mv {0} /var/lib/mysql.bak'.format(MYSQL_DEFAULT_DIR),
          'sudo rm {0}/ib_logfile0  {0}/ib_logfile1'.format(MYSQL_DIR),
          'sudo ln -sf /etc/apparmor.d/usr.sbin.mysqld /etc/apparmor.d/disable/',
          'sudo apparmor_parser -R /etc/apparmor.d/usr.sbin.mysqld',
          'sudo mkdir {0}/mysql -p'.format(MYSQL_DEFAULT_DIR)]

  vm.RemoteCommand(' && '.join(cmds))

  context = _GetContextForMySQL(vm)
  local_path = data.ResourcePath("intel_hammerdb/mysql/mysqld_deb.cnf.j2")
  remote_path = posixpath.join('{0}'.format(vm_util.VM_TMP_DIR),
                               os.path.splitext(os.path.basename("intel_hammerdb"
                                                                 "/mysqld_deb.cnf.j2"))[0])
  vm.RenderTemplate(local_path, remote_path, context=context)
  vm.RemoteCommand("sudo cp {0}/mysqld_deb.cnf {1}".format(vm_util.VM_TMP_DIR, MYSQL_CNF))

  _ClearCache(vm)

  _SetMySQLKernelParams(vm)
  if FLAGS.intel_hammerdb_tpcc_mysql_hugepages == 'on':
    innodb_buf_pool_size_B = _SetMySQLHugePages(vm)
    vm.RemoteCommand('echo -e "\nlarge-pages" | sudo tee -a {0}'.format(MYSQL_CNF))
    vm.RemoteCommand('sudo sed -i "/innodb_buffer_pool_size*/c\innodb_buffer_pool_size={0}"'
                     ' {1}'.format(innodb_buf_pool_size_B, MYSQL_CNF))

  host_addr = _GetMySQLHostAddr(vm)
  if FLAGS.intel_hammerdb_run_single_node:
    cmds = ["echo '\nbind-address='{0}'' | sudo tee -a {1}".format(host_addr, MYSQL_CNF),
            'sudo systemctl start mysql',
            "sudo mysql -uroot -proot mysql -e \"ALTER USER 'root'@'localhost' IDENTIFIED WITH "
            " mysql_native_password BY '{0}';\"".format(FLAGS.intel_hammerdb_mysql_password)]
  else:
    cmds = ["echo '\nbind-address='{0}'' | sudo tee -a {1}".format(host_addr, MYSQL_CNF),
            'sudo systemctl start mysql',
            "sudo mysql -uroot -p{0} -e \"CREATE USER 'root'@'%' IDENTIFIED BY '{0}';\"".
            format(FLAGS.intel_hammerdb_mysql_password),
            "sudo mysql -uroot -p{0} -e \"GRANT ALL PRIVILEGES ON *.* TO 'root'@'%';\"".
            format(FLAGS.intel_hammerdb_mysql_password),
            "sudo mysql -uroot -p{0} -e \"FLUSH PRIVILEGES;\""
            .format(FLAGS.intel_hammerdb_mysql_password)]

  vm.RobustRemoteCommand(' && '.join(cmds))


def _ConfigureMYSQLDebDatabaseForARM(vm):
  MYSQL_CNF = "/etc/my.cnf"

  context = _GetContextForMySQL(vm)
  local_path = data.ResourcePath("intel_hammerdb/mysql/mysqld_arm_deb.cnf.j2")
  remote_path = posixpath.join('{0}'.format(vm_util.VM_TMP_DIR),
                               os.path.splitext(os.path.basename("intel_hammerdb"
                                                                 "/mysqld_arm_deb.cnf.j2"))[0])
  vm.RenderTemplate(local_path, remote_path, context=context)
  vm.RemoteCommand("sudo cp {0}/mysqld_arm_deb.cnf {1}".format(vm_util.VM_TMP_DIR, MYSQL_CNF))

  _ClearCache(vm)

  _SetMySQLKernelParams(vm)

  cmds = ['sudo groupadd mysql',
          'sudo useradd -r -g mysql -s /bin/false mysql',
          'sudo /usr/local/mysql/bin/mysqld --defaults-file=/etc/my.cnf  --initialize '
          '--default-storage-engine=innodb --datadir=/scratch/data/ --user=mysql',
          'sudo cp /usr/local/mysql/support-files/mysql.server /etc/init.d/mysqld',
          'sudo /etc/init.d/mysqld start']
  vm.RobustRemoteCommand(' && '.join(cmds))

  if FLAGS.intel_hammerdb_tpcc_mysql_hugepages == 'on':
    innodb_buf_pool_size_B = _SetMySQLHugePages(vm)
    vm.RemoteCommand('echo -e "\nlarge-pages" | sudo tee -a {0}'.format(MYSQL_CNF))
    vm.RemoteCommand('sudo sed -i "/innodb_buffer_pool_size*/c\innodb_buffer_pool_size={0}"'
                     ' {1}'.format(innodb_buf_pool_size_B, MYSQL_CNF))

  host_addr = _GetMySQLHostAddr(vm)

  cmds = [("echo '\nbind-address='{0}'' | sudo tee -a {1}".format(host_addr, MYSQL_CNF)),
          'sudo /etc/init.d/mysqld start',
          "pass=$(sudo grep 'A temporary password' /tmp/error.log | "
          "awk -F 'host: ' '{print $2}')",
          "sudo /usr/local/mysql/bin/mysql -uroot -p$pass -h\"localhost\" "
          " --connect-expired-password mysql -e \"ALTER USER 'root'@'localhost' IDENTIFIED BY '{0}';\"".
          format(FLAGS.intel_hammerdb_mysql_password)]
  stdout, stderr = vm.RobustRemoteCommand(' && '.join(cmds), ignore_failure=True)
  print(stdout, stderr)

  cmds = ["sudo /usr/local/mysql/bin/mysql -uroot -p{0} -e \"CREATE USER 'root'@'%' IDENTIFIED BY '{0}';\"".
          format(FLAGS.intel_hammerdb_mysql_password),
          "sudo /usr/local/mysql/bin/mysql -uroot -p{0} -e \"GRANT ALL PRIVILEGES ON *.* TO 'root'@'%';\"".
          format(FLAGS.intel_hammerdb_mysql_password),
          "sudo /usr/local/mysql/bin/mysql -uroot -p{0} -e \"FLUSH PRIVILEGES;\""
          .format(FLAGS.intel_hammerdb_mysql_password)]

  stdout, stderr = vm.RobustRemoteCommand(' && '.join(cmds), ignore_failure=True)
  print(stdout, stderr)


def _GetContextForMySQL(vm):

  innodb_buffer_pool_size = _GetMySQLBufferPoolSize(vm)
  context = {'mysql_port': 3306,
             'innodb_buffer_pool_size': innodb_buffer_pool_size,
             'innodb_buffer_pool_instances': FLAGS.intel_hammerdb_tpcc_mysql_innodb_buffer_pool_instances,
             'innodb_log_buffer_size': FLAGS.intel_hammerdb_tpcc_mysql_innodb_log_buffer_size,
             'innodb_doublewrite': FLAGS.intel_hammerdb_tpcc_mysql_innodb_doublewrite,
             'innodb_thread_concurrency': FLAGS.intel_hammerdb_tpcc_mysql_innodb_thread_concurrency,
             'innodb_flush_log_at_trx_commit':
             FLAGS.intel_hammerdb_tpcc_mysql_innodb_flush_log_at_trx_commit,
             'innodb_max_dirty_pages_pct': FLAGS.intel_hammerdb_tpcc_mysql_innodb_max_dirty_pages_pct,
             'innodb_max_dirty_pages_pct_lwm':
             FLAGS.intel_hammerdb_tpcc_mysql_innodb_max_dirty_pages_pct_lwm,
             'join_buffer_size': FLAGS.intel_hammerdb_tpcc_mysql_join_buffer_size,
             'sort_buffer_size': FLAGS.intel_hammerdb_tpcc_mysql_sort_buffer_size,
             'innodb_use_native_aio': FLAGS.intel_hammerdb_tpcc_mysql_innodb_use_native_aio,
             'innodb_stats_persistent': FLAGS.intel_hammerdb_tpcc_mysql_innodb_stats_persistent,
             'innodb_spin_wait_delay': FLAGS.intel_hammerdb_tpcc_mysql_innodb_spin_wait_delay,
             'innodb_max_purge_lag_delay': FLAGS.intel_hammerdb_tpcc_mysql_innodb_max_purge_lag_delay,
             'innodb_max_purge_lag': FLAGS.intel_hammerdb_tpcc_mysql_innodb_max_purge_lag,
             'innodb_flush_method': FLAGS.intel_hammerdb_tpcc_mysql_innodb_flush_method,
             'innodb_checksum_algorithm': FLAGS.intel_hammerdb_tpcc_mysql_innodb_checksum_algorithm,
             'innodb_io_capacity': FLAGS.intel_hammerdb_tpcc_mysql_innodb_io_capacity,
             'innodb_io_capacity_max': FLAGS.intel_hammerdb_tpcc_mysql_innodb_io_capacity_max,
             'innodb_lru_scan_depth': FLAGS.intel_hammerdb_tpcc_mysql_innodb_lru_scan_depth,
             'innodb_change_buffering': FLAGS.intel_hammerdb_tpcc_mysql_innodb_change_buffering,
             'innodb_read_only': FLAGS.intel_hammerdb_tpcc_mysql_innodb_read_only,
             'innodb_page_cleaners': FLAGS.intel_hammerdb_tpcc_mysql_innodb_page_cleaners,
             'innodb_undo_log_truncate': FLAGS.intel_hammerdb_tpcc_mysql_innodb_undo_log_truncate,
             'innodb_adaptive_flushing': FLAGS.intel_hammerdb_tpcc_mysql_innodb_adaptive_flushing,
             'innodb_flush_neighbors': FLAGS.intel_hammerdb_tpcc_mysql_innodb_flush_neighbors,
             'innodb_read_io_threads': FLAGS.intel_hammerdb_tpcc_mysql_innodb_read_io_threads,
             'innodb_write_io_threads': FLAGS.intel_hammerdb_tpcc_mysql_innodb_write_io_threads,
             'innodb_purge_threads': FLAGS.intel_hammerdb_tpcc_mysql_innodb_purge_threads,
             'innodb_adaptive_hash_index': FLAGS.intel_hammerdb_tpcc_mysql_innodb_adaptive_hash_index}
  return context


def _SetMySQLKernelParams(vm):
  vm.RemoteCommand('echo -e "mysql soft memlock unlimited" | sudo tee -a /etc/security/limits.conf')
  vm.RemoteCommand('echo -e "mysql hard memlock unlimited" | sudo tee -a /etc/security/limits.conf')


def _IsDefinedInnoDBBufferSize(totalMemForHugePages_KB):
  innodb_buffer_pool_size_KB = ""
  totalMemForHugePages_B = totalMemForHugePages_KB * 1024
  if ("intel_hammerdb_tpcc_mysql_innodb_buffer_pool_size" in
      flag_util.GetProvidedCommandLineFlags()):
        if int(FLAGS.intel_hammerdb_tpcc_mysql_innodb_buffer_pool_size) > totalMemForHugePages_B:
          raise Exception("Innodb buffer pool size cannot exceed the huge pages memory!")
        innodb_buffer_pool_size_KB = int(int(FLAGS.intel_hammerdb_tpcc_mysql_innodb_buffer_pool_size)
                                         / 1024)
  return innodb_buffer_pool_size_KB


def _SetMySQLHugePages(vm):
  vm.RemoteCommand('sudo cp /etc/sysctl.conf /etc/hammerdb_sysctl_tmp.conf')
  # Save original hugepages setting
  vm.RemoteCommand("/sbin/sysctl -n vm.nr_hugepages > {0}".format(HUGEPAGES_TMP_FILE))

  hugepagesz_KB = int(vm.RemoteCommand("cat /proc/meminfo | grep Hugepagesize | "
                                       "awk -F' ' '{print $2}'")[0].rstrip("\n"))

  mem_available_KB = int(vm.RemoteCommand("cat /proc/meminfo | grep MemAvailable | "
                                          "awk -F' ' '{print $2}'")[0].rstrip("\n"))

  mem_75GB_in_KB = 75 * 1024 * 1024
  innodb_buffer_pool_size_KB = ""
  # If users decides the num of huge pages use as is
  if "intel_hammerdb_tpcc_mysql_num_hugepages" in flag_util.GetProvidedCommandLineFlags():
    numOfHugePages = int(FLAGS.intel_hammerdb_tpcc_mysql_num_hugepages)
    totalMemForHugePages_KB = numOfHugePages * hugepagesz_KB

    if totalMemForHugePages_KB > int(0.75 * mem_available_KB):
      raise Exception("Huge page memory more than 75% of the available memory is not recommended"
                      "Please reduce the num of hugepages!")

    innodb_buffer_pool_size_KB = _IsDefinedInnoDBBufferSize(totalMemForHugePages_KB)
    if not innodb_buffer_pool_size_KB:
      innodb_buffer_pool_size_KB = int(0.9 * totalMemForHugePages_KB)

  # If user has not mentioned this & system has more than 75GB available memory, then use 35000
  elif mem_available_KB > mem_75GB_in_KB:
    numOfHugePages = 35000
    totalMemForHugePages_KB = numOfHugePages * hugepagesz_KB

    innodb_buffer_pool_size_KB = _IsDefinedInnoDBBufferSize(totalMemForHugePages_KB)
    if not innodb_buffer_pool_size_KB:
      innodb_buffer_pool_size_KB = 64 * 1024 * 1024

  # Otherwise calculate the value
  else:
    totalMemForHugePages_KB = int(0.75 * mem_available_KB)

    innodb_buffer_pool_size_KB = _IsDefinedInnoDBBufferSize(totalMemForHugePages_KB)
    if not innodb_buffer_pool_size_KB:
      innodb_buffer_pool_size_KB = int(0.9 * totalMemForHugePages_KB)

    numOfHugePages = int(totalMemForHugePages_KB / hugepagesz_KB)

  numOfNormalPages = int(innodb_buffer_pool_size_KB / 4)
  innodbLargestBlockSize = int((innodb_buffer_pool_size_KB * 1024) /
                               FLAGS.intel_hammerdb_tpcc_mysql_innodb_buffer_pool_instances)

  getGID = vm.RemoteCommand("id mysql | awk -F' ' '{print $2}'")[0].rstrip("\n")
  match = re.search(r'gid=([0-9]*)', getGID)

  vm.RemoteCommand('echo -e "vm.hugetlb_shm_group={0}" | sudo tee -a /etc/sysctl.conf'
                   .format(match.group(1)))
  vm.RemoteCommand('echo -e "kernel.shmmax={0}" | sudo tee -a /etc/sysctl.conf'
                   .format(innodbLargestBlockSize))
  vm.RemoteCommand('echo -e "kernel.shmall={0}" | sudo tee -a /etc/sysctl.conf'
                   .format(numOfNormalPages))

  vm.RemoteCommand('sudo sysctl -p')

  cmd = "sudo sysctl -w vm.nr_hugepages={0}".format(numOfHugePages)
  vm.RemoteCommand(cmd)

  hugePgMem = numOfHugePages * int(hugepagesz_KB)

  if hugePgMem > int(mem_available_KB):
    raise Exception("Memory for Num of Huge pages cannot exceed the available memory!")

  innodb_buffer_pool_size_B = innodb_buffer_pool_size_KB * 1024
  return innodb_buffer_pool_size_B


def _ConfigureMYSQLRhelDatabase(vm):
  MYSQL_MNT_DIR = vm.GetScratchDir()
  MYSQL_DIR = "{0}/data".format(MYSQL_MNT_DIR)
  MYSQL_CNF = "/etc/my.cnf"

  cmds = ['echo "bind-address=\"127.0.0.1\"" | sudo tee -a {0}'.format(MYSQL_CNF),
          'echo "port=3306" | sudo tee -a {0}'.format(MYSQL_CNF),
          "echo 'default-authentication-plugin=mysql_native_password' | sudo tee "
          " -a {0}".format(MYSQL_CNF)]

  vm.RemoteCommand(' && '.join(cmds))

  vm.RobustRemoteCommand('sudo systemctl restart mysqld')
  cmds = ["pass=$(sudo grep 'A temporary password' /var/log/mysqld.log | "
          "awk -F 'host: ' '{print $2}')",
          "sudo mysql -uroot -p$pass -h\"127.0.0.1\" --connect-expired-password mysql -e "
          "\"ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '{0}';\""
          .format(FLAGS.intel_hammerdb_mysql_password)]
  vm.RemoteCommand(' && '.join(cmds))

  vm.RobustRemoteCommand('sudo systemctl stop mysqld')

  cmds = ['sudo mkdir -p {0}'.format(MYSQL_DIR),
          'sudo mv /var/lib/mysql {0}/'.format(MYSQL_DIR),
          'sudo chown -R mysql:mysql {0}'.format(MYSQL_DIR),
          'sudo chcon -R -t mysqld_db_t {0}'.format(MYSQL_DIR),
          'sudo semanage fcontext -a -t mysqld_db_t "{0}/data(/.*)?"'.format(MYSQL_MNT_DIR),
          'sudo restorecon -Rv {0}'.format(MYSQL_DIR)]
  vm.RemoteCommand(' && '.join(cmds))

  context = _GetContextForMySQL(vm)
  local_path = data.ResourcePath("intel_hammerdb/mysql/mysqld_rhel.cnf.j2")
  remote_path = posixpath.join('{0}'.format(vm_util.VM_TMP_DIR),
                               os.path.splitext(os.path.basename("intel_hammerdb"
                                                                 "/mysqld_rhel.cnf.j2"))[0])
  vm.RenderTemplate(local_path, remote_path, context=context)
  vm.RemoteCommand("sudo cp {0}/mysqld_rhel.cnf {1}".format(vm_util.VM_TMP_DIR, MYSQL_CNF))

  _ClearCache(vm)

  _SetMySQLKernelParams(vm)
  if FLAGS.intel_hammerdb_tpcc_mysql_hugepages == 'on':
    innodb_buf_pool_size_B = _SetMySQLHugePages(vm)
    vm.RemoteCommand('echo -e "\nlarge-pages" | sudo tee -a {0}'.format(MYSQL_CNF))
    vm.RemoteCommand('sudo sed -i "/innodb_buffer_pool_size*/c\innodb_buffer_pool_size={0}"'
                     ' {1}'.format(innodb_buf_pool_size_B, MYSQL_CNF))

  vm.RobustRemoteCommand('sudo systemctl start mysqld')


def _BuildSchema(hammer_vm):
  if FLAGS.intel_hammerdb_db_type == 'pg':

    BUILD_LOG = 'build_pgdb.log'
    # building the database
    logging.info("Running Build Schema . . .")
    # build hammerdb
    hammer_vm.RemoteCommand("export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/pgsql/lib &&"
                            "cd {0} && ./hammerdbcli auto build_pgdb.tcl >> {1}"
                            .format(HAMMERDB_HOME, BUILD_LOG))
    cmds = ['cd {0} '.format(HAMMERDB_HOME),
            'sed -i "s,\x1B\[[0-9;]*[a-zA-Z],,g" {0}'.format(BUILD_LOG),
            'sed -i "s,\r,,g" {0}'.format(BUILD_LOG)]

    hammer_vm.RemoteCommand(' && '.join(cmds))
  elif FLAGS.intel_hammerdb_db_type == 'mysql':
    BUILD_LOG = 'build_mysql.log'
    # building the database
    logging.info("Running Build Schema . . .")
    # build hammerdb
    hammer_vm.RemoteCommand("cd {0} && ./hammerdbcli auto build_mysql.tcl >> {1}"
                            .format(HAMMERDB_HOME, BUILD_LOG))
    cmds = ['cd {0} '.format(HAMMERDB_HOME),
            'sed -i "s,\x1B\[[0-9;]*[a-zA-Z],,g" {0}'.format(BUILD_LOG),
            'sed -i "s,\r,,g" {0}'.format(BUILD_LOG)]

    hammer_vm.RemoteCommand(' && '.join(cmds))
  else:
    raise Exception("Incorrect choice of database !!! ")
  # copy build logs to local run directory
  cmd = ['sudo mkdir -p -m 0755 /opt/pkb/build_logs/',
         'sudo cp -ar {0}/*.log /opt/pkb/build_logs/'. format(HAMMERDB_HOME),
         'sudo chmod 0644 /opt/pkb/build_logs/*']
  s = " && "
  hammer_vm.RemoteCommand(s.join(cmd))
  remote_dir = '/opt/pkb/build_logs'
  hammer_vm.PullFile(vm_util.GetTempDir(), remote_dir)


def _RunBenchmark(hammer_vm):
  if FLAGS.intel_hammerdb_db_type == 'pg':
    RUN_HAMMER_LOG = 'run_hammer.log'
    # running the benchmark
    # Copy the hammer script to the hammer vm
    logging.info("Running HammerDB workload . . .")

    hammer_vm.RemoteCommand("export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/pgsql/lib &&"
                            "cd {0} && ./hammerdbcli auto run_hammer.tcl >> {1}"
                            . format(HAMMERDB_HOME, RUN_HAMMER_LOG))

    cmds = ['cd {0} '.format(HAMMERDB_HOME),
            'sed -i "s,\x1B\[[0-9;]*[a-zA-Z],,g" {0}'.format(RUN_HAMMER_LOG),
            'sed -i "s,\r,,g" {0}'.format(RUN_HAMMER_LOG)]

    hammer_vm.RemoteCommand(' && '.join(cmds))
  elif FLAGS.intel_hammerdb_db_type == 'mysql':
    RUN_HAMMER_LOG = 'run_hammer_mysql.log'
    # running the benchmark
    # Copy the hammer script to the hammer vm
    logging.info("Running HammerDB workload . . .")
    hammer_vm.RemoteCommand("cd {0} && ./hammerdbcli auto run_hammer_mysql.tcl >> {1}"
                            . format(HAMMERDB_HOME, RUN_HAMMER_LOG))

    cmds = ['cd {0} '.format(HAMMERDB_HOME),
            'sed -i "s,\x1B\[[0-9;]*[a-zA-Z],,g" {0}'.format(RUN_HAMMER_LOG),
            'sed -i "s,\r,,g" {0}'.format(RUN_HAMMER_LOG)]

    hammer_vm.RemoteCommand(' && '.join(cmds))
  else:
    raise Exception("Incorrect choice of database !!! ")

  if FLAGS.intel_hammerdb_enable_timeprofile:
      hammer_vm.RemoteCommand("cd {0} && ./hammerdbcli auto convert_hammer_log_txt.tcl"
                              .format(HAMMERDB_HOME))
  # copy run logs to local run directory
  cmd = ['sudo mkdir -p -m 0755 /opt/pkb/run_logs/',
         'sudo cp -ar {0}/*.log /opt/pkb/run_logs/'. format(HAMMERDB_HOME),
         'sudo cp -ar /tmp/hammerdb* /opt/pkb/run_logs',
         'sudo chmod 0644 /opt/pkb/run_logs/*']
  s = " && "
  hammer_vm.RemoteCommand(s.join(cmd))
  remote_dir = '/opt/pkb/run_logs'
  hammer_vm.PullFile(vm_util.GetTempDir(), remote_dir)


def _GetMetadataForMySQL(benchmark_spec, vm):
  mysql_cnf_dict = {'debian': '/etc/mysql/mysql.conf.d/mysqld.cnf', 'rhel': '/etc/my.cnf'}

  innodb_buffer_pool_size = vm.RemoteCommand("sudo grep innodb_buffer_pool_size {0} "
                                             "| awk -F'=' '{{print $2}}'"
                                             .format(mysql_cnf_dict
                                                     [vm.BASE_OS_TYPE]))[0].rstrip("\n")
  if vm.BASE_OS_TYPE == "rhel":
    innodb_buffer_pool_size = innodb_buffer_pool_size.split('\n')[0].rstrip("\n")

  innodb_buffer_pool_size = str(innodb_buffer_pool_size) + 'B'

  mysql_version = intel_hammerdb.MySQLVersion()

  benchmark_spec.software_config_metadata.update({
      'mysql_port': 3306,
      'mysql_version': mysql_version,
      'innodb_read_only': FLAGS.intel_hammerdb_tpcc_mysql_innodb_read_only,
      'innodb_undo_log_truncate': FLAGS.intel_hammerdb_tpcc_mysql_innodb_undo_log_truncate})

  benchmark_spec.tunable_parameters_metadata.update({
      'innodb_buffer_pool_size': innodb_buffer_pool_size,
      'innodb_buffer_pool_instances': FLAGS.intel_hammerdb_tpcc_mysql_innodb_buffer_pool_instances,
      'innodb_log_buffer_size': FLAGS.intel_hammerdb_tpcc_mysql_innodb_log_buffer_size,
      'innodb_doublewrite': FLAGS.intel_hammerdb_tpcc_mysql_innodb_doublewrite,
      'innodb_thread_concurrency': FLAGS.intel_hammerdb_tpcc_mysql_innodb_thread_concurrency,
      'innodb_flush_log_at_trx_commit':
      FLAGS.intel_hammerdb_tpcc_mysql_innodb_flush_log_at_trx_commit,
      'innodb_max_dirty_pages_pct': FLAGS.intel_hammerdb_tpcc_mysql_innodb_max_dirty_pages_pct,
      'innodb_max_dirty_pages_pct_lwm':
      FLAGS.intel_hammerdb_tpcc_mysql_innodb_max_dirty_pages_pct_lwm,
      'join_buffer_size': FLAGS.intel_hammerdb_tpcc_mysql_join_buffer_size,
      'sort_buffer_size': FLAGS.intel_hammerdb_tpcc_mysql_sort_buffer_size,
      'innodb_use_native_aio': FLAGS.intel_hammerdb_tpcc_mysql_innodb_use_native_aio,
      'innodb_stats_persistent': FLAGS.intel_hammerdb_tpcc_mysql_innodb_stats_persistent,
      'innodb_spin_wait_delay': FLAGS.intel_hammerdb_tpcc_mysql_innodb_spin_wait_delay,
      'innodb_max_purge_lag_delay': FLAGS.intel_hammerdb_tpcc_mysql_innodb_max_purge_lag_delay,
      'innodb_max_purge_lag': FLAGS.intel_hammerdb_tpcc_mysql_innodb_max_purge_lag,
      'innodb_flush_method': FLAGS.intel_hammerdb_tpcc_mysql_innodb_flush_method,
      'innodb_checksum_algorithm': FLAGS.intel_hammerdb_tpcc_mysql_innodb_checksum_algorithm,
      'innodb_io_capacity': FLAGS.intel_hammerdb_tpcc_mysql_innodb_io_capacity,
      'innodb_io_capacity_max': FLAGS.intel_hammerdb_tpcc_mysql_innodb_io_capacity_max,
      'innodb_lru_scan_depth': FLAGS.intel_hammerdb_tpcc_mysql_innodb_lru_scan_depth,
      'innodb_change_buffering': FLAGS.intel_hammerdb_tpcc_mysql_innodb_change_buffering,
      'innodb_page_cleaners': FLAGS.intel_hammerdb_tpcc_mysql_innodb_page_cleaners,
      'innodb_adaptive_flushing': FLAGS.intel_hammerdb_tpcc_mysql_innodb_adaptive_flushing,
      'innodb_flush_neighbors': FLAGS.intel_hammerdb_tpcc_mysql_innodb_flush_neighbors,
      'innodb_read_io_threads': FLAGS.intel_hammerdb_tpcc_mysql_innodb_read_io_threads,
      'innodb_write_io_threads': FLAGS.intel_hammerdb_tpcc_mysql_innodb_write_io_threads,
      'innodb_purge_threads': FLAGS.intel_hammerdb_tpcc_mysql_innodb_purge_threads,
      'innodb_adaptive_hash_index': FLAGS.intel_hammerdb_tpcc_mysql_innodb_adaptive_hash_index,
      'tpcc_mysql_num_warehouses': _GetNumWarehouses(vm)})


def _GenerateMetadataFromFlags(benchmark_spec):
  vm_dict = benchmark_spec.vm_groups
  db_vm = _GetDBVm(benchmark_spec)
  hammer_vm = _GetHammerVm(benchmark_spec)

  benchmark_spec.software_config_metadata = {
      'db_type': FLAGS.intel_hammerdb_db_type,
      'benchmark_type': FLAGS.intel_hammerdb_benchmark_type,
      'num_server_nodes': len(vm_dict[DB]),
      'num_client_nodes': len(vm_dict[HAMMER]),
      'hammerdb_version': 'HammerDB-v' + FLAGS.intel_hammerdb_version}

  benchmark_spec.tunable_parameters_metadata = {
      'intel_hammerdb_tpcc_threads_build_schema':
      _GetDBThreadsForBuildSchema(hammer_vm),
      'tpcc_hammer_num_virtual_users':
      str(_GetHammerNumUsers(db_vm)) + " VirtualUsers"}

  if FLAGS.intel_hammerdb_db_type == 'pg':
    shared_buffers = FLAGS.intel_hammerdb_tpcc_postgres_shared_buffers
    if "intel_hammerdb_tpcc_postgres_shared_buffers" not in flag_util.GetProvidedCommandLineFlags():
      shared_buffers = _GetSharedBuffers(db_vm)

    postgres_version = 'Postgres'
    postgres_version = postgres_version + intel_hammerdb.PostgresVersion()

    benchmark_spec.software_config_metadata.update({
        'port': FLAGS.intel_hammerdb_port,
        'postgres_version': postgres_version,
        'tpcc_postgres_log_timezone': FLAGS.intel_hammerdb_tpcc_postgres_log_timezone,
        'tpcc_postgres_timezone': FLAGS.intel_hammerdb_tpcc_postgres_timezone})

    benchmark_spec.tunable_parameters_metadata.update({
        'tpcc_postgres_num_warehouse': _GetNumWarehouses(db_vm),
        'tpcc_postgres_rampup': FLAGS.intel_hammerdb_tpcc_rampup,
        'tpcc_postgres_runtime': FLAGS.intel_hammerdb_tpcc_runtime,
        'tpcc_postgres_allwarehouse': FLAGS.intel_hammerdb_tpcc_postgres_allwarehouse,
        'tpcc_postgres_max_connections':
        FLAGS.intel_hammerdb_tpcc_postgres_max_connections,
        'tpcc_postgres_shared_buffers': shared_buffers,
        'tpcc_postgres_hugepages': FLAGS.intel_hammerdb_tpcc_postgres_hugepages,
        'tpcc_postgres_temp_buffers': FLAGS.intel_hammerdb_tpcc_postgres_temp_buffers,
        'tpcc_postgres_work_mem': FLAGS.intel_hammerdb_tpcc_postgres_work_mem,
        'tpcc_postgres_maintenance_work_mem':
        FLAGS.intel_hammerdb_tpcc_postgres_maintenance_work_mem,
        'tpcc_postgres_autovacuum_work_mem':
        FLAGS.intel_hammerdb_tpcc_postgres_autovacuum_work_mem,
        'tpcc_postgres_max_stack_depth': FLAGS.intel_hammerdb_tpcc_postgres_max_stack_depth,
        'tpcc_postgres_dynamic_shared_memory_type':
        FLAGS.intel_hammerdb_tpcc_postgres_dynamic_shared_memory_type,
        'tpcc_postgres_max_files_per_process':
        FLAGS.intel_hammerdb_tpcc_postgres_max_files_per_process,
        'tpcc_postgres_io_concur': FLAGS.intel_hammerdb_tpcc_postgres_io_concur,
        'tpcc_postgres_max_worker_process': db_vm.num_cpus,
        'tpcc_postgres_wal_level': FLAGS.intel_hammerdb_tpcc_postgres_wal_level,
        'tpcc_postgres_syn_commit': FLAGS.intel_hammerdb_tpcc_postgres_syn_commit,
        'tpcc_postgres_wal_buffers': FLAGS.intel_hammerdb_tpcc_postgres_wal_buffers,
        'tpcc_postgres_max_wal_senders':
        FLAGS.intel_hammerdb_tpcc_postgres_max_wal_senders,
        'tpcc_postgres_max_locks_per_transaction':
        FLAGS.intel_hammerdb_tpcc_postgres_max_locks_per_transaction,
        'tpcc_postgres_max_pred_locks_per_transaction':
        FLAGS.intel_hammerdb_tpcc_postgres_max_pred_locks_per_transaction,
        'tpcc_postgres_min_wal_size': FLAGS.intel_hammerdb_tpcc_postgres_min_wal_size,
        'tpcc_postgres_max_wal_size': FLAGS.intel_hammerdb_tpcc_postgres_max_wal_size,
        'tpcc_postgres_checkpoint_completion_target':
        FLAGS.intel_hammerdb_tpcc_postgres_checkpoint_completion_target,
        'tpcc_postgres_checkpoint_warning': FLAGS.intel_hammerdb_tpcc_postgres_checkpoint_warning,
        'tpcc_postgres_random_page_cost': FLAGS.intel_hammerdb_tpcc_postgres_random_page_cost,
        'tpcc_postgres_cpu_tuple_cost': FLAGS.intel_hammerdb_tpcc_postgres_cpu_tuple_cost,
        'tpcc_postgres_effective_cache_size':
        FLAGS.intel_hammerdb_tpcc_postgres_effective_cache_size,
        'tpcc_postgres_autovacuum': FLAGS.intel_hammerdb_tpcc_postgres_autovacuum,
        'tpcc_postgres_autovacuum_max_workers':
        FLAGS.intel_hammerdb_tpcc_postgres_autovacuum_max_workers,
        'tpcc_postgres_autovacuum_freeze_max_age':
        FLAGS.intel_hammerdb_tpcc_postgres_autovacuum_freeze_max_age,
        'tpcc_postgres_autovacuum_vacuum_cost_limit':
        FLAGS.intel_hammerdb_tpcc_postgres_autovacuum_vacuum_cost_limit,
        'tpcc_postgres_vacuum_freeze_min_age':
        FLAGS.intel_hammerdb_tpcc_postgres_vacuum_freeze_min_age})

  elif FLAGS.intel_hammerdb_db_type == 'mysql':
    _GetMetadataForMySQL(benchmark_spec, db_vm)


def _GetHammerVm(benchmark_spec):
  if FLAGS.intel_hammerdb_run_single_node:
    hammer_vm = benchmark_spec.vm_groups[DB][0]
  else:
    hammer_vm = benchmark_spec.vm_groups[HAMMER][0]
  return hammer_vm


def _GetDBVm(benchmark_spec):
  db_vm = benchmark_spec.vm_groups[DB][0]
  return db_vm


def _GetPGResults(db_vm):
   # copying back config files from database:
  PGDB_MNT_DIR = db_vm.GetScratchDir()

  remote_dir = '/opt/pkb/confs/'
  cmds = ["mkdir -p {0}". format(remote_dir),
          "sudo cp -ar {0}/data/pg_hba.conf {1}". format(PGDB_MNT_DIR, remote_dir),
          "sudo cp -ar {0}/data/postgresql.conf {1}" . format(PGDB_MNT_DIR, remote_dir),
          "sudo chmod 644 {0}*". format(remote_dir)]

  db_vm.RemoteCommand(" && ".join(cmds))
  db_vm.PullFile(vm_util.GetTempDir(), remote_dir)


def _CollectPGResults(db_vm, hammer_vm):
  """Collect and parse test results.

  Args:
    benchmark_spec: The benchmark specification. Contains all data
        that is required to run the benchmark.
    metadata: dict. Contains metadata for this benchmark.
  """
  logging.info('Gathering results and configurations')
  _GetPGResults(db_vm)
  # parsing result file
  filename = '/opt/pkb/run_logs/run_hammer.log'
  resp, _ = hammer_vm.RemoteCommand('cat {0} | grep TPM'.format(filename))
  numUsersRes, _ = hammer_vm.RemoteCommand('cat {0} | grep "Active Virtual Users"'
                                           .format(filename))
  results = []
  postgresqlTPM = 'PostgreSQL TPM'
  nopm = 'NOPM'
  postgresqlTPMValues = []
  nopmValues = []
  virtualUsers = []
  allResults = ''
  for line1, line2 in zip(resp.splitlines(), numUsersRes.splitlines()):
    if FLAGS.intel_hammerdb_version == '4.0':
      found1 = re.search(r"(\d+) {0} \w+ (\d+)".format(nopm), line1)
      postgresqlTPMValues.append(int(found1.group(2)))
      nopmValues.append(int(found1.group(1)))
      found2 = re.search(r"\d:(\d+)", line2)
      virtualUsers.append(found2.group(1))
      logging.info("No of Virtual Users: {0}, PostgreSQL TPM: {1}, NOPM: {2}"
                   .format(found2.group(1), found1.group(2), found1.group(1)))
      allResults += ("No of Virtual Users: {0}, PostgreSQL TPM: {1}, NOPM: {2} <br>"
                     .format(found2.group(1), found1.group(2), found1.group(1)))
    else:
      found1 = re.search(r"(\d+) {0} \w+ (\d+)".format(postgresqlTPM), line1)
      postgresqlTPMValues.append(int(found1.group(1)))
      nopmValues.append(int(found1.group(2)))
      found2 = re.search(r"\d:(\d+)", line2)
      virtualUsers.append(found2.group(1))
      logging.info("No of Virtual Users: {0}, PostgreSQL TPM: {1}, NOPM: {2}"
                   .format(found2.group(1), found1.group(1), found1.group(2)))
      allResults += ("No of Virtual Users: {0}, PostgreSQL TPM: {1}, NOPM: {2} <br>"
                     .format(found2.group(1), found1.group(1), found1.group(2)))

  maxPostgresqlTPM = max(postgresqlTPMValues)
  indexOfMaxValue = postgresqlTPMValues.index(maxPostgresqlTPM)

  results.append(sample.Sample("Num of Virtual Users with Peak Value",
                               str(virtualUsers[indexOfMaxValue]), "",
                               {'List of all results': allResults}))
  results.append(sample.Sample(postgresqlTPM, str(postgresqlTPMValues[indexOfMaxValue]),
                               "Transactions/Minute", {}))
  results.append(sample.Sample(nopm, str(nopmValues[indexOfMaxValue]), "New Orders Per Minute",
                               {'primary_sample': True}))

  return results


def _GetMySQLResults(db_vm):
  # copying back config files from database:
  if FLAGS.intel_hammerdb_platform == 'ARM':
    if db_vm.BASE_OS_TYPE == "debian":
      MYSQL_CONF_DIR = "/etc/my.cnf"
  else:
    if db_vm.BASE_OS_TYPE == "debian":
      MYSQL_CONF_DIR = "/etc/mysql/mysql.conf.d/mysqld.cnf"
    elif db_vm.BASE_OS_TYPE == "rhel":
      MYSQL_CONF_DIR = "/etc/my.cnf"

  remote_dir = '/opt/pkb/confs/'
  cmds = ["mkdir -p {0}". format(remote_dir),
          "sudo cp {0} {1}" . format(MYSQL_CONF_DIR, remote_dir),
          "sudo chmod 644 {0}*". format(remote_dir)]
  # Add the configuraiton file to be copied from VM for this

  db_vm.RemoteCommand(" && ".join(cmds))
  db_vm.PullFile(vm_util.GetTempDir(), remote_dir)


def _CollectMYSQLResults(db_vm, hammer_vm):
  """Collect and parse test results.

  Args:
    benchmark_spec: The benchmark specification. Contains all data
        that is required to run the benchmark.
    metadata: dict. Contains metadata for this benchmark.
  """
  logging.info('Gathering results and configurations')
  _GetMySQLResults(db_vm)
  # parsing result file
  filename = '/opt/pkb/run_logs/run_hammer_mysql.log'
  resp, _ = hammer_vm.RemoteCommand('cat {0} | grep TPM'.format(filename))
  numUsersRes, _ = hammer_vm.RemoteCommand('cat {0} | grep "Active Virtual Users"'
                                           .format(filename))
  results = []

  mysqlTPM = 'MySQL TPM'
  nopm = 'NOPM'
  mysqlTPMValues = []
  nopmValues = []
  virtualUsers = []
  allResults = ''
  for line1, line2 in zip(resp.splitlines(), numUsersRes.splitlines()):
    if FLAGS.intel_hammerdb_version == '4.0':
      found1 = re.search(r"(\d+) {0} \w+ (\d+)".format(nopm), line1)
      mysqlTPMValues.append(int(found1.group(2)))
      nopmValues.append(int(found1.group(1)))
      found2 = re.search(r"\d:(\d+)", line2)
      virtualUsers.append(found2.group(1))
      logging.info("No of Virtual Users: {0}, MySQL TPM: {1}, NOPM: {2}"
                   .format(found2.group(1), found1.group(2), found1.group(1)))
      allResults += ("No of Virtual Users: {0}, MySQL TPM: {1}, NOPM: {2} <br>"
                     .format(found2.group(1), found1.group(2), found1.group(1)))
    else:
      found1 = re.search(r"(\d+) {0} \w+ (\d+)".format(mysqlTPM), line1)
      mysqlTPMValues.append(int(found1.group(1)))
      nopmValues.append(int(found1.group(2)))
      found2 = re.search(r"\d:(\d+)", line2)
      virtualUsers.append(found2.group(1))
      logging.info("No of Virtual Users: {0}, MySQL TPM: {1}, NOPM: {2}"
                   .format(found2.group(1), found1.group(1), found1.group(2)))
      allResults += ("No of Virtual Users: {0}, MySQL TPM: {1}, NOPM: {2} <br>"
                     .format(found2.group(1), found1.group(2), found1.group(1)))

  maxMysqlTPM = max(mysqlTPMValues)
  indexOfMaxValue = mysqlTPMValues.index(maxMysqlTPM)

  results.append(sample.Sample("Num of Virtual Users with Peak Value",
                               str(virtualUsers[indexOfMaxValue]), "",
                               {'List of all results': allResults}))
  results.append(sample.Sample(mysqlTPM, str(mysqlTPMValues[indexOfMaxValue]),
                               "Transactions/Minute", {}))
  results.append(sample.Sample(nopm, str(nopmValues[indexOfMaxValue]), "New Orders Per Minute",
                               {'primary_sample': True}))
  return results


def Prepare(benchmark_spec):
  benchmark_spec.workload_name = "Intel HammerDB V{0} Postgres".format(FLAGS.intel_hammerdb_version)
  if FLAGS.intel_hammerdb_db_type == 'mysql':
    benchmark_spec.workload_name = "Intel HammerDB V{0} MySQL".format(FLAGS.intel_hammerdb_version)

  benchmark_spec.sut_vm_group = "workers"
  benchmark_spec.always_call_cleanup = True

  db_vm = _GetDBVm(benchmark_spec)
  logging.info(benchmark_spec.vm_groups[DB])
  logging.info(db_vm)

  hammer_vm = _GetHammerVm(benchmark_spec)

  if FLAGS.intel_hammerdb_platform == 'ARM':
    if FLAGS.intel_hammerdb_db_type == 'pg':
      db_vm.Install('intel_hammerdb')
      hammer_vm.Install('intel_hammerdb')
      _ConfigureClientForPGDataSet(db_vm, hammer_vm)
      _ConfigurePGDatabase(db_vm)
    else:
      if db_vm.BASE_OS_TYPE == "debian":
        intel_hammerdb.InstallMySQLOnArmUbuntu(db_vm)
        _ConfigureMYSQLDebDatabaseForARM(db_vm)
      hammer_vm.Install('intel_hammerdb')
      _ConfigureClientForMYSQLDataSet(db_vm, hammer_vm)
  else:
    if FLAGS.intel_hammerdb_run_single_node:
      db_vm.Install('intel_hammerdb')
    else:
      logging.info(benchmark_spec.vm_groups[HAMMER])
      logging.info(hammer_vm)
      # installing dependencies.
      db_vm.Install('intel_hammerdb')
      hammer_vm.Install('intel_hammerdb')

    # configuring client and db, building the database
    if FLAGS.intel_hammerdb_db_type == 'pg':
      _ConfigureClientForPGDataSet(db_vm, hammer_vm)
      _ConfigurePGDatabase(db_vm)
    elif FLAGS.intel_hammerdb_db_type == 'mysql':
      _ConfigureClientForMYSQLDataSet(db_vm, hammer_vm)
      if db_vm.BASE_OS_TYPE == "debian":
        _ConfigureMYSQLDebDatabase(db_vm)
      elif db_vm.BASE_OS_TYPE == "rhel":
        _ConfigureMYSQLRhelDatabase(db_vm)
      else:
        raise Exception("{0} OS type not supported.".format(db_vm.BASE_OS_TYPE))

  _BuildSchema(hammer_vm)


def Run(benchmark_spec):
  db_vm = _GetDBVm(benchmark_spec)
  hammer_vm = _GetHammerVm(benchmark_spec)
  _ConfigureClientForHammerRun(db_vm, hammer_vm)
  _RunBenchmark(hammer_vm)
  _GenerateMetadataFromFlags(benchmark_spec)

  if FLAGS.intel_hammerdb_db_type == 'pg':
    return _CollectPGResults(db_vm, hammer_vm)
  elif FLAGS.intel_hammerdb_db_type == 'mysql':
    return _CollectMYSQLResults(db_vm, hammer_vm)


def _CleanupPG(vm):
  # Restore the original hugepages setting
  if (FLAGS.intel_hammerdb_tpcc_postgres_hugepages == "on" or
      FLAGS.intel_hammerdb_tpcc_postgres_hugepages == "try"):
    original_hugepages = vm.RemoteCommand("cat {0}".format(HUGEPAGES_TMP_FILE))[0].rstrip("\n")
    vm.RemoteCommand("sudo sysctl -w vm.nr_hugepages={0}".format(original_hugepages,
                                                                 ignore_failure=True))
    vm.RemoteCommand("rm {0}".format(HUGEPAGES_TMP_FILE))

  vm.RemoteCommand("sudo mv /etc/hammerdb_sysctl_tmp.conf /etc/sysctl.conf")
  vm.RemoteCommand('sudo rm -rf /opt/pkb/confs', ignore_failure=True)
  PGDB_MNT_DIR = vm.GetScratchDir()
  vm.RemoteCommand('sudo rm -rf {0}/data'. format(PGDB_MNT_DIR))
  if vm.BASE_OS_TYPE == "rhel":
    _, _, retcode = vm.RemoteCommandWithReturnCode('file -f {0}'.format(FIREWALL_CHECK_FILE),
                                                   ignore_failure=True, suppress_warning=True)
    if retcode == 0:
      vm.RemoteCommand('sudo systemctl start firewalld')
      vm.RemoteCommand('rm {0}'.format(FIREWALL_CHECK_FILE))
  vm.RemoteCommand("sudo sed -i 's/^postgres.*//g' /etc/security/limits.conf")


def _CleanupMySQL(vm):
  MYSQL_MNT_DIR = vm.GetScratchDir()
  if FLAGS.intel_hammerdb_tpcc_mysql_hugepages == 'on':
    original_hugepages = vm.RemoteCommand("cat {0}".format(HUGEPAGES_TMP_FILE))[0].rstrip("\n")
    vm.RemoteCommand("sudo sysctl -w vm.nr_hugepages={0}".format(original_hugepages,
                                                                 ignore_failure=True))
    vm.RemoteCommand("rm {0}".format(HUGEPAGES_TMP_FILE))

  if FLAGS.intel_hammerdb_platform == 'ARM':
    if vm.BASE_OS_TYPE == "debian":
      vm.RemoteCommand('sudo rm -r {0}/mysql*'.format(MYSQL_MNT_DIR))
      vm.RemoteCommand('sudo rm -r /etc/init.d/mysqld')
      vm.RemoteCommand('sudo rm -r /usr/local/mysql')
  else:
    if vm.BASE_OS_TYPE == "debian":
      vm.RobustRemoteCommand('sudo systemctl stop mysql')
      cmds = ['sudo rm -r {0}/mysql'.format(MYSQL_MNT_DIR),
              'sudo rm -rf /var/lib/mysql.bak']
      vm.RemoteCommand(' && '.join(cmds))
    elif vm.BASE_OS_TYPE == "rhel":
      cmds = ['sudo rm -f /var/log/mysqld.log',
              'sudo rm -rf {0}/data'.format(MYSQL_MNT_DIR)]
      vm.RemoteCommand(' && '.join(cmds))
  if FLAGS.intel_hammerdb_tpcc_mysql_hugepages == 'on':
    vm.RemoteCommand("sudo mv /etc/hammerdb_sysctl_tmp.conf /etc/sysctl.conf")
  vm.RemoteCommand("sudo sed -i 's/^mysql.*//g' /etc/security/limits.conf")


def Cleanup(benchmark_spec):
  db_vm = _GetDBVm(benchmark_spec)
  hammer_vm = _GetHammerVm(benchmark_spec)
  if FLAGS.intel_hammerdb_db_type == 'pg':
    _CleanupPG(db_vm)
  elif FLAGS.intel_hammerdb_db_type == 'mysql':
    _CleanupMySQL(db_vm)
  hammer_vm.RemoteCommand('cd /tmp && rm hammerdb*', ignore_failure=True)
