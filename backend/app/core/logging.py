from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class LogEvent:
    event: str
    trace_id: str | None = None
    session_id: str | None = None
    agent: str | None = None
    latency_ms: int | None = None
    input: Any | None = None
    output: Any | None = None
    usage: dict[str, Any] | None = None
    extra: dict[str, Any] | None = None


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base: dict[str, Any] = {
            "level": record.levelname,
            "time": int(time.time() * 1000),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "event") and isinstance(record.event, dict):
            base.update(record.event)
        return json.dumps(base, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.handlers.clear()
    root.addHandler(handler)


def log_event(logger: logging.Logger, evt: LogEvent, level: int = logging.INFO) -> None:
    logger.log(level, evt.event, extra={"event": asdict(evt)})

