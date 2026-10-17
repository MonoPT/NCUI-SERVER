"""Multiplexed Fish PTY sessions for the server-to-worker WebSocket."""

import asyncio
import base64
import binascii
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import partial
import fcntl
import os
import pty
import signal
import struct
import subprocess
import termios
from typing import Any


MAX_INPUT_BYTES = 64 * 1024
MAX_OUTPUT_BYTES = 64 * 1024
MAX_COLUMNS = 500
MAX_ROWS = 200
DEFAULT_COLUMNS = 80
DEFAULT_ROWS = 24
MAX_SESSION_ID_LENGTH = 256

SendEvent = Callable[[dict[str, Any]], Awaitable[None]]


class TerminalMessageError(ValueError):
    """A terminal message is malformed or exceeds protocol bounds."""


@dataclass
class TerminalSession:
    """Resources owned by one opaque server-created terminal session."""

    session_id: str
    process: subprocess.Popen[bytes]
    master_fd: int
    output_task: asyncio.Task[None]
    wait_task: asyncio.Task[None]
    closing: bool = False


def session_id_from_message(data: Any) -> str:
    """Return a bounded opaque session ID from a terminal message payload."""

    if not isinstance(data, dict):
        raise TerminalMessageError("Terminal message data must be an object")

    session_id = data.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise TerminalMessageError("Terminal session ID is required")

    if len(session_id) > MAX_SESSION_ID_LENGTH:
        raise TerminalMessageError("Terminal session ID is too long")

    return session_id


def dimensions_from_message(data: dict[str, Any]) -> tuple[int, int]:
    """Validate terminal dimensions, applying version-one defaults on open."""

    columns = _dimension_from_value(
        data.get("cols", DEFAULT_COLUMNS),
        "columns",
        MAX_COLUMNS,
    )
    rows = _dimension_from_value(
        data.get("rows", DEFAULT_ROWS),
        "rows",
        MAX_ROWS,
    )

    return columns, rows


def _dimension_from_value(value: Any, name: str, maximum: int) -> int:
    if isinstance(value, bool):
        raise TerminalMessageError(f"Terminal {name} must be an integer")

    if isinstance(value, str):
        if (
            not value.isascii()
            or not value.isdecimal()
            or (len(value) > 1 and value.startswith("0"))
        ):
            raise TerminalMessageError(f"Terminal {name} must be a canonical decimal integer")

        value = int(value)

    if not isinstance(value, int):
        raise TerminalMessageError(f"Terminal {name} must be an integer")

    if not 1 <= value <= maximum:
        raise TerminalMessageError(f"Terminal {name} must be between 1 and {maximum}")

    return value


def input_from_message(data: dict[str, Any]) -> bytes:
    """Decode bounded base64 terminal input without interpreting user bytes."""

    encoded_input = data.get("input")
    if not isinstance(encoded_input, str):
        raise TerminalMessageError("Terminal input must be base64 text")

    maximum_encoded_length = ((MAX_INPUT_BYTES + 2) // 3) * 4
    if len(encoded_input) > maximum_encoded_length:
        raise TerminalMessageError(f"Terminal input exceeds {MAX_INPUT_BYTES} bytes")

    try:
        input_bytes = base64.b64decode(encoded_input, validate=True)
    except (binascii.Error, ValueError) as error:
        raise TerminalMessageError("Terminal input is not valid base64") from error

    if len(input_bytes) > MAX_INPUT_BYTES:
        raise TerminalMessageError(f"Terminal input exceeds {MAX_INPUT_BYTES} bytes")

    return input_bytes


def configure_controlling_terminal(slave_fd: int) -> None:
    """Give a spawned shell its own session and controlling PTY on Linux."""

    os.setsid()
    fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)


class TerminalManager:
    """Create, route, and clean up PTY sessions for one worker WebSocket."""

    def __init__(self, send_event: SendEvent):
        self._send_event = send_event
        self._sessions: dict[str, TerminalSession] = {}
        self._send_lock = asyncio.Lock()

    async def open(self, data: Any) -> None:
        """Open a Fish session with the server-provided opaque session ID."""

        session_id = session_id_from_message(data)
        columns, rows = dimensions_from_message(data)

        if session_id in self._sessions:
            await self._send_error(session_id, "Terminal session is already open")
            return

        master_fd: int | None = None
        slave_fd: int | None = None

        try:
            master_fd, slave_fd = pty.openpty()
            self._set_window_size(master_fd, columns, rows)

            process = subprocess.Popen(
                ["fish"],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                env={
                    **os.environ,
                    "TERM": "xterm-256color",
                },
                preexec_fn=partial(configure_controlling_terminal, slave_fd),
            )
        except (OSError, subprocess.SubprocessError):
            if master_fd is not None:
                os.close(master_fd)

            await self._send_error(session_id, "Unable to start terminal session")
            return
        finally:
            if slave_fd is not None:
                os.close(slave_fd)

        output_task = asyncio.create_task(self._forward_output(session_id, master_fd))
        wait_task = asyncio.create_task(self._wait_for_exit(session_id, process))

        self._sessions[session_id] = TerminalSession(
            session_id=session_id,
            process=process,
            master_fd=master_fd,
            output_task=output_task,
            wait_task=wait_task,
        )

    async def input(self, data: Any) -> None:
        """Write server-provided opaque terminal bytes to the matching PTY."""

        session_id = session_id_from_message(data)
        input_bytes = input_from_message(data)
        session = self._sessions.get(session_id)

        if session is None or session.closing:
            await self._send_error(session_id, "Terminal session is not open")
            return

        try:
            await asyncio.to_thread(self._write_all, session.master_fd, input_bytes)
        except OSError:
            await self._send_error(session_id, "Terminal session is no longer available")
            await self.close(session_id, reason="unavailable")

    async def resize(self, data: Any) -> None:
        """Update the PTY window size and notify Fish of the resize."""

        session_id = session_id_from_message(data)
        columns, rows = dimensions_from_message(data)
        session = self._sessions.get(session_id)

        if session is None or session.closing:
            await self._send_error(session_id, "Terminal session is not open")
            return

        try:
            self._set_window_size(session.master_fd, columns, rows)
            os.killpg(session.process.pid, signal.SIGWINCH)
        except (OSError, ProcessLookupError):
            await self._send_error(session_id, "Terminal session is no longer available")
            await self.close(session_id, reason="unavailable")

    async def error(self, session_id: str, message: str) -> None:
        """Send a safe protocol error while serializing shared socket writes."""

        await self._send_error(session_id, message)

    async def close(
        self,
        session_id: str,
        reason: str = "closed",
        emit_exit: bool = True,
    ) -> None:
        """Terminate a session and optionally report its terminal exit to the server."""

        session = self._sessions.pop(session_id, None)
        if session is None:
            return

        session.closing = True
        session.output_task.cancel()
        os.close(session.master_fd)

        await self._terminate_process(session.process)

        if emit_exit:
            await self._send_exit(session_id, session.process.returncode, reason)

    async def close_all(self) -> None:
        """Close every session when the server-worker socket disconnects."""

        session_ids = list(self._sessions)

        for session_id in session_ids:
            await self.close(
                session_id,
                reason="transport_lost",
                emit_exit=False,
            )

    async def _forward_output(self, session_id: str, master_fd: int) -> None:
        """Forward PTY output without reserving a worker-thread-pool thread."""

        event_loop = asyncio.get_running_loop()
        output_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

        def read_available_output() -> None:
            try:
                output_bytes = os.read(master_fd, MAX_OUTPUT_BYTES)
            except BlockingIOError:
                return
            except OSError:
                output_queue.put_nowait(None)
                return

            output_queue.put_nowait(output_bytes or None)

        try:
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            event_loop.add_reader(master_fd, read_available_output)

            while True:
                output_bytes = await output_queue.get()
                if output_bytes is None:
                    return

                session = self._sessions.get(session_id)
                if session is None or session.closing:
                    return

                await self._send_event_message(
                    "terminal_output",
                    {
                        "session_id": session_id,
                        "output": base64.b64encode(output_bytes).decode("ascii"),
                    },
                )
        except (OSError, RuntimeError, asyncio.CancelledError):
            return
        finally:
            event_loop.remove_reader(master_fd)

    async def _wait_for_exit(
        self,
        session_id: str,
        process: subprocess.Popen[bytes],
    ) -> None:
        await asyncio.to_thread(process.wait)

        session = self._sessions.pop(session_id, None)
        if session is None or session.closing:
            return

        session.closing = True
        session.output_task.cancel()
        os.close(session.master_fd)

        await self._send_exit(session_id, process.returncode, "exited")

    async def _send_error(self, session_id: str, message: str) -> None:
        await self._send_event_message(
            "terminal_error",
            {
                "session_id": session_id,
                "message": message,
            },
        )

    async def _send_exit(
        self,
        session_id: str,
        return_code: int | None,
        reason: str,
    ) -> None:
        await self._send_event_message(
            "terminal_exit",
            {
                "session_id": session_id,
                "exit_code": return_code,
                "reason": reason,
            },
        )

    async def _send_event_message(self, name: str, data: dict[str, Any]) -> None:
        event = {
            "name": name,
            "data": data,
        }

        async with self._send_lock:
            await self._send_event(event)

    @staticmethod
    def _set_window_size(master_fd: int, columns: int, rows: int) -> None:
        window_size = struct.pack("HHHH", rows, columns, 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, window_size)

    @staticmethod
    def _write_all(master_fd: int, input_bytes: bytes) -> None:
        bytes_written = 0

        while bytes_written < len(input_bytes):
            written = os.write(master_fd, input_bytes[bytes_written:])

            if written == 0:
                raise OSError("PTY input could not be written")

            bytes_written += written

    @staticmethod
    async def _terminate_process(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return

        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return

        try:
            await asyncio.wait_for(asyncio.to_thread(process.wait), timeout=2)
            return
        except TimeoutError:
            pass

        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return

        await asyncio.to_thread(process.wait)
