"""Capture and relay live worker-process output for machine-owner logs."""

import asyncio
from collections.abc import Awaitable, Callable
import sys
from typing import Any, TextIO


SendEvent = Callable[[dict[str, Any]], Awaitable[None]]


class CapturedTextStream:
    """Forward a process text stream while relaying successful writes live."""

    def __init__(self, stream: TextIO, stream_name: str, log_manager: "MachineLogManager"):
        self._stream = stream
        self._stream_name = stream_name
        self._log_manager = log_manager

    def write(self, text: str) -> int:
        written = self._stream.write(text)
        self._log_manager.record_output(self._stream_name, text[:written])
        return written

    def flush(self) -> None:
        self._stream.flush()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)


class MachineLogManager:
    """Relay live worker logs through the active persistent server connection."""

    def __init__(self) -> None:
        self._send_event: SendEvent | None = None
        self._send_lock = asyncio.Lock()
        self._has_announced_worker_started = False

    def attach(self, send_event: SendEvent) -> None:
        """Start live delivery through the current persistent worker WebSocket."""

        self._send_event = send_event

    def detach(self) -> None:
        """Stop live delivery when the persistent worker WebSocket is unavailable."""

        self._send_event = None

    def record_output(self, stream: str, text: str) -> None:
        if stream not in {"stdout", "stderr"}:
            raise ValueError("Machine log stream must be stdout or stderr")

        if text:
            self._schedule_live_event(
                {
                    "name": "machine_log",
                    "data": {
                        "stream": stream,
                        "text": text,
                    },
                }
            )

    def announce_worker_started(self) -> None:
        """Emit the startup event once when a live server connection is available."""

        if self._has_announced_worker_started:
            return

        self._has_announced_worker_started = True
        self.record_lifecycle("worker_started")

    def record_lifecycle(self, event: str) -> None:
        if not event:
            raise ValueError("Machine lifecycle event is required")

        self._schedule_live_event(
            {
                "name": "machine_lifecycle",
                "data": {"event": event},
            }
        )

    def install_process_stream_capture(self) -> None:
        """Install stdout/stderr wrappers once before Uvicorn begins writing logs."""

        if not isinstance(sys.stdout, CapturedTextStream):
            sys.stdout = CapturedTextStream(sys.stdout, "stdout", self)

        if not isinstance(sys.stderr, CapturedTextStream):
            sys.stderr = CapturedTextStream(sys.stderr, "stderr", self)

    def _schedule_live_event(self, event: dict[str, Any]) -> None:
        if self._send_event is None:
            return

        try:
            event_loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        event_loop.create_task(self._send(event))

    async def _send(self, event: dict[str, Any]) -> None:
        send_event = self._send_event
        if send_event is None:
            return

        async with self._send_lock:
            if self._send_event is not send_event:
                return

            try:
                await send_event(event)
            except Exception:
                self.detach()


machine_log_manager = MachineLogManager()


__all__ = [
    "CapturedTextStream",
    "MachineLogManager",
    "machine_log_manager",
]
