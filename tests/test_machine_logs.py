import asyncio
from io import StringIO
import unittest

from worker.machine_logs import CapturedTextStream, MachineLogManager


class MachineLogManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_captured_stream_forwards_and_publishes_live_stdout(self):
        events = []

        async def send_event(event):
            events.append(event)

        manager = MachineLogManager()
        manager.attach(send_event)

        stream = StringIO()
        captured_stream = CapturedTextStream(stream, "stdout", manager)

        self.assertEqual(captured_stream.write("live output\n"), 12)
        self.assertEqual(stream.getvalue(), "live output\n")

        await asyncio.sleep(0)

        self.assertEqual(
            events,
            [
                {
                    "name": "machine_log",
                    "data": {
                        "stream": "stdout",
                        "text": "live output\n",
                    },
                }
            ],
        )

    async def test_manager_publishes_live_stderr_and_lifecycle_events(self):
        events = []

        async def send_event(event):
            events.append(event)

        manager = MachineLogManager()
        manager.attach(send_event)

        manager.record_output("stderr", "warning\n")
        manager.announce_worker_started()
        manager.announce_worker_started()
        manager.record_lifecycle("server_connection_opened")

        await asyncio.sleep(0)

        self.assertEqual(
            events,
            [
                {
                    "name": "machine_log",
                    "data": {
                        "stream": "stderr",
                        "text": "warning\n",
                    },
                },
                {
                    "name": "machine_lifecycle",
                    "data": {"event": "worker_started"},
                },
                {
                    "name": "machine_lifecycle",
                    "data": {"event": "server_connection_opened"},
                },
            ],
        )

    async def test_events_are_not_retained_while_no_server_connection_exists(self):
        events = []

        async def send_event(event):
            events.append(event)

        manager = MachineLogManager()
        manager.record_output("stdout", "not retained\n")
        manager.record_lifecycle("worker_started")

        manager.attach(send_event)
        await asyncio.sleep(0)

        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
