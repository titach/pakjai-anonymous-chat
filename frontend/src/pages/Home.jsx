import Icon from "../components/Icon";
export default function Home({ ready, count, onCreate, onBrowse }) {
  return (
    <>
      <section className="hero-section">
        <span className="eyebrow">
          <span className="dot" /> บางครั้ง แค่มีใครสักคนรับฟังก็พอ
        </span>
        <h1>
          คนแปลกหน้า
          <br />
          ที่อาจทำให้คุณ<span className="accent">สบายใจ</span>
        </h1>
        <p className="hero-description">
          ไม่ต้องรู้จักกันมาก่อน ไม่ต้องแนะนำตัว
          <br />
          เปิดห้องเล่าเรื่องของคุณ หรือเข้าไปเป็นผู้ฟังให้ใครสักคน
        </p>
        <div className="hero-decoration" aria-hidden="true">
          <span className="bubble one">วันนี้เป็นยังไงบ้าง?</span>
          <span className="bubble two">
            เล่าได้นะ เราฟังอยู่ <Icon name="heart" />
          </span>
          <span className="spark">✳</span>
        </div>
      </section>
      <section className="action-grid" aria-label="เริ่มต้นสนทนา">
        <article className="action-card create-card">
          <span className="card-number">01 / อยากเล่า</span>
          <span className="feature-icon">
            <Icon name="plus" />
          </span>
          <h2>สร้างห้องของคุณ</h2>
          <p>
            มีเรื่องในใจใช่ไหม? ตั้งหัวข้อที่อยากคุย
            <br />
            แล้วรอใครสักคนเข้ามารับฟัง
          </p>
          <button
            className="button primary"
            onClick={onCreate}
            disabled={!ready || count >= 100}
          >
            สร้างห้อง <Icon name="arrow" />
          </button>
          {count >= 100 && <small>ขณะนี้ครบ 100 ห้องแล้ว</small>}
        </article>
        <article className="action-card join-card">
          <span className="card-number">02 / อยากฟัง</span>
          <span className="feature-icon">
            <Icon name="chat" />
          </span>
          <h2>เข้าร่วมห้องสนทนา</h2>
          <p>
            เลือกเรื่องที่คุณอยากคุย
            <br />
            บางคนอาจกำลังรอคุณอยู่พอดี
          </p>
          <button className="button secondary" onClick={onBrowse}>
            เลือกห้องสนทนา <Icon name="arrow" />
          </button>
        </article>
      </section>
      <section className="principles" aria-label="เกี่ยวกับพื้นที่นี้">
        <div>
          <Icon name="users" />
          <span>
            <strong>แค่เราสองคน</strong>พื้นที่สนทนาแบบ 1 ต่อ 1
          </span>
        </div>
        <div>
          <Icon name="shield" />
          <span>
            <strong>เป็นคนแปลกหน้าได้เต็มที่</strong>ไม่ต้องมีบัญชีหรือรหัสห้อง
          </span>
        </div>
        <div>
          <Icon name="heart" />
          <span>
            <strong>คุยด้วยความเข้าใจ</strong>รับฟังและเคารพกันเสมอ
          </span>
        </div>
      </section>
      <p className="home-caption">
        ทุกความรู้สึกมีที่ว่างตรงนี้ <span aria-hidden="true">✳</span>
      </p>
    </>
  );
}
