"""Cliente mínimo do IPC local do Discord (Windows, named pipe).

Formato de cada mensagem: u32 opcode + u32 tamanho + JSON (little endian).
Os handles de pipe síncronos do Windows serializam leitura e escrita, então não há
thread de leitura: antes de ler, PeekNamedPipe diz quantos bytes já chegaram.
"""
from __future__ import annotations

import ctypes
import json
import logging
import msvcrt
import os
import struct
import time
import uuid
from ctypes import wintypes

log = logging.getLogger(__name__)

OP_HANDSHAKE, OP_FRAME, OP_CLOSE, OP_PING, OP_PONG = 0, 1, 2, 3, 4

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_PeekNamedPipe = _kernel32.PeekNamedPipe
_PeekNamedPipe.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                           ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
                           ctypes.POINTER(wintypes.DWORD)]
_PeekNamedPipe.restype = wintypes.BOOL


class DiscordError(Exception):
    """Discord fechado, ID inválido ou resposta de erro."""


class DiscordIPC:
    def __init__(self, client_id: str):
        self.client_id = str(client_id).strip()
        self._pipe = None
        self.user: dict | None = None

    @property
    def connected(self) -> bool:
        return self._pipe is not None

    # ---- conexão -------------------------------------------------------------------------
    def connect(self, timeout: float = 5.0) -> dict:
        if not self.client_id.isdigit():
            raise DiscordError("Application ID inválido (precisa ser só números)")
        last_error: Exception | None = None
        for i in range(10):
            path = rf"\\?\pipe\discord-ipc-{i}"
            try:
                self._pipe = open(path, "w+b", buffering=0)
            except OSError as exc:
                last_error = exc
                continue
            try:
                self._send(OP_HANDSHAKE, {"v": 1, "client_id": self.client_id})
                op, data = self._recv(timeout)
                if op == OP_CLOSE:
                    raise DiscordError(f"Discord recusou a conexão: {data.get('message')} ({data.get('code')})")
                if data.get("evt") != "READY":
                    raise DiscordError(f"Resposta inesperada no handshake: {data}")
                self.user = (data.get("data") or {}).get("user")
                log.info("Conectado ao Discord pelo pipe %d como %s", i,
                         (self.user or {}).get("username", "?"))
                return data
            except DiscordError:
                self.close()
                raise
            except OSError as exc:
                last_error = exc
                self.close()
        raise DiscordError(f"Discord não está aberto ({last_error})")

    def close(self) -> None:
        pipe, self._pipe = self._pipe, None
        if pipe is not None:
            try:
                pipe.close()
            except OSError:
                pass

    # ---- comandos ------------------------------------------------------------------------
    def set_activity(self, activity: dict | None) -> dict:
        return self._command("SET_ACTIVITY", {"pid": os.getpid(), "activity": activity})

    def clear_activity(self) -> None:
        if self.connected:
            try:
                self.set_activity(None)
            except (DiscordError, OSError):
                pass

    def poll(self) -> None:
        """Responde PINGs e descarta eventos que chegaram sozinhos."""
        if not self.connected:
            return
        try:
            while self._available() >= 8:
                op, data = self._recv(1.0)
                if op == OP_CLOSE:
                    self.close()
                    raise DiscordError(f"Discord fechou a conexão: {data}")
        except OSError as exc:
            self.close()
            raise DiscordError(f"Conexão perdida: {exc}") from exc

    def _command(self, cmd: str, args: dict, timeout: float = 5.0) -> dict:
        if not self.connected:
            raise DiscordError("não conectado")
        nonce = str(uuid.uuid4())
        try:
            self._send(OP_FRAME, {"cmd": cmd, "args": args, "nonce": nonce})
            deadline = time.monotonic() + timeout
            while True:
                op, data = self._recv(max(0.1, deadline - time.monotonic()))
                if op == OP_CLOSE:
                    self.close()
                    raise DiscordError(f"Discord fechou a conexão: {data}")
                if data.get("nonce") == nonce:
                    break
        except OSError as exc:
            self.close()
            raise DiscordError(f"Conexão perdida: {exc}") from exc
        if data.get("evt") == "ERROR":
            err = data.get("data") or {}
            raise DiscordError(f"{cmd} recusado: {err.get('message')} ({err.get('code')})")
        return data

    # ---- baixo nível ---------------------------------------------------------------------
    def _send(self, op: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._pipe.write(struct.pack("<II", op, len(body)) + body)

    def _available(self) -> int:
        handle = msvcrt.get_osfhandle(self._pipe.fileno())
        avail = wintypes.DWORD(0)
        if not _PeekNamedPipe(handle, None, 0, None, ctypes.byref(avail), None):
            raise OSError(ctypes.get_last_error(), "PeekNamedPipe falhou (pipe fechado)")
        return avail.value

    def _read_exact(self, n: int) -> bytes:
        chunks = b""
        while len(chunks) < n:
            part = self._pipe.read(n - len(chunks))
            if not part:
                raise OSError("pipe fechado")
            chunks += part
        return chunks

    def _recv(self, timeout: float) -> tuple[int, dict]:
        deadline = time.monotonic() + timeout
        while True:
            if self._available() >= 8:
                break
            if time.monotonic() > deadline:
                raise OSError("tempo esgotado esperando o Discord")
            time.sleep(0.02)
        op, length = struct.unpack("<II", self._read_exact(8))
        data = json.loads(self._read_exact(length).decode("utf-8")) if length else {}
        if op == OP_PING:
            self._send(OP_PONG, data)
            return self._recv(max(0.1, deadline - time.monotonic()))
        return op, data
