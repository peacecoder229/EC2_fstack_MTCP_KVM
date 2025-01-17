# Copyright 2018 PerfKitBenchmarker Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Contains classes/functions related to EKS (Elastic Kubernetes Service).

This requires that the eksServiceRole IAM role has already been created and
requires that the aws-iam-authenticator binary has been installed.
See https://docs.aws.amazon.com/eks/latest/userguide/getting-started.html for
instructions.
"""

import json
import logging
import re

from absl import flags
from perfkitbenchmarker import container_service
from perfkitbenchmarker import errors
from perfkitbenchmarker import vm_util
from perfkitbenchmarker.providers import aws
from perfkitbenchmarker.providers.aws import aws_virtual_machine
from perfkitbenchmarker.providers.aws import util

FLAGS = flags.FLAGS


class EksCluster(container_service.KubernetesCluster):
  """Class representing an Elastic Kubernetes Service cluster."""

  CLOUD = aws.CLOUD

  def __init__(self, spec):
    super(EksCluster, self).__init__(spec)
    # EKS requires a region and optionally a list of zones.
    # Interpret the zone as a comma separated list of zones or a region.
    self.zones = sorted(FLAGS.eks_zones) or (self.zone and self.zone.split(','))
    if not self.zones:
      raise errors.Config.MissingOption(
          'container_cluster.vm_spec.AWS.zone is required.')
    elif len(self.zones) > 1:
      self.region = util.GetRegionFromZone(self.zones[0])
      self.zone = ','.join(self.zones)
    elif util.IsRegion(self.zones[0]):
      self.region = self.zone = self.zones[0]
      self.zones = []
      logging.info("Interpreting zone '%s' as a region", self.zone)
    else:
      raise errors.Config.InvalidValue(
          'container_cluster.vm_spec.AWS.zone must either be a comma separated '
          'list of zones or a region.')
    self.cluster_version = FLAGS.container_cluster_version
    # TODO(user) support setting boot disk type if EKS does.
    self.boot_disk_type = self.vm_config.DEFAULT_ROOT_DISK_TYPE
    self.node_group_name = 'eks'
    self.ssh_access = FLAGS.aws_eks_ssh_access

  def GetResourceMetadata(self):
    """Returns a dict containing metadata about the cluster.

    Returns:
      dict mapping string property key to value.
    """
    result = super(EksCluster, self).GetResourceMetadata()
    result['container_cluster_version'] = self.cluster_version
    result['boot_disk_type'] = self.boot_disk_type
    result['boot_disk_size'] = self.vm_config.boot_disk_size
    return result

  def _CreateDependencies(self):
    """Set up the ssh key."""
    aws_virtual_machine.AwsKeyFileManager.ImportKeyfile(self.region)

  def _DeleteDependencies(self):
    """Delete the ssh key."""
    aws_virtual_machine.AwsKeyFileManager.DeleteKeyfile(self.region)

  def _Create(self):
    """Creates the control plane and worker nodes."""
    tags = util.MakeDefaultTags()
    eksctl_flags = {
        'kubeconfig': FLAGS.kubeconfig,
        'managed': True,
        'name': self.name,
        'nodegroup-name': self.node_group_name,
        'nodes': self.num_nodes,
        'nodes-min': self.min_nodes,
        'nodes-max': self.max_nodes,
        'node-type': self.vm_config.machine_type,
        'node-volume-size': self.vm_config.boot_disk_size,
        'region': self.region,
        'tags': ','.join('{}={}'.format(k, v) for k, v in tags.items()),
        'ssh-access': self.ssh_access,
        'ssh-public-key':
            aws_virtual_machine.AwsKeyFileManager.GetKeyNameForRun(),
        'version': self.cluster_version,
        # NAT mode uses an EIP.
        'vpc-nat-mode': 'Disable',
        'zones': ','.join(self.zones),
    }
    cmd = [FLAGS.eksctl, 'create', 'cluster'] + sorted(
        '--{}={}'.format(k, v) for k, v in eksctl_flags.items() if v)
    vm_util.IssueCommand(cmd, timeout=1800)

  def _Delete(self):
    """Deletes the control plane and worker nodes."""
    cmd = [FLAGS.eksctl, 'delete', 'cluster',
           '--name', self.name,
           '--region', self.region]
    vm_util.IssueCommand(cmd, timeout=1800)

  def _IsReady(self):
    """Returns True if the workers are ready, else False."""
    get_cmd = [
        FLAGS.kubectl, '--kubeconfig', FLAGS.kubeconfig,
        'get', 'nodes',
    ]
    stdout, _, _ = vm_util.IssueCommand(get_cmd)
    ready_nodes = len(re.findall('Ready', stdout))
    return ready_nodes >= self.min_nodes

  def _PostCreate(self):
    """Adds CIDR IP range of ingress SSH security group rules."""
    if self.ssh_access:
      group_name = 'eksctl-{}-nodegroup-{}-remoteAccess'.format(self.name, self.node_group_name)
      cmd = aws.util.AWS_PREFIX + ['ec2', 'describe-security-groups', '--filters',
                                   'Name=group-name,Values={}'.format(group_name),
                                   '--query', 'SecurityGroups[*].{ID:GroupId}',
                                   '--region', self.region]
      raw_output, stderror, retcode = vm_util.IssueCommand(cmd)
      if retcode != 0:
        logging.warning('Failed to add CIDR IP range of ingress SSH security group rules! %s', stderror)
        return

      json_output = json.loads(raw_output)
      if len(json_output) != 1:
        logging.warning("Failed to add CIDR IP range of ingress SSH security group rules! "
                        "Couldn't find {} security group!".format(group_name))
        return

      if not ('ID' in json_output[0]):
        logging.warning("Failed to add CIDR IP range of ingress SSH security group rules! "
                        "Missing security group id!")
      group_id = json_output[0]['ID']

      proxy_server_ip_list_path = FLAGS.proxy_server_ip_list

      CIDRs = util.ReadCIDRList(proxy_server_ip_list_path)
      if len(CIDRs) == 0:
        logging.warning('Failed to add CIDR IP range of ingress SSH security group rules! No rules in "{}"!',
                        proxy_server_ip_list_path)

      for cidr in CIDRs:
        cmd = aws.util.AWS_PREFIX + ['ec2', 'authorize-security-group-ingress',
                                     '--group-id', group_id, '--protocol', 'tcp',
                                     '--port', '22', '--cidr', cidr, '--region', self.region]

        _, stderror, retcode = vm_util.IssueCommand(cmd)
        if retcode != 0:
          logging.warning('Failed to add %q CIDR IP range of ingress SSH security group rule! %s', cidr, stderror)
          return
