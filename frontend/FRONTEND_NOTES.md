
## การตรวจข้อความก่อนสร้าง/ส่ง

ใช้ hook useModeration และ component ModerationStatus ร่วมกันทั้งชื่อห้องและ draft แชท
useChat.request ส่งคำสั่งผ่าน WebSocket พร้อม requestId และรอ type=result
API key อยู่ backend เท่านั้น ไม่มี fetch ไป AI for Thai โดยตรงจาก browser
หลังหยุดพิมพ์ 650ms จึงตรวจ ข้อความที่แก้ใหม่ใช้ผลเก่าไม่ได้ ปุ่มปิดระหว่างตรวจ/เมื่อพบการรังแก/เมื่อ API ขัดข้อง และมีปุ่มลองตรวจใหม่
สร้างห้องและส่งข้อความต้องรอ backend ยืนยันก่อนล้าง input; backend มีการตรวจอิสระก่อน commit ด้วย
ข้อความแจ้งใกล้ input ระบุว่าข้อความที่พิมพ์จะถูกส่งให้ AI for Thai ตรวจ
