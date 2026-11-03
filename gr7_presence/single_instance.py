"""Impede duas cópias rodando ao mesmo tempo (mutex nomeado do Windows)."""
from __future__ import annotations

import ctypes
from ctypes import wintypes

ERROR_ALREADY_EXISTS = 183

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
_kernel32.CreateMutexW.restype = wintypes.HANDLE


class SingleInstance:
    def __init__(self, name: str):
        self._handle = _kernel32.CreateMutexW(None, False, f"Local\\{name}")
        self.acquired = bool(self._handle) and ctypes.get_last_error() != ERROR_ALREADY_EXISTS

    def release(self) -> None:
        if self._handle:
            _kernel32.CloseHandle(self._handle)
            self._handle = None
