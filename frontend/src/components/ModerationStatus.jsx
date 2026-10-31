export default function ModerationStatus({ check, id }) {
  return (
    <div
      id={id}
      className={`moderation-status ${check.status}`}
      role="status"
      aria-live="polite"
    >
      {check.status === "checking" && "กำลังตรวจข้อความ…"}
      {check.status === "allowed" && "ตรวจข้อความแล้ว พร้อมใช้งาน"}
      {(check.status === "blocked" || check.status === "error") &&
        check.message}
      {check.status === "error" && (
        <button type="button" className="text-button" onClick={check.retry}>
          ลองตรวจใหม่
        </button>
      )}
    </div>
  );
}
