/* global onconnect */
// Browser-only prototype: all state is ephemeral, shared only by same-origin tabs.
// FastAPI must enforce these rules independently for actual multi-device use.
const clients = new Map();
const rooms = new Map();
function post(client, data) {
  try {
    client.port.postMessage(data);
  } catch {
    /* Heartbeat cleanup handles closed ports. */
  }
}
function publicRoom(room) {
  return {
    id: room.id,
    title: room.title,
    ownerId: room.ownerId,
    count: room.guestId ? 2 : 1,
  };
}
function broadcast() {
  const list = [...rooms.values()].map(publicRoom);
  for (const client of clients.values()) {
    const room = rooms.get(client.roomId);
    post(client, {
      type: "state",
      payload: {
        clientId: client.id,
        rooms: list,
        room: room ? publicRoom(room) : null,
        messages: room?.messages || [],
      },
    });
  }
}
function notice(clientId, message) {
  const client = clients.get(clientId);
  if (client) post(client, { type: "notice", message });
}
function leave(client) {
  const room = rooms.get(client.roomId);
  if (!room) return;
  if (room.ownerId === client.id) {
    const guest = clients.get(room.guestId);
    if (guest) guest.roomId = null;
    notice(
      room.guestId,
      "ผู้สร้างปิดห้องแล้ว บทสนทนาถูกลบ คุณเลือกห้องใหม่ได้เลย",
    );
    rooms.delete(room.id);
  } else {
    room.guestId = null;
    room.messages = [];
    notice(
      room.ownerId,
      "อีกคนออกจากห้องแล้ว ล้างบทสนทนาแล้ว และกำลังรอผู้เข้าร่วมคนใหม่",
    );
  }
  client.roomId = null;
}
onconnect = (event) => {
  const port = event.ports[0];
  const client = {
    id: crypto.randomUUID(),
    port,
    roomId: null,
    lastSeen: Date.now(),
  };
  clients.set(client.id, client);
  port.onmessage = ({ data }) => {
    if (!clients.has(client.id)) {
      post(client, {
        type: "error",
        message: "เซสชันหมดอายุ กรุณารีเฟรชหน้าเว็บเพื่อเริ่มใหม่",
      });
      return;
    }
    client.lastSeen = Date.now();
    const fail = (message) => post(client, { type: "error", message });
    if (data.type === "ping") return;
    if (data.type === "create") {
      if (client.roomId)
        return fail("คุณอยู่ในห้องแล้ว กรุณาออกจากห้องเดิมก่อน");
      if (rooms.size >= 100)
        return fail("ขณะนี้ครบ 100 ห้องแล้ว กรุณารอให้มีห้องปิดก่อน");
      const title = typeof data.title === "string" ? data.title.trim() : "";
      if (!title || title.length > 80)
        return fail("กรุณาใส่ชื่อห้อง 1–80 ตัวอักษร");
      const room = {
        id: crypto.randomUUID(),
        title,
        ownerId: client.id,
        guestId: null,
        messages: [],
      };
      rooms.set(room.id, room);
      client.roomId = room.id;
    } else if (data.type === "join") {
      if (client.roomId)
        return fail("คุณอยู่ในห้องแล้ว กรุณาออกจากห้องเดิมก่อน");
      const room = rooms.get(data.roomId);
      if (!room) return fail("ห้องนี้ปิดไปแล้ว กรุณาเลือกห้องใหม่");
      if (room.guestId)
        return fail("มีคนเข้าร่วมห้องนี้แล้ว กรุณาเลือกห้องอื่น");
      room.guestId = client.id;
      client.roomId = room.id;
    } else if (data.type === "message") {
      const room = rooms.get(client.roomId);
      if (!room || !room.guestId)
        return fail("กรุณารอผู้เข้าร่วมก่อนส่งข้อความ");
      const text = typeof data.text === "string" ? data.text.trim() : "";
      if (!text || text.length > 1000)
        return fail("ข้อความต้องมีความยาว 1–1,000 ตัวอักษร");
      room.messages.push({
        id: crypto.randomUUID(),
        senderId: client.id,
        text,
        at: Date.now(),
      });
      if (room.messages.length > 300) room.messages.shift();
    } else if (data.type === "leave" || data.type === "disconnect") {
      leave(client);
      if (data.type === "disconnect") clients.delete(client.id);
    }
    broadcast();
  };
  port.start();
};
setInterval(() => {
  let changed = false;
  for (const client of clients.values()) {
    if (Date.now() - client.lastSeen > 120000) {
      leave(client);
      clients.delete(client.id);
      changed = true;
    }
  }
  if (changed) broadcast();
}, 15000);
