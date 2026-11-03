"""Extrai o grupo de ícones de um .exe do Windows e devolve como bytes de um arquivo .ico."""
from __future__ import annotations

import ctypes
import struct
from ctypes import wintypes

RT_ICON, RT_GROUP_ICON = 3, 14
LOAD_LIBRARY_AS_DATAFILE = 0x2
LOAD_LIBRARY_AS_IMAGE_RESOURCE = 0x20

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
k32.LoadLibraryExW.restype = wintypes.HMODULE
k32.FindResourceW.argtypes = [wintypes.HMODULE, wintypes.LPVOID, wintypes.LPVOID]
k32.FindResourceW.restype = wintypes.HANDLE
k32.LoadResource.argtypes = [wintypes.HMODULE, wintypes.HANDLE]
k32.LoadResource.restype = wintypes.HANDLE
k32.LockResource.argtypes = [wintypes.HANDLE]
k32.LockResource.restype = ctypes.c_void_p
k32.SizeofResource.argtypes = [wintypes.HMODULE, wintypes.HANDLE]
k32.SizeofResource.restype = wintypes.DWORD
k32.FreeLibrary.argtypes = [wintypes.HMODULE]

_EnumNamesProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMODULE, wintypes.LPVOID, wintypes.LPVOID, wintypes.LPARAM)
k32.EnumResourceNamesW.argtypes = [wintypes.HMODULE, wintypes.LPVOID, _EnumNamesProc, wintypes.LPARAM]


def _resource(module, kind, name) -> bytes:
    res = k32.FindResourceW(module, ctypes.c_void_p(name) if isinstance(name, int) else name, ctypes.c_void_p(kind))
    if not res:
        raise OSError(ctypes.get_last_error(), "recurso não encontrado")
    size = k32.SizeofResource(module, res)
    ptr = k32.LockResource(k32.LoadResource(module, res))
    return ctypes.string_at(ptr, size)


def extract_ico(exe_path: str) -> bytes:
    module = k32.LoadLibraryExW(exe_path, None, LOAD_LIBRARY_AS_DATAFILE | LOAD_LIBRARY_AS_IMAGE_RESOURCE)
    if not module:
        raise OSError(ctypes.get_last_error(), f"não abriu {exe_path}")
    try:
        names: list = []

        def collect(_mod, _type, name, _param):
            # nome numérico (MAKEINTRESOURCE) ou string
            value = name if name and name < 0x10000 else ctypes.wstring_at(name)
            names.append(value)
            return False   # só o primeiro grupo (o ícone principal)

        k32.EnumResourceNamesW(module, ctypes.c_void_p(RT_GROUP_ICON), _EnumNamesProc(collect), 0)
        if not names:
            raise OSError("o executável não tem ícones")
        group = _resource(module, RT_GROUP_ICON, names[0])
        _reserved, _type, count = struct.unpack_from("<HHH", group, 0)
        entries, images = [], []
        for i in range(count):
            w, h, colors, res, planes, bits, size, icon_id = struct.unpack_from("<BBBBHHIH", group, 6 + i * 14)
            data = _resource(module, RT_ICON, icon_id)
            entries.append((w, h, colors, res, planes, bits, len(data)))
            images.append(data)
        offset = 6 + 16 * count
        out = struct.pack("<HHH", 0, 1, count)
        for (w, h, colors, res, planes, bits, size) in entries:
            out += struct.pack("<BBBBHHII", w, h, colors, res, planes, bits, size, offset)
            offset += size
        return out + b"".join(images)
    finally:
        k32.FreeLibrary(module)
