import { useEffect, useRef, useState } from "react";
import Icon from "./Icon";
import { useModeration } from "../hooks/useModeration";
import ModerationStatus from "./ModerationStatus";
export default function CreateRoomDialog({
  count,
  onClose,
  onCreate,
  request,
}) {
  const ref = useRef(null);
  const [title, setTitle] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const check = useModeration(title, "title", request);
  const full = count >= 100;
  useEffect(() => {
    const dialog = ref.current;
    dialog.showModal();
    return () => dialog.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className="modal"
      onCancel={onClose}
      onClick={(event) => {
        if (event.target === ref.current) onClose();
      }}
    >
      <div className="modal-body">
        <button
          className="icon-button modal-close"
          aria-label="ปิดหน้าสร้างห้อง"
          onClick={onClose}
        >
          <Icon name="close" />
        </button>
        <span className="feature-icon">
          <Icon name="plus" />
        </span>
        <h2>วันนี้อยากคุยเรื่องอะไร?</h2>
        <p className="muted">ตั้งหัวข้อให้คนที่อยากรับฟังหาคุณเจอ</p>
        <form
          onSubmit={async (event) => {
            event.preventDefault();
            if (!check.allowed || full || submitting) return;
            setSubmitting(true);
            setSubmitError("");
            const reply = await onCreate(title.trim());
            if (!reply.ok) setSubmitError(reply.message);
            setSubmitting(false);
          }}
        >
          <label htmlFor="room-title">ชื่อห้อง / หัวข้อสนทนา</label>
          <input
            id="room-title"
            autoFocus
            value={title}
            disabled={submitting}
            aria-describedby="title-moderation"
            onChange={(event) => {
              setTitle(event.target.value);
              setSubmitError("");
            }}
            maxLength={80}
            placeholder="เช่น ต้องการคนรับฟังด่วน"
            required
          />
          <div className="field-note">
            <span>ใช้หัวข้อแทนข้อมูลส่วนตัว</span>
            <span>{title.length}/80</span>
          </div>
          <div className="gentle-note">
            <Icon name="users" />
            <span>
              ห้องนี้มีที่สำหรับคุณและผู้ฟังอีก 1 คน
              <br />
              เมื่อคุณปิดห้อง บทสนทนาจะถูกลบ
            </span>
          </div>
          <p className="moderation-disclosure">
            ชื่อห้องที่พิมพ์จะส่งให้ AI for Thai ตรวจการรังแกก่อนใช้งาน
          </p>
          <ModerationStatus id="title-moderation" check={check} />
          {submitError && (
            <p role="alert" className="error-text">
              {submitError}
            </p>
          )}
          {full && (
            <p className="error-text" role="alert">
              ครบ 100 ห้องแล้ว กรุณารอให้มีห้องปิดก่อน
            </p>
          )}
          <button
            className="button primary full-width"
            disabled={full || !check.allowed || submitting}
          >
            {submitting ? "กำลังสร้างห้อง…" : "สร้างห้องและรอคนเข้าร่วม"}{" "}
            <Icon name="arrow" />
          </button>
        </form>
      </div>
    </dialog>
  );
}
