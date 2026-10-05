from __future__ import annotations

import json
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path
from threading import Event, Lock

import psutil

from models import DownloadSettings
from qt import QObject, Signal, Slot
from services.worker_process import settings_to_payload


class DownloadWorker(QObject):
    log = Signal(str)
    progress = Signal(int)
    current_title = Signal(str)
    item_state = Signal(str, str, str, object)
    duplicate_question = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, settings: DownloadSettings) -> None:
        super().__init__()
        self.settings = settings
        self._cancelled = Event()
        self._process: subprocess.Popen[bytes] | None = None
        self._connection: socket.socket | None = None
        self._send_lock = Lock()

    def answer_duplicate(self, decision: str) -> None:
        connection = self._connection
        if connection is not None:
            with self._send_lock:
                try:
                    connection.sendall((json.dumps({"decision": decision}) + "\n").encode("utf-8"))
                except OSError:
                    pass

    @Slot()
    def run(self) -> None:
        if self._cancelled.is_set():
            self.finished.emit(False, "Descarga cancelada.")
            return

        command = [sys.executable]
        if not getattr(sys, "frozen", False):
            command.append(str(Path(__file__).resolve().parents[1] / "main.py"))
        command.append("--download-worker")
        result: tuple[bool, str] | None = None
        listener: socket.socket | None = None
        try:
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            listener.settimeout(0.2)
        except OSError as exc:
            if listener is not None:
                listener.close()
            self.finished.emit(False, f"No se pudo iniciar la comunicación local: {exc}")
            return
        token = secrets.token_hex(16)
        env = {
            **os.environ,
            "SPIDER_WORKER_PORT": str(listener.getsockname()[1]),
            "SPIDER_WORKER_TOKEN": token,
        }
        try:
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
            )
            if self._cancelled.is_set():
                self._kill_process_tree()
            connection = self._accept_worker(listener, token)
            self._connection = connection
            with connection:
                message = json.dumps(settings_to_payload(self.settings)) + "\n"
                connection.sendall(message.encode("utf-8"))
                with connection.makefile("r", encoding="utf-8") as reader:
                    for line in reader:
                        try:
                            payload = json.loads(line)
                            event, values = payload["event"], payload["values"]
                        except (ValueError, KeyError, TypeError):
                            self.log.emit(line.rstrip())
                            continue
                        if event == "finished":
                            result = bool(values[0]), str(values[1])
                        elif event == "log":
                            self.log.emit(str(values[0]))
                        elif event == "progress":
                            self.progress.emit(int(values[0]))
                        elif event == "current_title":
                            self.current_title.emit(str(values[0]))
                        elif event == "item_state":
                            self.item_state.emit(str(values[0]), str(values[1]), str(values[2]), values[3])
                        elif event == "duplicate_question":
                            self.duplicate_question.emit(str(values[0]))
            exit_code = self._process.wait()
        except Exception as exc:
            self.log.emit(str(exc))
            exit_code = 1
        finally:
            self._connection = None
            listener.close()
            process = self._process
            if process is not None:
                if process.poll() is None:
                    self._kill_process_tree()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            self._process = None

        if self._cancelled.is_set():
            self.finished.emit(False, "Descarga cancelada.")
        elif result is not None:
            self.finished.emit(*result)
        else:
            self.finished.emit(False, f"El proceso de descarga terminó con código {exit_code}.")

    def _accept_worker(self, listener: socket.socket, token: str) -> socket.socket:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if self._cancelled.is_set():
                raise RuntimeError("Descarga cancelada.")
            if self._process is not None and self._process.poll() is not None:
                raise RuntimeError("El proceso de descarga terminó antes de conectar.")
            try:
                connection, _ = listener.accept()
            except socket.timeout:
                continue
            connection.settimeout(5)
            try:
                with connection.makefile("r", encoding="utf-8") as reader:
                    supplied_token = reader.readline().rstrip("\r\n")
                if supplied_token != token:
                    raise RuntimeError("Conexión de descarga no autorizada.")
            except Exception:
                connection.close()
                raise
            connection.settimeout(None)
            return connection
        raise TimeoutError("El proceso de descarga no pudo iniciar.")

    def cancel(self) -> None:
        self._cancelled.set()
        self._kill_process_tree()

    def _kill_process_tree(self) -> None:
        process = self._process
        if process is None or process.poll() is not None:
            return
        try:
            parent = psutil.Process(process.pid)
            children = parent.children(recursive=True)
            for child in children:
                child.kill()
            parent.kill()
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied:
            process.kill()
