"""Ephemeral room state. Call on ONE asyncio event loop / ONE server worker.

Mutations contain no await: checking capacity and assigning the guest are atomic
relative to other connections on that loop. Network I/O runs in per-client writers.
"""
import asyncio
from collections import deque
from dataclasses import dataclass, field
import time
from uuid import uuid4

MAX_ROOMS = 100
MAX_MESSAGES = 300
MAX_CLIENTS = 500


@dataclass
class Client:
    id: str = field(default_factory=lambda: str(uuid4()))
    room_id: str | None = None
    outbox: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=32))
    stopped: asyncio.Event = field(default_factory=asyncio.Event)
    commands: deque = field(default_factory=deque)
    moderations: deque = field(default_factory=deque)


@dataclass
class Room:
    title: str
    owner_id: str
    id: str = field(default_factory=lambda: str(uuid4()))
    guest_id: str | None = None
    messages: list = field(default_factory=list)

    def public(self):
        return {"id": self.id, "title": self.title, "ownerId": self.owner_id,
                "count": 2 if self.guest_id else 1}


class ChatManager:
    def __init__(self):
        self.clients: dict[str, Client] = {}
        self.rooms: dict[str, Room] = {}

    def connect(self):
        if len(self.clients) >= MAX_CLIENTS:
            return None
        client = Client()
        self.clients[client.id] = client
        self.state(client)
        return client

    def emit(self, client, event):
        if client.stopped.is_set():
            return
        try:
            client.outbox.put_nowait(event)
        except asyncio.QueueFull:
            # A slow client must not hold up everybody else or grow RAM forever.
            client.stopped.set()

    def error(self, client, message):
        self.emit(client, {"type": "error", "message": message})

    def notice(self, client_id, message):
        if client := self.clients.get(client_id):
            self.emit(client, {"type": "notice", "message": message})

    def room_list(self):
        return [room.public() for room in self.rooms.values()]

    def state(self, client, room_list=None):
        room = self.rooms.get(client.room_id)
        self.emit(client, {"type": "state", "payload": {
            "clientId": client.id,
            "rooms": self.room_list() if room_list is None else room_list,
            "room": room.public() if room else None,
            # Copy the list so queued events cannot change before serialization.
            "messages": list(room.messages) if room else [],
        }})

    def broadcast(self):
        rooms = self.room_list()
        for client in self.clients.values():
            self.state(client, rooms)

    def leave(self, client):
        room = self.rooms.get(client.room_id)
        client.room_id = None
        if not room:
            return
        if room.owner_id == client.id:
            if guest := self.clients.get(room.guest_id):
                guest.room_id = None
                self.notice(guest.id, "ผู้สร้างปิดห้องแล้ว บทสนทนาถูกลบ คุณเลือกห้องใหม่ได้เลย")
            del self.rooms[room.id]
        elif room.guest_id == client.id:
            room.guest_id = None
            room.messages.clear()
            self.notice(room.owner_id, "อีกคนออกจากห้องแล้ว ล้างบทสนทนาแล้ว และกำลังรอผู้เข้าร่วมคนใหม่")

    def disconnect(self, client):
        if self.clients.pop(client.id, None) is None:
            return
        had_room = client.room_id is not None
        self.leave(client)
        client.stopped.set()
        if had_room:
            self.broadcast()

    def handle(self, client, data):
        if client.id not in self.clients or client.stopped.is_set():
            return
        if not isinstance(data, dict) or not isinstance(data.get("type"), str):
            return self.error(client, "รูปแบบคำสั่งไม่ถูกต้อง")
        kind = data["type"]
        now = time.monotonic()
        while client.commands and now - client.commands[0] >= 10:
            client.commands.popleft()
        if len(client.commands) >= 30:
            return self.error(client, "ส่งคำสั่งถี่เกินไป กรุณารอสักครู่")
        client.commands.append(now)
        if kind == "ping":
            self.emit(client, {"type": "pong"})
            return
        if kind == "hello":
            return self.state(client)
        if kind == "create":
            if client.room_id:
                return self.error(client, "คุณอยู่ในห้องแล้ว กรุณาออกจากห้องเดิมก่อน")
            if len(self.rooms) >= MAX_ROOMS:
                return self.error(client, "ขณะนี้ครบ 100 ห้องแล้ว กรุณารอให้มีห้องปิดก่อน")
            title = data.get("title")
            if not isinstance(title, str) or not 1 <= len(title.strip()) <= 80:
                return self.error(client, "กรุณาใส่ชื่อห้อง 1–80 ตัวอักษร")
            room = Room(title=title.strip(), owner_id=client.id)
            self.rooms[room.id] = room
            client.room_id = room.id
        elif kind == "join":
            if client.room_id:
                return self.error(client, "คุณอยู่ในห้องแล้ว กรุณาออกจากห้องเดิมก่อน")
            room_id = data.get("roomId")
            room = self.rooms.get(room_id) if isinstance(room_id, str) else None
            if not room:
                return self.error(client, "ห้องนี้ปิดไปแล้ว กรุณาเลือกห้องใหม่")
            if room.guest_id:
                return self.error(client, "มีคนเข้าร่วมห้องนี้แล้ว กรุณาเลือกห้องอื่น")
            room.guest_id = client.id
            client.room_id = room.id
        elif kind == "message":
            # Never trust roomId/senderId supplied in the incoming payload.
            room = self.rooms.get(client.room_id)
            if not room or client.id not in (room.owner_id, room.guest_id):
                return self.error(client, "คุณยังไม่ได้เข้าร่วมห้อง")
            if not room.guest_id:
                return self.error(client, "กรุณารอผู้เข้าร่วมก่อนส่งข้อความ")
            text = data.get("text")
            if not isinstance(text, str) or not 1 <= len(text.strip()) <= 1000:
                return self.error(client, "ข้อความต้องมีความยาว 1–1,000 ตัวอักษร")
            message = {"id": str(uuid4()), "senderId": client.id,
                       "text": text.strip(), "at": int(time.time() * 1000)}
            room.messages.append(message)
            del room.messages[:-MAX_MESSAGES]
            # Message traffic is sent only to the two participants, not the lobby.
            for member_id in (room.owner_id, room.guest_id):
                if member := self.clients.get(member_id):
                    self.emit(member, {"type": "message", "message": message})
            return True
        elif kind == "leave":
            self.leave(client)
        else:
            return self.error(client, "ไม่รู้จักคำสั่งนี้")
        self.broadcast()
        return True
