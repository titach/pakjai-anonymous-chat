import { useEffect, useRef, useState } from "react";
import Icon from "../components/Icon";
import { useModeration } from "../hooks/useModeration";
import ModerationStatus from "../components/ModerationStatus";
export default function Chat({ room, messages, clientId, send, request }) {
  const [draft, setDraft] = useState("");
  const [confirmExit, setConfirmExit] = useState(false);
  const bottom = useRef(null);
  const dialog = useRef(null);
  const owner = room.ownerId === clientId;
  const connected = room.count === 2;
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const check = useModeration(draft, "message", request, connected);
  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "nearest" });
  }, [messages]);
  useEffect(() => {
    if (confirmExit) dialog.current.showModal();
  }, [confirmExit]);
  async function submit(event) {
    event.preventDefault();
    if (!check.allowed || !connected || submitting) return;
    setSubmitting(true);
    setSubmitError("");
    const reply = await request("message", { text: draft.trim() });
    if (reply.ok) setDraft("");
    else setSubmitError(reply.message);
    setSubmitting(false);
  }
  return (
    <main className="chat-page">
      <div className="chat-intro">
        <span className="eyebrow">A LITTLE SPACE FOR TWO</span>
        <p>ไม่ต้องรีบ ค่อย ๆ เล่า เรามีเวลาให้กัน</p>
      </div>
      <section className="chat-panel" aria-label="ห้องสนทนา">
        <header className="chat-header">
          <span className="room-icon">
            <Icon name="chat" />
          </span>
          <div className="room-info">
            <h1>{room.title}</h1>
            <span className="status">
              <span className="dot" />
              {connected ? "พร้อมคุยแล้ว" : "กำลังรอผู้เข้าร่วม"} · {room.count}
              /2 คน
            </span>
          </div>
          <button
            className="button exit-button"
            onClick={() => setConfirmExit(true)}
          >
            {owner ? "ปิดห้อง" : "ออกจากห้อง"}
          </button>
        </header>
        <div
          className="conversation"
          role="log"
          aria-label="ข้อความสนทนา"
          aria-live="polite"
          aria-relevant="additions text"
        >
          <p className="conversation-note">
            <Icon name="shield" /> เป็นพื้นที่ของคนแปลกหน้าสองคน
            คุยกันด้วยความเคารพนะ
          </p>
          {!messages.length && (
            <div className="chat-empty">
              <span className="feature-icon">
                <Icon name={connected ? "heart" : "chat"} />
              </span>
              <h2>
                {connected
                  ? "เริ่มด้วยคำว่า “สวัสดี” ก็ได้นะ"
                  : "เผื่อใครสักคน กำลังมองหาห้องนี้"}
              </h2>
              <p>
                {connected
                  ? "อีกคนเข้ามาแล้ว เริ่มบทสนทนาได้เลย"
                  : "หัวข้อของคุณแสดงอยู่ในหน้ารายการห้องแล้ว"}
              </p>
              {!connected && (
                <small>
                  เมื่อมีคนเลือกเข้าร่วมห้อง คุณจะเริ่มคุยกันได้ทันที
                </small>
              )}
            </div>
          )}
          {messages.map((message) => (
            <div
              key={message.id}
              className={`message-row ${message.senderId === clientId ? "mine" : ""}`}
            >
              <span className="message-author">
                {message.senderId === clientId ? "คุณ" : "คนแปลกหน้า"}
              </span>
              <div className="message-bubble">{message.text}</div>
              <time dateTime={new Date(message.at).toISOString()}>
                {new Date(message.at).toLocaleTimeString("th-TH", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </time>
            </div>
          ))}
          <div ref={bottom} />
        </div>
        <form className="composer" onSubmit={submit}>
          <label className="sr-only" htmlFor="message">
            ข้อความ
          </label>
          <textarea
            id="message"
            rows={2}
            maxLength={1000}
            value={draft}
            disabled={!connected || submitting}
            aria-describedby="message-moderation"
            onChange={(event) => {
              setDraft(event.target.value);
              setSubmitError("");
            }}
            onKeyDown={(event) => {
              if (
                event.key === "Enter" &&
                !event.shiftKey &&
                !event.nativeEvent.isComposing
              ) {
                event.preventDefault();
                submit(event);
              }
            }}
            placeholder={
              connected
                ? "พิมพ์สิ่งที่อยากเล่า…"
                : "รออีกคนเข้าร่วม แล้วเริ่มคุยกันได้เลย…"
            }
          />
          <button
            className="button primary send-button"
            disabled={!connected || !check.allowed || submitting}
            aria-label="ส่งข้อความ"
          >
            <Icon name="send" />
          </button>
          <span className="composer-hint">
            Enter เพื่อส่ง · Shift + Enter เพื่อขึ้นบรรทัดใหม่
          </span>
          <span className="char-count">{draft.length}/1000</span>
        </form>
        <div className="chat-moderation">
          <ModerationStatus id="message-moderation" check={check} />
          {submitting && <p role="status">กำลังส่งข้อความ…</p>}
          {submitError && (
            <p role="alert" className="error-text">
              {submitError}
            </p>
          )}
          <p className="moderation-disclosure">
            ข้อความที่พิมพ์จะส่งให้ AI for Thai ตรวจการรังแกก่อนส่งให้คู่สนทนา
          </p>
        </div>
      </section>
      <p className="chat-footnote">
        ข้อความอยู่ในหน่วยความจำชั่วคราว ไม่บันทึกลงฐานข้อมูล ·
        เมื่อผู้เข้าร่วมออก บทสนทนาจะถูกล้างก่อนรับคนใหม่
      </p>
      {confirmExit && (
        <dialog
          ref={dialog}
          className="modal"
          onCancel={() => setConfirmExit(false)}
        >
          <div className="modal-body">
            <h2>{owner ? "ปิดห้องสนทนานี้?" : "ออกจากบทสนทนานี้?"}</h2>
            <p className="muted">
              {owner
                ? "ห้องจะหายจากรายการ และข้อความของทั้งสองคนจะถูกลบ"
                : "ข้อความจะถูกล้าง และห้องจะเปิดรับคนใหม่"}
            </p>
            <div className="dialog-actions">
              <button
                className="button secondary"
                autoFocus
                onClick={() => setConfirmExit(false)}
              >
                คุยต่อ
              </button>
              <button className="button danger" onClick={() => send("leave")}>
                {owner ? "ยืนยันปิดห้อง" : "ยืนยันออกจากห้อง"}
              </button>
            </div>
          </div>
        </dialog>
      )}
    </main>
  );
}
