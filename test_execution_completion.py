import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch
from app import proccess_message
from state import GlobalState


class Socket:
    def __init__(self): self.events = []
    async def send_json(self, event): self.events.append(event)


def workflow_message(workflow_data=None, owner="owner"):
    return json.dumps({"name": "run_workflow", "data": {
        "execution_id": "server-token", "owner_id": owner,
        "workflow_data": workflow_data if workflow_data is not None else json.dumps({"workflow_id": "workflow", "nodes": [], "edges": []}),
    }})


class CompletionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        lock = patch("execution_context.cache_lock", asyncio.Lock())
        lock.start()
        self.addCleanup(lock.stop)
    async def test_cache_preparation_cannot_mutate_inputs_during_execution(self):
        import apis
        started, finish_allowed = asyncio.Event(), asyncio.Event()
        async def running(*args):
            started.set()
            await finish_allowed.wait()
        with patch("events.run_workflow.run_workflow", side_effect=running), \
             patch("apis._files", new=AsyncMock(return_value=[])) as prepare, \
             patch("apis._upload", new=AsyncMock(return_value={"status": "saved"})) as upload:
            execution = asyncio.create_task(proccess_message(workflow_message(), Socket(), [], GlobalState()))
            await asyncio.wait_for(started.wait(), 1)
            preparation = asyncio.create_task(apis.files([]))
            transfer = asyncio.create_task(apis.upload(None, "hash", 0, "source", "/input/owner/file"))
            await asyncio.sleep(0)
            prepare.assert_not_awaited()
            upload.assert_not_awaited()
            self.assertFalse(preparation.done())
            self.assertFalse(transfer.done())
            finish_allowed.set()
            await asyncio.wait_for(asyncio.gather(execution, preparation, transfer), 1)
            prepare.assert_awaited_once()
            upload.assert_awaited_once()
    async def test_cancellation_is_terminal_error_and_releases_worker_lease(self):
        import execution_context
        socket = Socket()
        with patch("events.run_workflow.run_workflow", new=AsyncMock(side_effect=asyncio.CancelledError)):
            with self.assertRaises(asyncio.CancelledError):
                await proccess_message(workflow_message(), socket, [], GlobalState())
        self.assertEqual(socket.events[-1]["name"], "WorkflowError")
        self.assertFalse(execution_context.cache_lock.locked())
    async def test_empty_workflow_has_exactly_one_terminal_acknowledgement(self):
        socket = Socket()
        with patch("events.run_workflow.build_dag", return_value=[]):
            await proccess_message(workflow_message(), socket, [], GlobalState())
        self.assertEqual([e["name"] for e in socket.events], ["WorkflowStarted", "WorkflowFinished"])
        self.assertTrue(all(e["execution_id"] == "server-token" for e in socket.events))
    async def test_parse_owner_and_build_errors_are_terminal(self):
        for data, owner in [("{", "owner"), (None, "../other"), (None, "owner")]:
            socket = Socket()
            with patch("events.run_workflow.build_dag", side_effect=ValueError("build failed")):
                await proccess_message(workflow_message(data, owner), socket, [], GlobalState())
            terminal = [e for e in socket.events if e["name"] in ("WorkflowFinished", "WorkflowError")]
            self.assertEqual(len(terminal), 1)
            self.assertEqual(terminal[0]["name"], "WorkflowError")
            self.assertEqual(terminal[0]["execution_id"], "server-token")
    async def test_node_error_does_not_acknowledge_while_other_work_is_running(self):
        socket = Socket()
        node_error_sent, finish_allowed = asyncio.Event(), asyncio.Event()
        async def running(message, ws, nodes, state):
            await ws.send_json({"name": "NodeExecutionError", "data": {"workflow_id": "workflow", "node_id": "node", "msg": "failure"}})
            node_error_sent.set()
            await finish_allowed.wait()
        with patch("events.run_workflow.run_workflow", side_effect=running):
            task = asyncio.create_task(proccess_message(workflow_message(), socket, [], GlobalState()))
            await asyncio.wait_for(node_error_sent.wait(), 1)
            self.assertEqual([e["name"] for e in socket.events], ["NodeExecutionError"])
            finish_allowed.set()
            await task
        self.assertEqual([e["name"] for e in socket.events], ["NodeExecutionError", "WorkflowFinished"])
    async def test_missing_dataframe_and_dataframe_errors_always_complete(self):
        message = json.dumps({"name": "dataframe_get_data", "data": {
            "execution_id": "dataframe-token", "owner_id": "owner",
            "dataframe_get_data": json.dumps({"page": 0, "df_id": "missing", "table_id": "table"}),
        }})
        for error in [None, ValueError("bad dataframe")]:
            socket = Socket()
            with patch("app.get_df_data", new=AsyncMock(side_effect=error)):
                await proccess_message(message, socket, [], GlobalState())
            self.assertEqual(socket.events, [{"name": "ExecutionComplete", "data": {}, "execution_id": "dataframe-token"}])


if __name__ == "__main__": unittest.main()
