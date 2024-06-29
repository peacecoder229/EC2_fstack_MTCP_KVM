kata_default_runtime = """
#!/bin/bash
sudo mkdir -p /etc/systemd/system/docker.service.d/
cat <<EOF | sudo tee /etc/systemd/system/docker.service.d/kata-containers.conf
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd -D --add-runtime kata-runtime=/usr/bin/kata-runtime --default-runtime=kata-runtime
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker
"""


def YumInstall(vm):
  cmds = [
      "source /etc/os-release",
      "sudo yum -y install yum-utils",
      'sudo -E yum-config-manager --add-repo "http://download.opensuse.org/repositories/home:/katacontainers:'
      '/releases:/$(arch):/master/CentOS_${VERSION_ID}/home:katacontainers:releases:$(arch):master.repo"',
      'sudo -E yum -y install kata-runtime kata-proxy kata-shim'
  ]
  vm.RemoteCommand(" && ".join(cmds))
  _SetDefaultRuntime(vm)


def AptInstall(vm):
  cmds = [
      'echo "deb http://download.opensuse.org/repositories/home:/katacontainers:/releases:/$(arch):/master/xUbuntu_'
      '$(lsb_release -rs)/ /" | sudo tee /etc/apt/sources.list.d/kata-containers.list',
      "curl -sL http://download.opensuse.org/repositories/home:/katacontainers:/releases:/$(arch):/master/xUbuntu_"
      "$(lsb_release -rs)/Release.key | sudo apt-key add -",
      "sudo -E apt-get update",
      "sudo -E apt-get -y install kata-runtime kata-proxy kata-shim"
  ]
  vm.RemoteCommand(" && ".join(cmds))
  _SetDefaultRuntime(vm)


def SwupdInstall(vm):
  vm.RemoteCommand("sudo swupd update")
  vm.InstallPackages("containers-virt")


def _SetDefaultRuntime(vm):
  vm.RemoteCommand("echo '%s' > runtime.sh && chmod +x runtime.sh && ./runtime.sh" % kata_default_runtime)
