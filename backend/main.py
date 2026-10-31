"""Run from project root: python -m uvicorn backend.main:app --port 8000."""

import asyncio
from contextlib import asynccontextmanager
import json
import os
from urllib.parse import urlsplit

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

if __package__:
    from .chat import ChatManager
    from .moderation import BullyingModerator
    from .commands import dispatch
else:
    from chat import ChatManager
    from moderation import BullyingModerator
    from commands import dispatch

MAX_FRAME_BYTES = 16384
IDLE_TIMEOUT = 120


@asynccontextmanager
async def lifespan(app):
    app.state.chat = ChatManager()
    app.state.moderator = BullyingModerator.from_env()
    yield
    for client in app.state.chat.clients.values():
        client.stopped.set()
    app.state.chat.rooms.clear()
    app.state.chat.clients.clear()
    await app.state.moderator.close()


app = FastAPI(title="Pakjai Chat API", version="1.0.0", lifespan=lifespan)


def allowed_origin(websocket):
    origin = websocket.headers.get("origin")
    if not origin:
        # Non-browser clients, including integration tests; no cookie auth exists.
        return True
    try:
        parsed = urlsplit(origin)
    except ValueError:
        return False
    if (
        parsed.scheme not in ("http", "https")
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        return False
    if parsed.netloc == websocket.headers.get("host"):
        return True
    allowed = {
        item.strip()
        for item in os.getenv(
            "CHAT_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if item.strip()
    }
    return origin in allowed


@app.get("/api/health")
async def health():
    return {"status": "ok", "storage": "memory", "maxRooms": 100}


@app.get("/api/rooms")
async def rooms():
    return {"rooms": app.state.chat.room_list(), "maxRooms": 100}


async def read_commands(websocket, manager, client):
    preview = None
    try:
        while True:
            packet = await asyncio.wait_for(websocket.receive(), timeout=IDLE_TIMEOUT)
            if packet["type"] == "websocket.disconnect":
                return
            raw = packet.get("text")
            if raw is None:
                await websocket.close(code=1003, reason="Text JSON required")
                return
            if len(raw.encode("utf-8")) > MAX_FRAME_BYTES:
                await websocket.close(code=1009, reason="Message too large")
                return
            try:
                data = json.loads(raw)
            except (ValueError, RecursionError):
                await websocket.close(code=1007, reason="Invalid JSON")
                return
            if isinstance(data, dict) and data.get('type') == 'moderate':
                # New drafts supersede old drafts; never build an API request backlog.
                if preview:
                    if not preview.done():
                        preview.cancel()
                        manager.emit(client, {'type': 'result', 'requestId': preview_id,
                                             'ok': False, 'message': 'ข้อความเปลี่ยนแล้ว'})
                    await asyncio.gather(preview, return_exceptions=True)
                preview_id = data.get('requestId')
                preview = asyncio.create_task(dispatch(manager, client, data, app.state.moderator))
            else:
                await dispatch(manager, client, data, app.state.moderator)
    finally:
        if preview:
            preview.cancel()
            await asyncio.gather(preview, return_exceptions=True)


async def write_events(websocket, client):
    while True:
        event = await client.outbox.get()
        await asyncio.wait_for(websocket.send_json(event), timeout=10)


@app.websocket("/api/ws")
async def chat_socket(websocket: WebSocket):
    if not allowed_origin(websocket):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    manager = app.state.chat
    client = manager.connect()
    if client is None:
        await websocket.close(code=1013, reason="Server is full")
        return
    tasks = [
        asyncio.create_task(read_commands(websocket, manager, client)),
        asyncio.create_task(write_events(websocket, client)),
        asyncio.create_task(client.stopped.wait()),
    ]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except (WebSocketDisconnect, asyncio.TimeoutError, OSError, RuntimeError):
        pass
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        manager.disconnect(client)
        try:
            await websocket.close()
        except (WebSocketDisconnect, RuntimeError, OSError):
            pass


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        ws_max_size=16384,
        access_log=False,
    )
