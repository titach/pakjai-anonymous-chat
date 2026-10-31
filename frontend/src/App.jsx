import { useState } from "react";
import { useChat } from "./hooks/useChat";
import Home from "./pages/Home";
import Rooms from "./pages/Rooms";
import Chat from "./pages/Chat";
import CreateRoomDialog from "./components/CreateRoomDialog";
import Icon from "./components/Icon";
import "./App.css";

export default function App() {
  const chat = useChat();
  const [page, setPage] = useState("home");
  const [creating, setCreating] = useState(false);
  return (
    <div className="app-shell">
      <header className="site-header">
        <button
          className="brand"
          onClick={() => !chat.room && setPage("home")}
          aria-label="พักใจ หน้าหลัก"
        >
          <span className="brand-icon">
            <Icon name="chat" />
          </span>
          <span>
            พักใจ<span className="brand-sub">พื้นที่เล็ก ๆ สำหรับบทสนทนา</span>
          </span>
        </button>
        <span className="anonymous-label">
          <Icon name="shield" /> ไม่ต้องบอกชื่อ ก็เล่าได้
        </span>
      </header>
      <div className="demo-banner">
        <span className="dot" />
        {chat.ready
          ? "เชื่อมต่อแล้ว · ห้องและบทสนทนาอัปเดตแบบเรียลไทม์"
          : "กำลังเชื่อมต่อเซิร์ฟเวอร์…"}
      </div>
      {chat.error && (
        <div className="notice error" role="alert">
          {chat.error}
          <button className="text-button" onClick={chat.clearError}>
            ปิดข้อความ
          </button>
        </div>
      )}
      {chat.notice && (
        <div className="notice" role="status">
          {chat.notice}
          <button className="text-button" onClick={chat.clearNotice}>
            รับทราบ
          </button>
        </div>
      )}
      {!chat.ready && !chat.error && (
        <p className="loading" role="status">
          กำลังเตรียมพื้นที่สนทนา…
        </p>
      )}
      {chat.room ? (
        <Chat
          key={chat.room.id}
          room={chat.room}
          messages={chat.messages}
          clientId={chat.clientId}
          send={chat.send}
          request={chat.request}
        />
      ) : (
        <main>
          {page === "home" ? (
            <Home
              ready={chat.ready}
              count={chat.rooms.length}
              onCreate={() => setCreating(true)}
              onBrowse={() => setPage("rooms")}
            />
          ) : (
            <Rooms
              rooms={chat.rooms}
              ready={chat.ready}
              onBack={() => setPage("home")}
              onCreate={() => setCreating(true)}
              onJoin={(roomId) => chat.send("join", { roomId })}
            />
          )}
        </main>
      )}
      <footer className="site-footer">
        <span>พักใจ — ให้ทุกเรื่องราวมีคนรับฟัง</span>
        <span>ไม่สมัครสมาชิก · ไม่ใช้รหัสห้อง · ไม่บันทึกลงฐานข้อมูล</span>
      </footer>
      {creating && !chat.room && (
        <CreateRoomDialog
          count={chat.rooms.length}
          request={chat.request}
          onClose={() => setCreating(false)}
          onCreate={async (title) => {
            const reply = await chat.request("create", { title });
            if (reply.ok) setCreating(false);
            return reply;
          }}
        />
      )}
    </div>
  );
}
