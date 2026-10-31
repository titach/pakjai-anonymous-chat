import { useState } from "react";
import Icon from "../components/Icon";
export default function Rooms({ rooms, ready, onBack, onCreate, onJoin }) {
  const [query, setQuery] = useState("");
  const [availableOnly, setAvailableOnly] = useState(false);
  const filtered = rooms.filter(
    (room) =>
      room.title
        .toLocaleLowerCase()
        .includes(query.trim().toLocaleLowerCase()) &&
      (!availableOnly || room.count < 2),
  );
  return (
    <section className="rooms-page">
      <button className="text-button back-button" onClick={onBack}>
        ← กลับหน้าหลัก
      </button>
      <div className="page-heading">
        <div>
          <span className="eyebrow">FIND YOUR CONVERSATION</span>
          <h1>เลือกเรื่องที่อยากคุย</h1>
          <p className="muted">หนึ่งห้อง สองคน และบทสนทนาที่เริ่มต้นได้เลย</p>
        </div>
        <button
          className="button primary"
          onClick={onCreate}
          disabled={!ready || rooms.length >= 100}
        >
          <Icon name="plus" /> สร้างห้อง
        </button>
      </div>
      <div className="room-toolbar">
        <label className="search-field">
          <Icon name="search" />
          <input
            aria-label="ค้นหาหัวข้อห้อง"
            placeholder="ค้นหาเรื่องที่อยากคุย…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <label className="filter">
          <input
            type="checkbox"
            checked={availableOnly}
            onChange={(event) => setAvailableOnly(event.target.checked)}
          />{" "}
          เฉพาะห้องว่าง
        </label>
      </div>
      <div className="list-caption">
        <span>
          ห้องสนทนา <strong>{rooms.length}</strong> / 100 ห้อง
        </span>
        <span>
          <span className="dot" /> ว่าง{" "}
          {rooms.filter((room) => room.count < 2).length} ห้อง
        </span>
      </div>
      {filtered.length ? (
        <div className="room-list">
          {filtered.map((room) => (
            <article className="room-card" key={room.id}>
              <span
                className={`room-icon ${room.count === 2 ? "is-full" : ""}`}
              >
                <Icon name="chat" />
              </span>
              <div className="room-info">
                <h2>{room.title}</h2>
                <span className={`status ${room.count === 2 ? "full" : ""}`}>
                  <span className="dot" />
                  {room.count === 2 ? "ห้องเต็ม" : "ห้องว่าง"} · {room.count}/2
                  คน
                </span>
              </div>
              <button
                className="button secondary"
                disabled={!ready || room.count === 2}
                onClick={() => onJoin(room.id)}
              >
                {room.count === 2 ? "ห้องเต็ม" : "เข้าร่วมห้อง"}
                {room.count < 2 && <Icon name="arrow" />}
              </button>
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <span className="feature-icon">
            <Icon name="chat" />
          </span>
          <h2>
            {rooms.length
              ? "ยังไม่พบห้องที่ตรงกัน"
              : "บทสนทนาแรก อาจเริ่มจากคุณ"}
          </h2>
          <p>
            {rooms.length
              ? "ลองเปลี่ยนคำค้น หรือดูห้องทั้งหมดอีกครั้ง"
              : "ยังไม่มีห้องในตอนนี้ ลองสร้างห้องเพื่อเริ่มบทสนทนาแรก"}
          </p>
          {!rooms.length && (
            <button
              className="button primary"
              onClick={onCreate}
              disabled={!ready}
            >
              สร้างห้องแรก <Icon name="plus" />
            </button>
          )}
        </div>
      )}
    </section>
  );
}
