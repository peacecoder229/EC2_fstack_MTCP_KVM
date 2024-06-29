**MITM Cache Usage Manual**

**Usage Model (Please Read)**

Project Cumulus will begin releasing signed cache files for usage in the future, requiring users to provide a local APT or YUM repo for their respective target SUTs. Their SUTs should be configured to pull packages from this local repo. The recording feature is intended to be a tool for Project Cumulus to automate the creation of official cache files. However, it will function to create custom cache files for offline use that will not be supported by Project Cumulus. This should also work in the absence of a separate APT or YUM repo because the entire session is recorded, and this may be an acceptable solution for some users.  

The following are flags that may be passed to pkb.py. 

| Flag Name | Type | Default | Notes |
| ------ | ------ | ------ | ------ |
|--use_offline	|boolean	|False	|Enable or disable mitm, required to enable options below|
|--offline_executable	|string	|/usr/bin/mitmproxy	|Use a custom mitmproxy executable|
|--offline_upstream_proxy	|string	|http://proxy-chain.intel.com:912	|Specify the proxy this proxy will use for internet access|
|--offline_listen_host	|string	|0.0.0.0	|IP Address for mitmproxy to bind on|
|--offline_listen_port	|integer	|8920	|Port for mitmproxy to listen on|
|--offline_replay_stream	|string	|''     |File to replay session stream from|
|--offline_record_stream	|string	|''	|File to record session stream to|
|--offline_log	|string	|<PKB run dir>/mitmproxy.log	|File to use for mitmproxy stdout (will overwrite)|
|--offline_error_log	|string	|<PKB run dir>/mitmproxy-error.log	|File to use for mitmproxy stderr (will overwrite)|

**Examples**

**Use mitmproxy with upstream proxy for inspecting PKB traffic**

        #Bind mitmproxy to default port 8920, and use the default upstream Intel proxy
        ./pkb.py --use_offline=True --offline_listen_host=192.168.0.1 --benchmarks=fio_static --benchmark_config_file=fio_static.yaml --os_type=debian --owner=mswynne

**Record a PKB Session**

        #Bind mitmproxy to default port 8920, and use the default upstream Intel proxy
        ./pkb.py --use_offline=True --offline_listen_host=192.168.0.1 --offline_record_stream=myFioSession.mitm --benchmarks=fio_static --benchmark_config_file=fio_static.yaml --os_type=debian --owner=mswynne

**Replay a PKB Session**

        #Bind mitmproxy to default port 8920
        ./pkb.py --use_offline=True --offline_listen_host=192.168.0.1 --offline_replay_stream=myFioSession.mitm --benchmarks=fio_static --benchmark_config_file=fio_static.yaml --os_type=debian --owner=mswynne

