import operator


def MeetsExitCriteria(scores, best=max, op=operator.gt):
  """ Does list of scores meet exit criteria (i.e. last two scores not
      as good as the best)?
  Arguments:
    scores: the list of scores accumulated
    best: the function that determines the best score in the list
    op: the operator used to compare the last two scores to the best
  Returns:
    True, if meets exit criteria
    False, if does not meet exit criteria
  """
  if len(scores) < 3:
    return False
  best_score = best(scores)
  return op(best_score, scores[-1]) and op(best_score, scores[-2])


def GetInternalIpAddresses(vm):
  """ Get list of all internal IP addresses defined on VM
  Arguments:
    vm: virtual machine object to get IP addresses from
  Returns:
    list of strings containing ip addresses
  """
  addrs = vm.additional_private_ip_addresses[:]
  addrs.append(vm.internal_ip)
  return addrs
