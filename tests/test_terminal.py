import base64
import json
import unittest
from typing import cast
from unittest.mock import AsyncMock

from fastapi import WebSocket
from worker.execution.state import GlobalState
from worker.server.dispatch import proccess_message
from worker.terminal.manager import (
    MAX_COLUMNS,
    MAX_INPUT_BYTES,
    MAX_ROWS,
    TerminalManager as WorkerTerminalManager,
    TerminalMessageError,
    dimensions_from_message,
    input_from_message,
)


class Socket:
    def __init__(self):
        self.events = []

    async def send_json(self, event):
        self.events.append(event)


class FakeTerminalManager:
    def __init__(self):
        self.open = AsyncMock()
        self.input = AsyncMock()
        self.resize = AsyncMock()
        self.close = AsyncMock()


class TerminalMessageTests(unittest.IsolatedAsyncioTestCase):
    def test_input_decodes_base64_and_rejects_oversized_payloads(self):
        self.assertEqual(
            input_from_message({"input": base64.b64encode(b"ls\n").decode("ascii")}),
            b"ls\n",
        )

        oversized_input = base64.b64encode(b"x" * (MAX_INPUT_BYTES + 1)).decode("ascii")

        with self.assertRaises(TerminalMessageError):
            input_from_message({"input": oversized_input})

    def test_dimensions_accept_canonical_decimal_strings(self):
        self.assertEqual(dimensions_from_message({"cols": 120, "rows": 40}), (120, 40))
        self.assertEqual(dimensions_from_message({"cols": "120", "rows": "40"}), (120, 40))

    def test_dimensions_reject_invalid_or_out_of_range_values(self):
        for dimensions in (
            {"cols": 0, "rows": 24},
            {"cols": MAX_COLUMNS + 1, "rows": 24},
            {"cols": 80, "rows": 0},
            {"cols": 80, "rows": MAX_ROWS + 1},
            {"cols": True, "rows": 24},
            {"cols": " 80", "rows": "24"},
            {"cols": "+80", "rows": "24"},
            {"cols": "-80", "rows": "24"},
            {"cols": "080", "rows": "24"},
        ):
            with self.assertRaises(TerminalMessageError):
                dimensions_from_message(dimensions)

    async def test_dispatch_routes_server_terminal_messages_by_session_id(self):
        socket = Socket()
        terminal_manager = FakeTerminalManager()
        message = json.dumps(
            {
                "name": "terminal_close",
                "data": {
                    "session_id": "server-created-session",
                },
            }
        )

        await proccess_message(
            message,
            cast(WebSocket, socket),
            [],
            GlobalState(),
            cast(WorkerTerminalManager, terminal_manager),
        )

        terminal_manager.close.assert_awaited_once_with("server-created-session")
        self.assertEqual(socket.events, [])


if __name__ == "__main__":
    unittest.main()
