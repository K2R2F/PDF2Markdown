"""Windows process tree ownership, including termination on parent exit."""
import ctypes as C
from ctypes import wintypes as W
import time


class BasicLimits(C.Structure):
    _fields_ = [('process_time', C.c_longlong), ('job_time', C.c_longlong),
                ('flags', W.DWORD), ('min_working_set', C.c_size_t), ('max_working_set', C.c_size_t),
                ('active_limit', W.DWORD), ('affinity', C.c_size_t), ('priority', W.DWORD), ('scheduling', W.DWORD)]


class IOCounts(C.Structure):
    _fields_ = [(name, C.c_ulonglong) for name in ('read_ops', 'write_ops', 'other_ops', 'read', 'write', 'other')]


class ExtendedLimits(C.Structure):
    _fields_ = [('basic', BasicLimits), ('io', IOCounts), ('process_memory', C.c_size_t),
                ('job_memory', C.c_size_t), ('peak_process', C.c_size_t), ('peak_job', C.c_size_t)]


class Accounting(C.Structure):
    _fields_ = [(n, C.c_longlong) for n in ('user', 'kernel', 'period_user', 'period_kernel')] + [
        (n, W.DWORD) for n in ('faults', 'total', 'active', 'terminated')]


class WindowsJob:
    def __init__(self):
        self.api = C.WinDLL('kernel32', use_last_error=True)
        specs = {
            'CreateJobObjectW': ([C.c_void_p, W.LPCWSTR], W.HANDLE),
            'SetInformationJobObject': ([W.HANDLE, C.c_int, C.c_void_p, W.DWORD], W.BOOL),
            'AssignProcessToJobObject': ([W.HANDLE, W.HANDLE], W.BOOL),
            'TerminateJobObject': ([W.HANDLE, W.UINT], W.BOOL),
            'QueryInformationJobObject': ([W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.c_void_p], W.BOOL),
            'CloseHandle': ([W.HANDLE], W.BOOL),
        }
        for name, (args, result) in specs.items():
            fn = getattr(self.api, name)
            fn.argtypes, fn.restype = args, result
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise C.WinError(C.get_last_error())
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE; no breakaway.
        if not self.api.SetInformationJobObject(self.handle, 9, C.byref(limits), C.sizeof(limits)):
            error = C.WinError(C.get_last_error())
            self.close()
            raise error

    def assign(self, child):
        if not self.api.AssignProcessToJobObject(self.handle, W.HANDLE(int(child._handle))):
            raise C.WinError(C.get_last_error())

    def stop(self, timeout=10):
        if not self.api.TerminateJobObject(self.handle, 1):
            raise C.WinError(C.get_last_error())
        deadline = time.monotonic() + timeout
        while True:
            counts = Accounting()
            if not self.api.QueryInformationJobObject(self.handle, 1, C.byref(counts), C.sizeof(counts), None):
                raise C.WinError(C.get_last_error())
            if counts.active == 0:
                return
            if time.monotonic() >= deadline:
                raise TimeoutError('プロセスツリーの停止を確認できません。')
            time.sleep(0.05)

    def close(self):
        if self.handle:
            if not self.api.CloseHandle(self.handle):
                raise C.WinError(C.get_last_error())
            self.handle = None
