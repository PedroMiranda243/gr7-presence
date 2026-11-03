"""Encontra o Guitar Rig 7: aplicativo standalone ou plugin VST3 dentro de uma DAW."""
from __future__ import annotations

import ctypes
import fnmatch
import logging
import time
from ctypes import wintypes
from dataclasses import dataclass

import psutil

log = logging.getLogger(__name__)

GR7_EXE = "guitar rig 7.exe"
VST3_MARKER = "guitar rig 7.vst3"

# Executável da DAW (ou do processo-ponte de plugins) -> nome bonito.
DAW_HOSTS = {
    "reaper.exe": "REAPER",
    "reaper_host64.exe": "REAPER",
    "fl64.exe": "FL Studio",
    "fl.exe": "FL Studio",
    "ilbridge.exe": "FL Studio",
    "ableton live*.exe": "Ableton Live",
    "studio one.exe": "Studio One",
    "cubase*.exe": "Cubase",
    "nuendo*.exe": "Nuendo",
    "bitwig studio.exe": "Bitwig Studio",
    "bitwigpluginhost*.exe": "Bitwig Studio",
    "cakewalk.exe": "Cakewalk",
    "sonar.exe": "Cakewalk Sonar",
    "ardour*.exe": "Ardour",
    "waveform*.exe": "Waveform",
    "mixcraft*.exe": "Mixcraft",
    "audacity.exe": "Audacity",
    "cantabile*.exe": "Cantabile",
    "gigperformer*.exe": "Gig Performer",
    "luna.exe": "LUNA",
    "samplitude*.exe": "Samplitude",
    "acid*.exe": "ACID Pro",
    "vegas*.exe": "VEGAS Pro",
}


@dataclass(frozen=True)
class Target:
    kind: str             # "standalone" ou "plugin"
    pid: int
    started_at: float     # epoch em segundos
    exe: str | None = None
    host: str | None = None   # nome da DAW no modo plugin


def _host_name(proc_name: str) -> str | None:
    name = proc_name.lower()
    for pattern, pretty in DAW_HOSTS.items():
        if fnmatch.fnmatch(name, pattern):
            return pretty
    return None


def _has_gr7_loaded(proc: psutil.Process) -> bool:
    try:
        return any(VST3_MARKER in (m.path or "").lower() for m in proc.memory_maps(grouped=True))
    except (psutil.Error, OSError):
        return False


class Detector:
    def __init__(self, detect_plugins: bool = True, plugin_check_every: float = 15.0):
        self.detect_plugins = detect_plugins
        self.plugin_check_every = plugin_check_every
        self._last_plugin_check = 0.0
        self._last_plugin: Target | None = None

    def find(self) -> Target | None:
        hosts: list[psutil.Process] = []
        for proc in psutil.process_iter(["name", "create_time", "exe"]):
            name = (proc.info.get("name") or "").lower()
            if name == GR7_EXE:
                return Target("standalone", proc.pid, proc.info.get("create_time") or time.time(),
                              exe=proc.info.get("exe"))
            if self.detect_plugins and _host_name(name):
                hosts.append(proc)
        if not self.detect_plugins or not hosts:
            self._last_plugin = None
            return None
        return self._find_plugin(hosts)

    def _find_plugin(self, hosts: list[psutil.Process]) -> Target | None:
        now = time.time()
        last = self._last_plugin
        # memory_maps é caro: entre as varreduras, repete o último resultado.
        if now - self._last_plugin_check < self.plugin_check_every:
            if last is None:
                return None
            if any(p.pid == last.pid for p in hosts):
                return last
        self._last_plugin_check = now
        found = None
        for proc in hosts:
            if _has_gr7_loaded(proc):
                started = last.started_at if last and last.pid == proc.pid else now
                found = Target("plugin", proc.pid, started, host=_host_name(proc.info.get("name") or ""))
                break
        self._last_plugin = found
        return found


# ---- versão do executável (Win32) --------------------------------------------------------
def file_version(path: str | None) -> str | None:
    if not path:
        return None
    ver = ctypes.WinDLL("version")
    size = ver.GetFileVersionInfoSizeW(path, None)
    if not size:
        return None
    buf = ctypes.create_string_buffer(size)
    if not ver.GetFileVersionInfoW(path, 0, size, buf):
        return None
    ptr = ctypes.c_void_p()
    length = wintypes.UINT()
    if not ver.VerQueryValueW(buf, "\\", ctypes.byref(ptr), ctypes.byref(length)):
        return None
    # VS_FIXEDFILEINFO: dwSignature, dwStrucVersion, dwFileVersionMS, dwFileVersionLS, ...
    fixed = ctypes.cast(ptr, ctypes.POINTER(wintypes.DWORD * 4)).contents
    ms, ls = fixed[2], fixed[3]
    parts = [ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF]
    while len(parts) > 3 and parts[-1] == 0:
        parts.pop()
    return ".".join(str(p) for p in parts)
