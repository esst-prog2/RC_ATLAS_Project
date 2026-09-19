from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class RepeatingRuntimeWorker:
    def __init__(
        self,
        name: str,
        handler: Callable[[], Any],
        interval_seconds: int = 300,
        enabled: bool = False,
    ) -> None:
        self.name = name
        self.handler = handler
        self.interval_seconds = max(1, int(interval_seconds))
        self.enabled = bool(enabled)
        self.started_at = _utc_now_iso()
        self._monotonic_started = time.monotonic()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self.last_run_at = ""
        self.last_completed_at = ""
        self.last_result: Dict[str, Any] = {}
        self.last_error = ""

    def configure(self, *, interval_seconds: Optional[int] = None, enabled: Optional[bool] = None) -> None:
        with self._lock:
            if interval_seconds is not None:
                self.interval_seconds = max(1, int(interval_seconds))
            if enabled is not None:
                self.enabled = bool(enabled)

    def run_once(self) -> Any:
        with self._lock:
            self.last_run_at = _utc_now_iso()
            self.last_error = ""
        try:
            result = self.handler()
            with self._lock:
                self.last_result = result if isinstance(result, dict) else {"result": result}
                self.last_completed_at = _utc_now_iso()
            return result
        except Exception as exc:
            with self._lock:
                self.last_error = str(exc)
                self.last_completed_at = _utc_now_iso()
            raise

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception:
                pass
            self._stop_event.wait(self.interval_seconds)

    def start(self) -> bool:
        with self._lock:
            if not self.enabled:
                return False
            if self._thread and self._thread.is_alive():
                return False
            self._stop_event = threading.Event()
            self._thread = threading.Thread(target=self._loop, name=self.name, daemon=True)
            self._thread.start()
            return True

    def stop(self, timeout: float = 3.0) -> bool:
        with self._lock:
            self._stop_event.set()
            thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=timeout)
            return not thread.is_alive()
        return True

    def status(self) -> Dict[str, Any]:
        with self._lock:
            thread = self._thread
            return {
                "name": self.name,
                "enabled": self.enabled,
                "interval_seconds": self.interval_seconds,
                "started_at": self.started_at,
                "uptime_seconds": max(0, int(time.monotonic() - self._monotonic_started)),
                "last_run_at": self.last_run_at,
                "last_completed_at": self.last_completed_at,
                "last_result": dict(self.last_result),
                "last_error": self.last_error,
                "thread_alive": bool(thread and thread.is_alive()),
            }
