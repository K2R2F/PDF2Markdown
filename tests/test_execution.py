import ctypes
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from core.models import Settings
from execution import controller
from execution.process import ManagedProcess
from execution.lease import OperationLease
from storage import state

FIXTURE = Path(__file__).parent / 'fixtures' / 'process_worker.py'


def wait_until(condition, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.05)
    raise AssertionError('Timed out waiting for test condition')


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        env = patch.dict(os.environ, {'PDF2MARKDOWN_DATA_DIR': self.folder.name})
        env.start()
        self.addCleanup(env.stop)
        controller._job.clear()

    def test_real_job_stops_parent_and_grandchild(self):
        process = ManagedProcess([sys.executable, str(FIXTURE), 'tree', self.folder.name],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: process.job.close() if process.job.handle else None)
        wait_until(lambda: (Path(self.folder.name) / 'leaf.pid').exists())
        pid = int((Path(self.folder.name) / 'leaf.pid').read_text())
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel.WaitForSingleObject.restype = ctypes.c_ulong
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x100000, False, pid)
        self.assertTrue(handle)
        try:
            process.close()
            self.assertIsNotNone(process.poll())
            self.assertEqual(kernel.WaitForSingleObject(handle, 5000), 0)
        finally:
            kernel.CloseHandle(handle)

    def test_os_lease_excludes_another_process(self):
        lease = OperationLease()
        try:
            code = 'from execution.lease import OperationLease; OperationLease()'
            result = subprocess.run([sys.executable, '-c', code], capture_output=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
        finally:
            lease.close()
        again = OperationLease()
        again.close()

    def _fixture_start(self, mode, timeout):
        actual = ManagedProcess
        def factory(command, **kwargs):
            return actual([sys.executable, str(FIXTURE), mode, command[-1]], **kwargs)
        with patch.object(controller, 'ManagedProcess', side_effect=factory):
            batch_id = controller.start(Settings(), 'ファイル', [('a.pdf', b'%PDF-')], [], timeout)
            folder = Path(self.folder.name) / 'jobs' / batch_id
            wait_until(lambda: (folder / 'ready').exists() or controller.snapshot().get('state') != 'running')
            if not (folder / 'ready').exists():
                self.fail(str(controller.snapshot()))
            return batch_id

    def test_real_cancel_preserves_completed_result_and_allows_retry(self):
        batch_id = self._fixture_start('partial', 30)
        controller.cancel(batch_id)
        wait_until(lambda: controller.snapshot().get('state') != 'running')
        settings, results, status = state.load_batch(batch_id)
        self.assertEqual(status, 'cancelled')
        self.assertEqual(results[0].markdown, '# completed')
        self.assertEqual(results[-1].status, 'failure')
        self.assertFalse(controller.snapshot()['blocked'])
        self.assertFalse((Path(self.folder.name) / 'jobs' / batch_id).exists())
        lease = OperationLease()
        lease.close()

    def test_real_timeout_stops_worker(self):
        batch_id = self._fixture_start('wait', 2)
        wait_until(lambda: controller.snapshot().get('state') != 'running')
        self.assertEqual(state.load_batch(batch_id)[2], 'timed_out')
        self.assertFalse(controller.snapshot()['blocked'])

    def test_real_worker_rejects_invalid_pdf_without_models(self):
        batch_id = controller.start(Settings(), 'ファイル', [('invalid.pdf', b'not pdf')], [], 30)
        wait_until(lambda: controller.snapshot().get('state') != 'running', 35)
        self.assertEqual(state.load_batch(batch_id)[2], 'failure')
        self.assertIn('ヘッダー', state.load_batch(batch_id)[1][0].error)

    def test_assignment_failure_does_not_open_gate(self):
        from execution.windows_job import WindowsJob
        with patch.object(WindowsJob, 'assign', side_effect=OSError('injected assignment failure')):
            with self.assertRaises(OSError):
                ManagedProcess([sys.executable, str(FIXTURE), 'wait', self.folder.name],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertFalse((Path(self.folder.name) / 'ready').exists())

    def test_parent_exit_kills_owned_worker(self):
        code = ('import sys,time; from execution.process import ManagedProcess; '
                'p=ManagedProcess([sys.executable,sys.argv[1],"wait",sys.argv[2]]); '
                'print(p.child.pid,flush=True); time.sleep(60)')
        parent = subprocess.Popen([sys.executable, '-u', '-c', code, str(FIXTURE), self.folder.name],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(parent.stdout.close)
        self.addCleanup(parent.stderr.close)
        try:
            wait_until(lambda: (Path(self.folder.name) / 'ready').exists())
            pid = int(parent.stdout.readline().strip())
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
            kernel.OpenProcess.restype = ctypes.c_void_p
            kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            kernel.WaitForSingleObject.restype = ctypes.c_ulong
            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            handle = kernel.OpenProcess(0x100000, False, pid)
            self.assertTrue(handle)
            try:
                parent.kill()
                parent.wait(timeout=10)
                self.assertEqual(kernel.WaitForSingleObject(handle, 5000), 0)
            finally:
                kernel.CloseHandle(handle)
        finally:
            if parent.poll() is None:
                parent.kill()
                parent.wait(timeout=10)

    def test_stale_input_cleanup_preserves_partial_results(self):
        from core.models import Result
        batch_id = 'a' * 32
        folder = Path(self.folder.name) / 'jobs' / batch_id
        folder.mkdir(parents=True)
        (folder / '0.input').write_bytes(b'%PDF-')
        state.save_batch(batch_id, Settings(), [Result('a.pdf', 'success', '# saved')], 'running')
        lease = OperationLease()
        try:
            controller.cleanup_stale_inputs()
        finally:
            lease.close()
        self.assertFalse(folder.exists())
        self.assertEqual(state.load_batch(batch_id)[2], 'interrupted')
        self.assertEqual(state.load_batch(batch_id)[1][0].markdown, '# saved')

    def test_monitor_start_failure_is_saved_and_unlocks(self):
        with patch.object(controller.threading, 'Thread') as thread:
            thread.return_value.start.side_effect = RuntimeError('injected thread failure')
            with self.assertRaises(RuntimeError):
                controller.start(Settings(), 'ファイル', [('a.pdf', b'%PDF-')], [], 30)
        self.assertEqual(state.list_batches()[0][2], 'failure')
        self.assertFalse(controller.OPERATION_LOCK.locked())
        lease = OperationLease()
        lease.close()
