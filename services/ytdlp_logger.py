from __future__ import annotations

from typing import Protocol


class LogSink(Protocol):
    def info(self, message: str) -> None: ...


class YtdlpLogger:
    def __init__(self, sink: LogSink) -> None:
        self.sink = sink

    def debug(self, message: str) -> None:
        if not message.startswith("[debug]"):
            self.sink.info(message)

    def warning(self, message: str) -> None:
        self.sink.info(f"Aviso: {message}")

    def error(self, message: str) -> None:
        self.sink.info(f"Error: {message}")
