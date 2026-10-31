# พักใจ — FastAPI backend

## เริ่มใช้งาน

เปิด terminal แรก จาก root ของโปรเจกต์:

```powershell
cd 'D:\อิมมี่\python\web-mini-project'
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --ws-max-size 16384 --no-access-log
```

เปิด terminal ที่สอง:

```powershell
cd 'D:\อิมมี่\python\web-mini-project\frontend'
npm run dev
```

เข้า URL ของ Vite (ปกติ http://localhost:5173) แล้วเปิดสองแท็บหรือสองเบราว์เซอร์เพื่อสร้างห้องและเข้าร่วม
main.py ใช้ package import จึงต้องรัน backend.main:app จาก root ตามคำสั่งนี้
เพิ่ม --reload ได้ระหว่างพัฒนา แต่ทุกครั้งที่ reload ห้องและบทสนทนาจะหาย
หากตั้งสภาพแวดล้อมใหม่ ติดตั้งด้วย `.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt`

## ทดลองจากคนละเครื่องใน Wi-Fi/LAN เดียวกัน

รัน backend ตามเดิม แล้วเปิด frontend ด้วย `npm run dev -- --host 0.0.0.0`
เครื่องอื่นเข้า `http://<IP ของเครื่องเซิร์ฟเวอร์>:5173` โดยทุกคนต้องใช้เซิร์ฟเวอร์เดียวกัน
Vite ส่ง /api และ WebSocket ไป backend จึงไม่จำเป็นต้องเปิดพอร์ต 8000 ออกสู่ LAN
หาก Windows Firewall บล็อก ต้องอนุญาตพอร์ต frontend สำหรับเครือข่ายที่ต้องการเอง งานนี้ไม่ได้แก้ firewall หรือเปิด public hosting
หาก deploy บนอินเทอร์เน็ต ต้องมี HTTPS และ reverse proxy ที่ส่ง /api/ws แบบ WebSocket ไป backend

## API

- GET /api/health: สถานะเซิร์ฟเวอร์และชนิด storage
- GET /api/rooms: รายชื่อห้องและจำนวนสมาชิก ไม่มีข้อความสนทนา
- WS /api/ws: หนึ่ง connection = ผู้ใช้ชั่วคราวหนึ่งคน backend ออก clientId เอง
- GET /docs: เอกสาร HTTP API (WebSocket protocol ดูด้านล่าง)

Frontend รับรายการห้องเริ่มต้นและ updates ผ่าน WebSocket ไม่ polling HTTP

### คำสั่ง JSON

```json
{"type":"create","title":"ต้องการคนรับฟัง"}
{"type":"join","roomId":"ID จากรายการห้อง"}
{"type":"message","text":"สวัสดี"}
{"type":"leave"}
{"type":"ping"}
{"type":"hello"}
```

leave ของเจ้าของ = ปิดห้อง; leave ของ guest = ออกและล้างข้อความ
ไม่ต้องกรอกรหัสห้อง ผู้ใช้เลือกจากรายการ backend ไม่เชื่อ senderId หรือ roomId ที่ส่งมาในคำสั่ง message

### เหตุการณ์ตอบกลับ

- state: payload มี clientId, rooms, room (หรือ null), messages
- message: message มี id, senderId, text, at (Unix milliseconds); ส่งเฉพาะสมาชิกห้อง
- notice: แจ้งการออก/ปิดห้อง
- error: ข้อความ validation หรือ rate limit
- pong: ตอบ heartbeat

## กติกาและวงจรข้อมูล

- ไม่ใช้ database, cookies หรือบัญชี ทุกอย่างอยู่ใน RAM ของ Python process
- ไม่เกิน 100 ห้อง ห้องละ 2 คน ผู้เชื่อมต่อรวมไม่เกิน 500 คน (รวมคนดูรายการ)
- ชื่อห้อง 1–80 ตัวอักษร ข้อความ 1–1,000 ตัวอักษร หลัง trim
- เก็บ 300 ข้อความล่าสุดต่อห้อง แอปไม่เขียนข้อความสนทนาลง log
- guest ออก/หลุด: ล้างข้อความ เปิดรับคนใหม่; owner ออก/หลุด: ลบห้องและแจ้ง guest
- ห้องเต็มปฏิเสธคนที่สาม แม้กดเข้าพร้อมกัน
- จำกัด 30 คำสั่งต่อ 10 วินาทีต่อ connection; outbound queue 32 events หากรับไม่ทันจะตัด connection เพื่อจำกัด RAM
- ไม่ได้รับ heartbeat/คำสั่ง 120 วินาทีจะตัด connection; frontend ping ทุก 15 วินาที และลองเชื่อมใหม่สูงสุดห่างกัน 10 วินาที
- การเชื่อมใหม่เป็น session ใหม่ ไม่คืนห้อง/ประวัติ แท็บถูกพักหรือเครื่อง sleep อาจทำให้หลุด
- JSON ผิดรูปแบบ/เฟรมใหญ่เกิน 16 KiB จะตัด connection
- ตรวจ Origin: อนุญาต origin เดียวกับ Host หรือ CHAT_ALLOWED_ORIGINS (ค่าเริ่มต้น http://localhost:5173 และ http://127.0.0.1:5173); non-browser client ที่ไม่มี Origin เชื่อมได้

หาก frontend อยู่คนละ origin ตั้งค่า allowlist ก่อนเริ่มเซิร์ฟเวอร์:

```powershell
$env:CHAT_ALLOWED_ORIGINS = 'https://your-frontend.example'
```

**ใช้ Uvicorn 1 worker / 1 instance เท่านั้น** เพราะ RAM ไม่แชร์ระหว่าง process
แก้ไขกติกาห้องแบบ synchronous บน event loop เดียว ไม่มี await คั่นระหว่างตรวจที่ว่างและกำหนด guest ส่วน network writes แยกเป็น task ต่อ client
เหมาะกับ mini project; ถ้าเปิด public ขนาดใหญ่ ต้องเพิ่มการจำกัด connection/IP และปรับ deployment ตามการใช้งานจริง

## ทดสอบ

```powershell
cd 'D:\อิมมี่\python\web-mini-project'
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
```

ใช้ unittest และ websockets ที่มีอยู่แล้ว Integration เริ่ม Uvicorn บนพอร์ตชั่วคราวและปิดเอง ไม่ชนพอร์ต 8000
ครอบคลุม HTTP, WebSocket, join พร้อมกัน, แยกข้อความ, disconnect, validation, 100 ห้อง, 2 คน, ขีดจำกัดข้อความ, rate limit, slow consumer และ Origin

## ตรวจการรังแกด้วย AI for Thai

backend/moderation.py อ่าน API_KEY และ SERVICE_URL จากไฟล์ .env ที่ root โดยอ้าง path จากตำแหน่งไฟล์ จึงใช้ run.cmd และ python backend/main.py ได้เหมือนเดิม ไม่ต้องย้าย .env และห้ามนำ API key ไปใส่ VITE_* หรือ frontend
ใช้ httpx async ส่ง form field text และ header Apikey ไป SERVICE_URL โดยไม่ส่งข้อความหรือ API key ลง log
เอกสารประเภทผลลัพธ์: https://v1.aiforthai.in.th/service_sa.php (0 = ทั่วไป, 1–6 = ประเภทการรังแก)
API จริงตอบ bully_type เป็น 0 สำหรับข้อความทั่วไป และอาจเป็น list เช่น [4] เมื่อพบการรังแก; รองรับค่าเดี่ยวและ list โดยทุกค่าต้องรู้จัก ห้ามตีความ response ผิดรูปแบบว่าอนุญาต

Frontend ส่งผ่าน WebSocket เดิม ไม่ส่ง API key ไปเบราว์เซอร์:

```json
{"type":"moderate","scope":"title","text":"หัวข้อห้อง","requestId":"unique-id"}
{"type":"moderate","scope":"message","text":"ข้อความ","requestId":"unique-id"}
```

ตอบ type=result พร้อม requestId, ok และ allowed; create/message ใช้ requestId ได้เช่นกัน โดย backend ตรวจอีกครั้งก่อน commit และตอบ ok หลัง commit เท่านั้น
คำสั่ง create/message ที่ส่งตรงโดยไม่ preview ก็ต้องผ่าน moderation เช่นกัน ไม่เชื่อ allowed จาก frontend
ส่วน ChatManager.handle เป็น synchronous state engine ภายใน ต้องเรียกผ่าน commands.dispatch สำหรับ input จาก network เสมอ
หลังรอ API ต้องตรวจสมาชิกและความจุห้องใหม่ ป้องกันข้อความเดิมถูกส่งไปยัง guest คนใหม่

- หยุดพิมพ์ 650ms แล้วตรวจ; request ใหม่ยกเลิก preview เก่า ไม่สะสมคิว
- ขณะตรวจ/ถูกบล็อก/ตรวจไม่สำเร็จ ปิดปุ่มสร้างและส่ง รวมถึง Enter
- API ล่ม/timeout/key ผิด/quota หมด: ปฏิเสธ create/message และให้ผู้ใช้ลองใหม่ ไม่ปล่อยข้อความที่ยังตรวจไม่ได้
- กดส่งแล้วเก็บ draft ไว้จน backend ยืนยันสำเร็จ; หากถูกปฏิเสธ draft ยังอยู่
- จำกัด moderation 20 ครั้ง/10 วินาทีต่อ connection และเรียก provider พร้อมกันสูงสุด 8 ครั้ง
- เวลาเชื่อมต่อ provider 8 วินาที รวมรอคิวไม่เกิน 10 วินาที
- cache ผลตรวจไม่เกิน 256 รายการ 30 วินาที เก็บเฉพาะ salted digest + verdict ไม่มีข้อความดิบ ใช้ผลเดียวกันได้เมื่อ preview แล้วส่งทันที
- ข้อความที่กำลังพิมพ์จะถูกส่งให้ผู้ให้บริการ AI for Thai แม้ยังไม่ได้กดส่ง; UI มีข้อความแจ้งไว้ ผลการจำแนกอาจมี false positive/false negative
- เว็บไซต์เองยังไม่ใช้ database แต่ไม่รับรองนโยบายการเก็บข้อมูลของผู้ให้บริการภายนอก

ติดตั้ง dependencies เพิ่มเมื่อย้ายเครื่อง: python -m pip install -r backend/requirements.txt
ชุดทดสอบใช้ local fake provider และ httpx.MockTransport เพื่อไม่ใช้ API key/quota จริง และไม่มีตัวเลือกปิด moderation ใน production
