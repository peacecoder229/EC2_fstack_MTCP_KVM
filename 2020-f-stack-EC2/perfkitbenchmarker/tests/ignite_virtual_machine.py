
import json
import time
import warnings

from absl import flags

from perfkitbenchmarker import pkb  # this is needed to define flags
from perfkitbenchmarker import vm_util
from perfkitbenchmarker import static_virtual_machine

FLAGS = flags.FLAGS
FLAGS.mark_as_parsed()


class IgniteVirtualMachine(static_virtual_machine.StaticVirtualMachine):
  def __init__(self, name, image, cores=1, memory=1):
    self.vm_provisioned = False
    if not self.IsIgniteInstalled():
      raise Exception("Ignite is not installed")
    warnings.simplefilter("ignore", category=ResourceWarning)
    vm_util.SSHKeyGen()
    self.private_key_path = vm_util.GetPrivateKeyPath()
    self.public_key_path = vm_util.GetPublicKeyPath()
    self.vm_name = name
    ignite_cmd = 'sudo ignite run {image} --cpus {cores} --memory {memory}GB ' \
                 '--ssh={public_key} --name {name}'.format(image=image, cores=cores, memory=memory,
                                                           public_key=self.public_key_path, name=self.vm_name)
    _, _, ret = vm_util.IssueCommand(ignite_cmd.split(' '), raise_on_failure=True)
    if ret == 0:
      self.vm_provisioned = True
    vm_info_cmd = 'sudo ignite inspect vm {name}'.format(name=self.vm_name)
    stdout, stderr, ret = vm_util.IssueCommand(vm_info_cmd.split(' '), raise_on_failure=True)

    # Provisioning takes a few seconds before ssh is ready
    time.sleep(5)
    self.vm_info = json.loads(stdout)
    self.ip_address = self.vm_info['status']['ipAddresses'][0]
    self.host_name = self.vm_info['metadata']['uid']
    self.user_name = 'root'

    vm_spec = static_virtual_machine.StaticVmSpec('test_static_vm_spec',
                                                  ssh_private_key=self.GetPrivateKeyPath(),
                                                  ip_address=self.GetIpAddress(),
                                                  user_name=self.GetUserName())

    super(IgniteVirtualMachine, self).__init__(vm_spec)
    # resolves ignite sudo issues
    self.RemoteCommand("echo '127.0.0.1 localhost.localdomain localhost' > /etc/hosts")
    self.RemoteCommand("echo '{} {}' >> /etc/hosts".format(self.GetIpAddress(), self.GetHostName()))

    # Disable IPv6 (causing some issues with commands)
    self.RemoteCommand("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
    self.RemoteCommand("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
    self.RemoteCommand("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")

    # Configure the proxy
    self.RemoteCommand("echo 'http_proxy=\"http://proxy-chain.intel.com:911\"' >> /etc/environment")
    self.RemoteCommand("echo 'https_proxy=\"http://proxy-chain.intel.com:912\"' >> /etc/environment")

    # Configure the git and Mercurial proxies
    self.RemoteCommand("echo '[http]\n    proxy = http://proxy-chain.intel.com:911' >> ~/.gitconfig")
    self.RemoteCommand("echo '[http_proxy]\nhost = http://proxy-chain.intel.com:911' >> ~/.hgrc")


  def teardown(self):
    if self.vm_provisioned:
      ignite_cmd = 'sudo ignite rm -f {name}'.format(name=self.vm_name)
      vm_util.IssueCommand(ignite_cmd.split(' '), raise_on_failure=True)

  @staticmethod
  def IsIgniteInstalled():
    stdout, stderr, ret = vm_util.IssueCommand(['which', 'ignite'], raise_on_failure=False)
    return False if not stdout else True

  def GetID(self):
    full_id = self.vm_info["status"]["runtime"]["id"]
    return full_id.split('-')[1]

  def GetIpAddress(self):
    return self.ip_address

  def GetHostName(self):
    return self.host_name

  def GetUserName(self):
    return self.user_name

  def GetPrivateKeyPath(self):
    return self.private_key_path


class Ubuntu2004BasedIgniteVirtualMachine(IgniteVirtualMachine, static_virtual_machine.Ubuntu2004BasedStaticVirtualMachine):
  def __init__(self, name, cores=1, memory=1):
    image = 'weaveworks/ignite-ubuntu:latest'

    super(Ubuntu2004BasedIgniteVirtualMachine, self).__init__(name, image, cores, memory)
