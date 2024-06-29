import mock
import unittest
from packaging.version import Version

from perfkitbenchmarker.linux_packages import openjdk

NO_JAVA_FOUND_OUTPUT = """
Command 'java' not found, but can be installed with:

sudo apt install openjdk-11-jre-headless  # version 11.0.10+9-0ubuntu1~20.04, or
sudo apt install default-jre              # version 2:1.11-72
sudo apt install openjdk-13-jre-headless  # version 13.0.4+8-1~20.04
sudo apt install openjdk-14-jre-headless  # version 14.0.2+12-1~20.04
sudo apt install openjdk-8-jre-headless   # version 8u282-b08-0ubuntu1~20.04"""

JAVA_VERSION_CASE_OLD_FORMAT = 8
JAVA_VERSION_OUTPUT_OLD_FORMAT = """openjdk version "1.8.0_282"
OpenJDK Runtime Environment (build 1.8.0_282-8u282-b08-0ubuntu1~16.04-b08)
OpenJDK 64-Bit Server VM (build 25.282-b08, mixed mode)
"""

JAVA_VERSION_OUTPUT_NEW_FORMAT = """openjdk version "11.0.10" 2021-01-19
OpenJDK Runtime Environment (build 11.0.10+9-Ubuntu-0ubuntu1.20.04)
OpenJDK 64-Bit Server VM (build 11.0.10+9-Ubuntu-0ubuntu1.20.04, mixed mode, sharing)
"""
JAVA_VERSION_CASE_NEW_FORMAT = 11

DUMMY_STRING = "foo"


class CheckJavaVersionTest(unittest.TestCase):

  def test_no_java(self):
    # GIVEN
    vm = mock.Mock()
    vm.RemoteCommand.return_value = (DUMMY_STRING, NO_JAVA_FOUND_OUTPUT)

    # THEN
    self.assertRaises(RuntimeError, openjdk.CheckJavaMajorVersion, vm)

  def test_java_exists_old_format(self):
    # GIVEN
    vm = mock.Mock()
    vm.RemoteCommand.return_value = (DUMMY_STRING, JAVA_VERSION_OUTPUT_OLD_FORMAT)

    # WHEN
    version = openjdk.CheckJavaMajorVersion(vm)

    # THEN
    self.assertEqual(version, JAVA_VERSION_CASE_OLD_FORMAT)

  def test_java_exists_new_format(self):
    # GIVEN
    vm = mock.Mock()
    vm.RemoteCommand.return_value = (DUMMY_STRING, JAVA_VERSION_OUTPUT_NEW_FORMAT)

    # WHEN
    version = openjdk.CheckJavaMajorVersion(vm)

    # THEN
    self.assertEqual(version, JAVA_VERSION_CASE_NEW_FORMAT)

  def test_output_not_recognized(self):
    # GIVEN
    vm = mock.Mock()
    vm.RemoteCommand.return_value = (DUMMY_STRING, DUMMY_STRING)

    # THEN
    self.assertRaises(RuntimeError, openjdk.CheckJavaMajorVersion, vm)
