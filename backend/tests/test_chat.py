"""Run from project root: .venv/Scripts/python -m unittest discover -s backend/tests -v"""
import asyncio
import json
import os
from backend.tests.fake_ai import start_provider
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from urllib.request import urlopen

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus
from backend.chat import ChatManager, MAX_ROOMS
from backend.main import app, chat_socket
from fastapi import WebSocketDisconnect


def drain(client):
    result = []
    while not client.outbox.empty():
        result.append(client.outbox.get_nowait())
    return result


class RoomRules(unittest.TestCase):
    def setUp(self):
        self.manager = ChatManager()
        self.owner = self.manager.connect()
        self.guest = self.manager.connect()
        self.other = self.manager.connect()
        for client in self.manager.clients.values():
            drain(client)

    def create(self):
        self.manager.handle(self.owner, {"type": "create", "title": " รับฟัง "})
        return self.owner.room_id

    def test_validation_and_membership(self):
        for payload in [None, [], {"type": []}, {"type": "create", "title": "  "},
                        {"type": "create", "title": "x" * 81}, {"type": "join", "roomId": []}]:
            self.manager.handle(self.owner, payload)
            self.assertEqual(drain(self.owner)[-1]["type"], "error")
        room_id = self.create()
        self.assertEqual(self.manager.rooms[room_id].title, "รับฟัง")
        self.manager.handle(self.guest, {"type": "message", "roomId": room_id, "text": "intrusion"})
        self.assertEqual(drain(self.guest)[-1]["type"], "error")
        self.assertEqual(self.manager.rooms[room_id].messages, [])
        self.manager.handle(self.owner, {"type": "create", "title": "duplicate"})
        self.assertEqual(len(self.manager.rooms), 1)

    def test_capacity_and_new_guest_privacy(self):
        room_id = self.create()
        self.manager.handle(self.guest, {"type": "join", "roomId": room_id})
        self.manager.handle(self.other, {"type": "join", "roomId": room_id})
        self.assertEqual(drain(self.other)[-1]["type"], "error")
        for client in self.manager.clients.values():
            drain(client)
        self.manager.handle(self.guest, {"type": "message", "senderId": self.owner.id, "text": "hello"})
        message = drain(self.owner)[-1]["message"]
        self.assertEqual(message["senderId"], self.guest.id)
        self.assertEqual(drain(self.other), [])
        self.manager.handle(self.guest, {"type": "leave"})
        self.assertEqual(self.manager.rooms[room_id].messages, [])
        self.manager.handle(self.other, {"type": "join", "roomId": room_id})
        self.assertEqual(drain(self.other)[-1]["payload"]["messages"], [])
        self.manager.disconnect(self.owner)
        self.assertIsNone(self.other.room_id)
        self.assertEqual(len(self.manager.rooms), 0)

    def test_room_limit_and_released_slot(self):
        for index in range(MAX_ROOMS):
            client = self.manager.connect()
            self.manager.handle(client, {"type": "create", "title": str(index)})
            for connected in self.manager.clients.values():
                drain(connected)
        self.manager.handle(self.owner, {"type": "create", "title": "overflow"})
        self.assertEqual(drain(self.owner)[-1]["type"], "error")
        self.assertEqual(len(self.manager.rooms), 100)
        owner_id = next(iter(self.manager.rooms.values())).owner_id
        self.manager.disconnect(self.manager.clients[owner_id])
        self.manager.handle(self.owner, {"type": "create", "title": "freed slot"})
        self.assertIsNotNone(self.owner.room_id)
        self.assertEqual(len(self.manager.rooms), 100)

    def test_message_length_and_memory_bound(self):
        room_id = self.create()
        self.manager.handle(self.guest, {"type": "join", "roomId": room_id})
        self.manager.handle(self.owner, {"type": "message", "text": "x" * 1001})
        self.assertEqual(drain(self.owner)[-1]["type"], "error")
        for index in range(305):
            self.owner.commands.clear()
            self.manager.handle(self.owner, {"type": "message", "text": str(index)})
            for client in self.manager.clients.values():
                drain(client)
        messages = self.manager.rooms[room_id].messages
        self.assertEqual(len(messages), 300)
        self.assertEqual(messages[0]["text"], "5")

    def test_rate_limit_and_slow_consumer(self):
        for _ in range(31):
            self.manager.handle(self.owner, {"type": "ping"})
            events = drain(self.owner)
        self.assertEqual(events[-1]["type"], "error")
        for _ in range(33):
            self.manager.state(self.guest)
        self.assertTrue(self.guest.stopped.is_set())
        self.assertLessEqual(self.guest.outbox.qsize(), 32)


async def receive_until(ws, predicate):
    async with asyncio.timeout(5):
        while True:
            event = json.loads(await ws.recv())
            if predicate(event):
                return event


async def command(ws, kind, **payload):
    await ws.send(json.dumps({"type": kind, **payload}))


class DisconnectCleanup(unittest.IsolatedAsyncioTestCase):
    async def test_already_closed_socket_does_not_raise(self):
        class ClosedSocket:
            headers = {}

            async def accept(self):
                pass

            async def receive(self):
                return {"type": "websocket.disconnect"}

            async def send_json(self, event):
                raise WebSocketDisconnect(code=1006)

            async def close(self):
                raise WebSocketDisconnect(code=1006)

        app.state.chat = ChatManager()
        await chat_socket(ClosedSocket())
        self.assertEqual(app.state.chat.clients, {})


class LiveAPI(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = start_provider()
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            cls.port = probe.getsockname()[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.ws_url = f"ws://127.0.0.1:{cls.port}/api/ws"
        cls.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1",
             "--port", str(cls.port), "--ws-max-size", "16384", "--no-access-log", "--log-level", "error"],
            cwd=Path(__file__).resolve().parents[2], env={**os.environ, 'API_KEY': 'test', 'SERVICE_URL': f'http://127.0.0.1:{cls.provider.server_port}/bully'}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        for _ in range(100):
            try:
                with urlopen(cls.base + "/api/health", timeout=.2) as response:
                    if response.status == 200:
                        return
            except OSError:
                time.sleep(.05)
        cls.process.terminate()
        cls.process.wait(timeout=5)
        raise RuntimeError("Test server did not start")

    @classmethod
    def tearDownClass(cls):
        cls.provider.shutdown()
        cls.provider.server_close()
        cls.process.terminate()
        cls.process.wait(timeout=5)

    async def test_http_endpoints(self):
        with urlopen(self.base + "/api/health") as response:
            self.assertEqual(json.load(response)["storage"], "memory")
        with urlopen(self.base + "/api/rooms") as response:
            self.assertEqual(json.load(response)["maxRooms"], 100)

    async def test_join_race_messages_and_disconnect(self):
        async with connect(self.ws_url) as owner, connect(self.ws_url) as a, connect(self.ws_url) as b:
            for ws in (owner, a, b):
                await receive_until(ws, lambda e: e["type"] == "state")
            await command(owner, "create", title="live test")
            state = await receive_until(owner, lambda e: e["type"] == "state" and e["payload"]["room"] is not None)
            room_id = state["payload"]["room"]["id"]
            for ws in (a, b):
                await receive_until(ws, lambda e: e["type"] == "state" and any(r["id"] == room_id for r in e["payload"]["rooms"]))
            await asyncio.gather(command(a, "join", roomId=room_id), command(b, "join", roomId=room_id))
            def result(e):
                return e["type"] == "error" or (e["type"] == "state" and e["payload"]["room"] is not None)
            ra, rb = await asyncio.gather(receive_until(a, result), receive_until(b, result))
            self.assertEqual(sorted([ra["type"], rb["type"]]), ["error", "state"])
            winner, loser = (a, b) if ra["type"] == "state" else (b, a)
            await command(winner, "message", text="สวัสดีข้ามการเชื่อมต่อ")
            message = await receive_until(owner, lambda e: e["type"] == "message")
            self.assertEqual(message["message"]["text"], "สวัสดีข้ามการเชื่อมต่อ")
            await command(loser, "hello")
            state = await receive_until(loser, lambda e: e["type"] == "state")
            self.assertEqual(state["payload"]["messages"], [])
            await winner.close()
            state = await receive_until(owner, lambda e: e["type"] == "state" and e["payload"]["room"]["count"] == 1)
            self.assertEqual(state["payload"]["messages"], [])
            await command(loser, "join", roomId=room_id)
            state = await receive_until(loser, lambda e: e["type"] == "state" and e["payload"]["room"] is not None)
            self.assertEqual(state["payload"]["messages"], [])
            await owner.close()
            state = await receive_until(loser, lambda e: e["type"] == "state" and e["payload"]["room"] is None)
            self.assertFalse(any(r["id"] == room_id for r in state["payload"]["rooms"]))

    async def test_moderation_enforced_over_socket(self):
        async with connect(self.ws_url) as ws:
            await ws.recv()
            await command(ws, 'moderate', requestId='preview', scope='title', text='bully-test')
            reply = await receive_until(ws, lambda e: e['type'] == 'result')
            self.assertFalse(reply['allowed'])
            await command(ws, 'create', requestId='bypass', title='bully-test', allowed=True)
            reply = await receive_until(ws, lambda e: e['type'] == 'result')
            self.assertFalse(reply['ok'])
            await command(ws, 'create', requestId='offline', title='provider-offline')
            reply = await receive_until(ws, lambda e: e['type'] == 'result')
            self.assertFalse(reply['ok'])
            await command(ws, 'hello')
            state = await receive_until(ws, lambda e: e['type'] == 'state')
            self.assertIsNone(state['payload']['room'])

    async def test_new_preview_cancels_old_without_blocking_ping(self):
        async with connect(self.ws_url) as ws:
            await ws.recv()
            await command(ws, 'moderate', requestId='old', scope='title', text='slow-preview')
            await asyncio.sleep(.05)
            await command(ws, 'ping')
            self.assertEqual((await receive_until(ws, lambda e: e['type'] == 'pong'))['type'], 'pong')
            await command(ws, 'moderate', requestId='new', scope='title', text='safe new draft')
            old = await receive_until(ws, lambda e: e['type'] == 'result' and e['requestId'] == 'old')
            self.assertFalse(old['ok'])
            new = await receive_until(ws, lambda e: e['type'] == 'result' and e['requestId'] == 'new')
            self.assertTrue(new['allowed'])

    async def test_origin_validation(self):
        with self.assertRaises(InvalidStatus):
            async with connect(self.ws_url, origin="https://untrusted.example"):
                pass
        async with connect(self.ws_url, origin="http://localhost:5173") as ws:
            self.assertEqual(json.loads(await ws.recv())["type"], "state")

    async def test_invalid_json_and_oversized_frame(self):
        for payload in ["{", "x" * 17000]:
            async with connect(self.ws_url) as ws:
                await ws.recv()
                await ws.send(payload)
                with self.assertRaises(ConnectionClosed):
                    await ws.recv()


if __name__ == "__main__":
    unittest.main()
