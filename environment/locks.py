"""Shared process-local conversion/setup exclusion."""
import threading

OPERATION_LOCK = threading.Lock()
