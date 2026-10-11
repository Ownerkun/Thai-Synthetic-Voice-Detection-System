# Frontend — ระบบตรวจสอบเสียงสังเคราะห์ภาษาไทย

React + Vite + TypeScript คุยกับ backend (FastAPI) ผ่าน REST เท่านั้น ไม่ได้แก้โค้ด backend
อ้างอิง contract จาก [`docs/API_MOCKUP.md`](../docs/API_MOCKUP.md) และ schema ใน `app/schemas/`

## เริ่มใช้งาน (dev)

ต้องมี Node.js 20+ และ backend รันอยู่ที่ `http://localhost:8000` (เช่น `docker compose up --build` ที่ root ของ repo)

```bash
cd frontend
npm install
npm run dev
```

เปิด http://localhost:5173 — ตอน dev ทุก request ไปที่ `/api/*` แล้ว Vite proxy ต่อไปที่ backend ให้
จึงไม่ต้องตั้ง CORS เพิ่ม ถ้า backend อยู่ที่อื่นให้ตั้ง `BACKEND_URL` ก่อนรัน เช่น `BACKEND_URL=http://192.168.1.10:8000 npm run dev`

## Build ไป deploy

```bash
VITE_API_BASE_URL=https://api.example.com npm run build   # ผลลัพธ์อยู่ใน dist/
```

`dist/` เป็นไฟล์ static ล้วน วางบน host ไหนก็ได้ (ต้องตั้ง fallback ทุก path ไปที่ `index.html` เพราะใช้ client-side routing)
และต้องใส่โดเมนของ frontend ใน `CORS_ORIGINS` ของ backend

## หน้าที่มี

| Path | สิทธิ์ | ทำอะไร |
|---|---|---|
| `/` | ทุกคน | อัปโหลดหลายไฟล์ / ลากวาง / อัดเสียงจากไมค์ → ผล + กราฟคะแนนรายช่วง (แตะแท่งเพื่อฟังช่วงนั้น), เทียบผลหลายไฟล์, ผลล่าสุดของ guest |
| `/about` | ทุกคน | วิธีทำงาน, วิธีอ่านผล, ความเป็นส่วนตัว, ข้อจำกัด |
| `/login`, `/register` | ทุกคน | เข้าสู่ระบบ / สมัครสมาชิก |
| `/history`, `/history/:id` | user | ประวัติ, รายละเอียด, ให้/แก้ feedback, ลบรายการ |
| `/feedback` | user | feedback ทั้งหมดที่เคยให้ |
| `/admin/login`, `/admin` | admin | สถิติ, ปรับ threshold, จัดการผู้ใช้ (ค้นหา, กรอง, แก้ชื่อ, ระงับ/เปิดใช้) |

## หมายเหตุการเชื่อมต่อกับ backend

- **อัดเสียง:** backend รับเฉพาะ `.wav`/`.flac` แต่เบราว์เซอร์อัดได้ webm/ogg จึงแปลงเป็น WAV mono 16 kHz ฝั่ง client ก่อนส่ง (`src/lib/wav.ts`) และหยุดอัดอัตโนมัติที่ 10 วินาที (backend วิเคราะห์แค่ 10 วินาทีแรก)
- **ไฟล์ที่ตรวจไม่ได้:** แสดงข้อความไทยจาก `failed_files[].reason` ตามตารางใน API_MOCKUP (ไม่อ่านจาก `message`) ถ้าเจอ reason ใหม่จะแสดงข้อความกลาง
- **Token:** เก็บ JWT ใน `localStorage`, อ่าน `role`/`exp` จาก payload เพื่อเลือกเมนูเท่านั้น (ตรวจลายเซ็นจริงที่ backend) ถ้า API ตอบ 401 หรือ token หมดอายุจะออกจากระบบให้อัตโนมัติ
- **ฟังเสียงรายช่วง:** ใช้ไฟล์ที่อยู่ในเบราว์เซอร์ตอนเพิ่งตรวจเท่านั้น (backend ไม่เก็บไฟล์เสียง) หน้าประวัติจึงฟังซ้ำไม่ได้
- **ผลล่าสุดของ guest:** ผู้ที่ไม่ได้ login จะเก็บ 20 ผลล่าสุดไว้ใน `localStorage` (`src/lib/guestResults.ts`) ตาม UML Activity Diagram — เก็บแค่คะแนน ไม่เก็บเสียง
- **ธีม:** ปุ่มสลับสว่าง/มืดบนแถบด้านบน จำค่าไว้ใน `localStorage` ถ้ายังไม่เคยเลือกจะตามการตั้งค่าเครื่อง
- **Mock model:** ถ้า `/health` ตอบ `using_mock_model: true` จะมีแถบเตือนด้านบนทุกหน้า
- **Types:** `src/api/types.ts` เขียนตาม schema ของ backend ถ้า backend เปลี่ยน schema ให้แก้ที่ไฟล์นี้ที่เดียว
