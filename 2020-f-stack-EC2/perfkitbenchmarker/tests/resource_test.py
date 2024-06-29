"""Tests for perfkitbenchmarker.resource."""

import unittest

from absl import flags
from absl.testing import parameterized
import mock
from perfkitbenchmarker import errors
from perfkitbenchmarker import resource
from tests import pkb_common_test_case

FLAGS = flags.FLAGS


class NonFreezeRestoreResource(resource.BaseResource):
  """Dummy class that is missing _Freeze()/_Restore()/_UpdateTimeout()."""

  def _Create(self):
    pass

  def _Delete(self):
    pass


class IncompleteFreezeRestoreResource(NonFreezeRestoreResource):
  """Dummy class that is missing _UpdateTimeout()."""

  def _Freeze(self):
    pass

  def _Restore(self):
    pass


class CompleteFreezeRestoreResource(IncompleteFreezeRestoreResource):
  """Complete implementation needed for Freeze()/Restore()."""

  def _UpdateTimeout(self, timeout_minutes):
    pass


class FreezeRestoreTest(pkb_common_test_case.PkbCommonTestCase):

  def testNoFreezeImplementationRaisesFreezeError(self):
    # Freeze() called with no _Freeze() implementation.
    test_resource = NonFreezeRestoreResource()
    with self.assertRaises(errors.Resource.FreezeError):
      test_resource.Freeze()

  def testNoRestoreImplementationRaisesRestoreError(self):
    # Restore() called with no _Restore() implementation.
    test_resource = NonFreezeRestoreResource()
    with self.assertRaises(errors.Resource.RestoreError):
      test_resource.Restore()

  def testFreezeNoTimeoutRaisesNotImplementedError(self):
    # Freeze() called with no _UpdateTimeout() implementation.
    test_resource = IncompleteFreezeRestoreResource()
    with self.assertRaises(NotImplementedError):
      test_resource.Freeze()

  def testRestoreNoTimeoutRaisesNotImplementedError(self):
    # Restore() called with no _UpdateTimeout() implementation.
    test_resource = IncompleteFreezeRestoreResource()
    with self.assertRaises(NotImplementedError):
      test_resource.Restore()

  @parameterized.named_parameters(
      {
          'testcase_name': 'ProceedsWithDeletion',
          'delete_on_freeze_error': True,
          'expected_deleted': True,
      }, {
          'testcase_name': 'DoesNotDelete',
          'delete_on_freeze_error': False,
          'expected_deleted': False,
      })
  def testDeleteWithFreezeError(self, delete_on_freeze_error, expected_deleted):
    test_resource = CompleteFreezeRestoreResource(
        delete_on_freeze_error=delete_on_freeze_error)
    self.enter_context(
        mock.patch.object(
            test_resource, 'Freeze', side_effect=errors.Resource.FreezeError()))

    # At the start of the test the resource is not deleted.
    self.assertFalse(test_resource.deleted)

    test_resource.Delete(freeze=True)

    self.assertEqual(test_resource.deleted, expected_deleted)

  def testExceptionsRaisedAsFreezeError(self):
    # Ensures that generic exceptions in _Freeze raised as FreezeError.
    test_resource = CompleteFreezeRestoreResource()
    self.enter_context(
        mock.patch.object(test_resource, '_Freeze', side_effect=Exception()))
    with self.assertRaises(errors.Resource.FreezeError):
      test_resource.Freeze()

  def testDeleteWithSuccessfulFreeze(self):
    test_resource = CompleteFreezeRestoreResource()
    mock_freeze = self.enter_context(
        mock.patch.object(test_resource, '_Freeze'))
    mock_update_timeout = self.enter_context(
        mock.patch.object(test_resource, '_UpdateTimeout'))

    test_resource.Delete(freeze=True)

    mock_freeze.assert_called_once()
    mock_update_timeout.assert_called_once()
    self.assertTrue(test_resource.frozen)

  def testCreateWithSuccessfulRestore(self):
    test_resource = CompleteFreezeRestoreResource()
    mock_restore = self.enter_context(
        mock.patch.object(test_resource, '_Restore'))
    mock_create_resource = self.enter_context(
        mock.patch.object(test_resource, '_CreateResource'))

    test_resource.Create(restore=True)

    mock_restore.assert_called_once()
    mock_create_resource.assert_not_called()
    self.assertFalse(test_resource.frozen)

  def testCreateWithRestoreErrorRaisesInsteadOfCreating(self):
    test_resource = CompleteFreezeRestoreResource()
    self.enter_context(
        mock.patch.object(test_resource, '_Restore', side_effect=Exception()))
    mock_create_resource = self.enter_context(
        mock.patch.object(test_resource, '_CreateResource'))

    with self.assertRaises(errors.Resource.RestoreError):
      test_resource.Create(restore=True)

    mock_create_resource.assert_not_called()


if __name__ == '__main__':
  unittest.main()
