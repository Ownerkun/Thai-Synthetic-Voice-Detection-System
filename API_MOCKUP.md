# API Mockup

เอกสารนี้แยกไว้ให้ frontend เริ่มเขียนโค้ดได้โดยไม่ต้องรอ backend/Docker
ทุก JSON ในนี้ **มาจาก request จริงที่ยิงผ่านโค้ด backend จริง**
ตอนที่ยังไม่มีไฟล์โมเดล .onnx ระบบจึงใช้ `MockSpoofAnalyzer` **ตัวเลขคะแนน/verdict เป็นค่าจำลอง**

> **มี Swagger UI ในตัวอยู่แล้วด้วย** พอรัน backend แล้วเปิด `http://localhost:8000/docs` (interactive,
> ลองยิงจริงได้จากหน้าเว็บเลย) หรือ `http://localhost:8000/redoc` (อ่านง่ายกว่า) หรือดึง schema ดิบที่
> `http://localhost:8000/openapi.json` ไปสร้าง TypeScript types อัตโนมัติได้ (เช่นด้วย `openapi-typescript`)
> เอกสารฉบับนี้มีไว้เสริมสำหรับตอน **backend ยังไม่รัน** หรืออยากเห็นตัวอย่าง error case ครบ ๆ ในที่เดียว

## ภาพรวม

- Base URL (dev ผ่าน Docker): `http://localhost:8000`
- Auth: `Authorization: Bearer <token>` (ได้ token จาก `/auth/login`, `/auth/register` หรือ `/auth/admin/login`)
- ทุก error ใช้รูปแบบเดียวกัน: `{"detail": "ข้อความ"}` ยกเว้น validation error (422) ที่ `detail` เป็น array
- Content-Type: `application/json` สำหรับ endpoint ทั่วไป, `multipart/form-data` เฉพาะ `/predict`

| Endpoint | Method | ต้อง Login | คำอธิบาย |
|---|---|---|---|
| `/health` | GET | ไม่ต้อง | เช็คสถานะ + ว่าใช้โมเดลจริงหรือ mock |
| `/auth/register` | POST | ไม่ต้อง | สมัครสมาชิกผู้ใช้ทั่วไป |
| `/auth/login` | POST | ไม่ต้อง | เข้าสู่ระบบผู้ใช้ทั่วไป |
| `/auth/admin/login` | POST | ไม่ต้อง | เข้าสู่ระบบผู้ดูแล |
| `/predict` | POST | ไม่บังคับ | ตรวจสอบเสียง (1 หรือหลายไฟล์) |
| `/history` | GET | **ต้อง** (user) | ดูรายการประวัติของตนเอง |
| `/history/{id}` | GET | **ต้อง** (user) | ดูรายละเอียด + คะแนนรายช่วง |
| `/history/{id}` | DELETE | **ต้อง** (user) | ลบรายการประวัติ |
| `/history/{id}/feedback` | POST | **ต้อง** (user) | ให้ feedback ว่าผลถูกต้องไหม |
| `/admin/threshold` | GET | **ต้อง** (admin) | ดูค่า threshold ปัจจุบัน |
| `/admin/threshold` | POST | **ต้อง** (admin) | อัปเดตค่า threshold (มีผลทันที) |
| `/admin/stats` | GET | **ต้อง** (admin) | สถิติภาพรวมระบบ |

---

## GET /health

```bash
curl http://localhost:8000/health
```

**200 OK**
```json
{
  "status": "ok",
  "model_version": "mock-v0 (โมเดลจริงยังไม่พร้อม)",
  "using_mock_model": true
}
```
เมื่อวางโมเดลจริงแล้ว `using_mock_model` จะเป็น `false` และ `model_version` จะเป็นค่าที่มาจาก `model.json`
→ frontend ใช้ field นี้แสดง banner เตือนผู้ใช้ได้ เช่น "ระบบอยู่ระหว่างทดสอบ ผลยังไม่แม่นยำ 100%"

---

## POST /auth/register

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"student@example.com","password":"S3cur3Passw0rd!","display_name":"สมชาย ทดสอบ"}'
```

**Request body**
```json
{
  "email": "student@example.com",
  "password": "S3cur3Passw0rd!",
  "display_name": "สมชาย ทดสอบ"
}
```
`display_name` ใส่หรือไม่ใส่ก็ได้ (optional) | `password` ต้อง ≥ 8 ตัวอักษร | `email` ต้องเป็นรูปแบบอีเมลที่ถูกต้อง

**201 Created**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiNTgyMDZmNi00ZGM1LTRiOWEtYmQ3Zi1iMDVjMmVhOGEwMmEiLCJyb2xlIjoidXNlciIsImV4cCI6MTc5MDA2MjQ5NX0.Ifqx5ju7DiD14IyHlIAwkxfoN0kRYE-92-vNXGuuH8Q",
  "token_type": "bearer"
}
```
เก็บ `access_token` ไว้ (เช่น localStorage หรือ cookie) แล้วแนบเป็น `Authorization: Bearer <access_token>`
ในคำขอถัดไปที่ต้องการ login

**409 Conflict** — อีเมลซ้ำ
```json
{ "detail": "อีเมลนี้ถูกใช้แล้ว" }
```

**422 Unprocessable Entity** — ข้อมูลไม่ผ่าน validation เช่น email ผิดรูปแบบ หรือ password สั้นไป
```json
{
  "detail": [
    { "type": "string_too_short", "loc": ["body", "password"], "msg": "String should have at least 8 characters" }
  ]
}
```

---

## POST /auth/login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"student@example.com","password":"S3cur3Passw0rd!"}'
```

**200 OK** — รูปแบบเดียวกับ register
```json
{ "access_token": "eyJhbGciOiJIUzI1NiIs...", "token_type": "bearer" }
```

**401 Unauthorized** — อีเมลหรือรหัสผ่านผิด (ข้อความเดียวกันทั้งสองกรณี ไม่บอกว่าผิดช่องไหน)
```json
{ "detail": "อีเมลหรือรหัสผ่านไม่ถูกต้อง" }
```

---

## POST /auth/admin/login

เหมือน `/auth/login` แต่ใช้ `username` แทน `email` และ token ที่ได้จะมี role เป็น admin
(ใช้เรียก `/admin/*` ได้ แต่เรียก `/history` ไม่ได้)

```bash
curl -X POST http://localhost:8000/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<รหัสผ่านจาก BOOTSTRAP_ADMIN_PASSWORD>"}'
```

**200 OK**
```json
{ "access_token": "eyJhbGciOiJIUzI1NiIs...", "token_type": "bearer" }
```

**401 Unauthorized**
```json
{ "detail": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง" }
```

---

## POST /predict

รับไฟล์เสียงเป็น **list เสมอ** (ไฟล์เดียวก็ส่งเป็น list ที่มี 1 ไฟล์) — ไม่ต้องแยก endpoint
ระหว่าง "อัปโหลดไฟล์เดียว / อัดเสียง / อัปโหลดหลายไฟล์" ทั้งสามวิธีจบที่ endpoint นี้เหมือนกันหมด
(อัดเสียงจากไมค์ก็คือได้ Blob แล้วแนบมาเป็นไฟล์เหมือนกัน)

`Authorization` header **ใส่หรือไม่ใส่ก็ได้**: มี token ที่ถูกต้อง → บันทึกผลลงประวัติ (`saved_to_history: true`),
ไม่มีหรือ token ผิด → ยังตรวจสอบได้ปกติ แต่ไม่บันทึกประวัติ (`saved_to_history: false`)

รองรับเฉพาะ `.wav`, `.flac` ความยาวเกิน 10 วินาทีจะถูกตัดอัตโนมัติ (ดู `duration_seconds` ในผลลัพธ์)

### ตัวอย่าง 1 — ไม่ login, ไฟล์เดียว ยาวเกิน 10 วิ (ถูกตัดอัตโนมัติ)

```bash
curl -F "files=@clip.wav" http://localhost:8000/predict
```

**200 OK**
```json
{
  "results": [
    {
      "id": "ecbecc1d-165e-46ef-b7f1-4497973eb917",
      "original_filename": "clip.wav",
      "duration_seconds": 10.0,
      "sample_rate": 16000,
      "num_segments": 3,
      "mean_probability": 0.6502,
      "max_probability": 0.7559,
      "threshold_used": 0.5,
      "verdict": "spoof",
      "possible_partial_spoof": false,
      "model_version": "mock-v0 (โมเดลจริงยังไม่พร้อม)",
      "processing_ms": 0,
      "segments": [
        { "index": 0, "start_seconds": 0.0, "end_seconds": 4.0, "spoof_probability": 0.7558805346488953, "is_spoof": true },
        { "index": 1, "start_seconds": 4.0, "end_seconds": 8.0, "spoof_probability": 0.7025182247161865, "is_spoof": true },
        { "index": 2, "start_seconds": 8.0, "end_seconds": 10.0, "spoof_probability": 0.4920880198478699, "is_spoof": false }
      ],
      "saved_to_history": false
    }
  ],
  "failed_files": []
}
```
`saved_to_history: false` → frontend รู้ทันทีว่าไม่ต้องแสดง "ดูในประวัติ" สำหรับผลนี้
`segments` → เอาไปวาดกราฟ/ไฮไลต์ช่วงเวลาที่น่าสงสัยได้เลย (ตรงกับ UC4)

### ตัวอย่าง 2 — login แล้ว, อัปโหลดหลายไฟล์พร้อมกัน

```bash
curl -F "files=@call_a.wav" -F "files=@call_b.wav" \
  -H "Authorization: Bearer <TOKEN>" \
  http://localhost:8000/predict
```

**200 OK** — `results` มีหลายรายการตามจำนวนไฟล์ที่ส่งมา แต่ละรายการมี `saved_to_history: true`
เพราะมี token ที่ถูกต้อง
```json
{
  "results": [
    {
      "id": "241de76c-f61e-48a8-9d37-807cb7cb6484",
      "original_filename": "call_a.wav",
      "duration_seconds": 3.0,
      "sample_rate": 16000,
      "num_segments": 1,
      "mean_probability": 0.7559,
      "max_probability": 0.7559,
      "threshold_used": 0.5,
      "verdict": "spoof",
      "possible_partial_spoof": false,
      "model_version": "mock-v0 (โมเดลจริงยังไม่พร้อม)",
      "processing_ms": 0,
      "segments": [
        { "index": 0, "start_seconds": 0.0, "end_seconds": 3.0, "spoof_probability": 0.7558805346488953, "is_spoof": true }
      ],
      "saved_to_history": true
    },
    {
      "id": "28db9dd4-47b7-4748-bf63-3c6387b66547",
      "original_filename": "call_b.wav",
      "duration_seconds": 5.0,
      "sample_rate": 16000,
      "num_segments": 2,
      "mean_probability": 0.655,
      "max_probability": 0.6829,
      "threshold_used": 0.5,
      "verdict": "spoof",
      "possible_partial_spoof": false,
      "model_version": "mock-v0 (โมเดลจริงยังไม่พร้อม)",
      "processing_ms": 0,
      "segments": [
        { "index": 0, "start_seconds": 0.0, "end_seconds": 4.0, "spoof_probability": 0.6270922422409058, "is_spoof": true },
        { "index": 1, "start_seconds": 4.0, "end_seconds": 5.0, "spoof_probability": 0.6828998923301697, "is_spoof": true }
      ],
      "saved_to_history": true
    }
  ],
  "failed_files": []
}
```
→ `results.length > 1` คือสัญญาณให้ frontend สลับไปแสดง "ตารางเปรียบเทียบ" แทน "ผลรายไฟล์" (ตาม Activity Diagram)

### ตัวอย่าง 3 — ไฟล์บางไฟล์รูปแบบไม่ถูกต้อง (ผสมกับไฟล์ที่ถูกต้อง)

```bash
curl -F "files=@clip.mp3" -F "files=@clip2.wav" http://localhost:8000/predict
```

**200 OK** — status code ยังเป็น 200 เสมอ! ไฟล์ที่ผ่านอยู่ใน `results`, ไฟล์ที่ไม่ผ่านอยู่ใน `failed_files`
(ไม่ throw error รวมทั้ง request เพราะอาจมีไฟล์อื่นที่ตรวจสำเร็จปนอยู่)
```json
{
  "results": [
    {
      "id": "581288b2-6cb9-4898-86a6-ef63cde50f25",
      "original_filename": "clip2.wav",
      "duration_seconds": 3.0,
      "sample_rate": 16000,
      "num_segments": 1,
      "mean_probability": 0.7559,
      "max_probability": 0.7559,
      "threshold_used": 0.5,
      "verdict": "spoof",
      "possible_partial_spoof": false,
      "model_version": "mock-v0 (โมเดลจริงยังไม่พร้อม)",
      "processing_ms": 0,
      "segments": [
        { "index": 0, "start_seconds": 0.0, "end_seconds": 3.0, "spoof_probability": 0.7558805346488953, "is_spoof": true }
      ],
      "saved_to_history": false
    }
  ],
  "failed_files": ["clip.mp3"]
}
```
→ frontend ควรวน `failed_files` มาแจ้งผู้ใช้แยกจากผลที่ตรวจสำเร็จ เช่น toast "clip.mp3 ไม่รองรับ (รองรับเฉพาะ .wav, .flac)"

---

## GET /history

```bash
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/history
```

**200 OK** — เรียงจากใหม่ไปเก่าเสมอ, ไม่มี `segments` ในนี้ (ดูรายละเอียดต้องเรียก `/history/{id}` ต่อ)
```json
[
  {
    "id": "241de76c-f61e-48a8-9d37-807cb7cb6484",
    "created_at": "2026-09-15T07:34:56",
    "original_filename": "call_a.wav",
    "duration_seconds": 3.0,
    "verdict": "spoof",
    "mean_probability": 0.7559,
    "max_probability": 0.7559,
    "possible_partial_spoof": false
  },
  {
    "id": "28db9dd4-47b7-4748-bf63-3c6387b66547",
    "created_at": "2026-09-15T07:34:56",
    "original_filename": "call_b.wav",
    "duration_seconds": 5.0,
    "verdict": "spoof",
    "mean_probability": 0.655,
    "max_probability": 0.6829,
    "possible_partial_spoof": false
  }
]
```
รองรับ `?limit=50` (default 50, สูงสุด 200)

**401 Unauthorized** — ไม่ได้แนบ token หรือ token ไม่ถูกต้อง/หมดอายุ
```json
{ "detail": "ต้องเข้าสู่ระบบก่อนใช้งานส่วนนี้" }
```

---

## GET /history/{id}

```bash
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/history/241de76c-f61e-48a8-9d37-807cb7cb6484
```

**200 OK** — เหมือน item ใน `/history` แต่เพิ่ม `threshold_used`, `model_version`, `processing_ms`, `segments`
```json
{
  "id": "241de76c-f61e-48a8-9d37-807cb7cb6484",
  "created_at": "2026-09-15T07:34:56",
  "original_filename": "call_a.wav",
  "duration_seconds": 3.0,
  "verdict": "spoof",
  "mean_probability": 0.7559,
  "max_probability": 0.7559,
  "possible_partial_spoof": false,
  "threshold_used": 0.5,
  "model_version": "mock-v0 (โมเดลจริงยังไม่พร้อม)",
  "processing_ms": 0,
  "segments": [
    { "index": 0, "start_seconds": 0.0, "end_seconds": 3.0, "spoof_probability": 0.7558805346488953, "is_spoof": true }
  ]
}
```

**404 Not Found** — ไม่พบ หรือเป็นของผู้ใช้คนอื่น (ตั้งใจให้ error เหมือนกันทั้งสองกรณี ไม่บอกว่ามีอยู่แต่ไม่ใช่ของเรา)
```json
{ "detail": "ไม่พบรายการ" }
```

---

## DELETE /history/{id}

```bash
curl -X DELETE -H "Authorization: Bearer <TOKEN>" http://localhost:8000/history/241de76c-f61e-48a8-9d37-807cb7cb6484
```

**204 No Content** — สำเร็จ ไม่มี body ตอบกลับ
**404 Not Found** — เหมือนด้านบน ถ้าไม่พบหรือไม่ใช่ของผู้ใช้คนนี้

---

## POST /history/{id}/feedback

```bash
curl -X POST http://localhost:8000/history/241de76c-f61e-48a8-9d37-807cb7cb6484/feedback \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"user_agrees": true}'
```

**201 Created**
```json
{
  "id": "24d9e7c2-1e72-4c71-9274-3a2663757985",
  "detection_id": "241de76c-f61e-48a8-9d37-807cb7cb6484",
  "user_agrees": true
}
```

**409 Conflict** — ให้ feedback รายการนี้ไปแล้ว (1 รายการให้ feedback ได้ครั้งเดียว)
```json
{ "detail": "ให้ feedback รายการนี้ไปแล้ว" }
```

> ⚠️ ตอนนี้ endpoint นี้บังคับ login เสมอ แม้ Use Case Diagram จะให้ guest feedback ได้ด้วย
> (ดูหมายเหตุใน README ของ backend — เป็นจุดที่ต้องยืนยันกับอาจารย์อีกครั้ง)

---

## GET /admin/threshold

```bash
curl -H "Authorization: Bearer <ADMIN_TOKEN>" http://localhost:8000/admin/threshold
```

**200 OK** — เป็น `null` ได้ถ้ายังไม่เคยมีใครตั้งค่ามาก่อน (ระบบจะใช้ค่า default จาก config แทน)
```json
null
```
หลังมีคนตั้งค่าแล้วจะได้แบบนี้แทน (รูปแบบเดียวกับ `current` ใน POST ด้านล่าง)

**401 Unauthorized** — token ไม่ใช่ของแอดมิน (หรือเป็น token ผู้ใช้ทั่วไป)
```json
{ "detail": "ไม่มีสิทธิ์ดำเนินการ" }
```

---

## POST /admin/threshold

```bash
curl -X POST http://localhost:8000/admin/threshold \
  -H "Authorization: Bearer <ADMIN_TOKEN>" -H "Content-Type: application/json" \
  -d '{"value": 0.65, "note": "ปรับตามผล validation ล่าสุด"}'
```

**200 OK** — `previous_value` เป็น `null` ถ้าเป็นการตั้งค่าครั้งแรก
```json
{
  "previous_value": null,
  "current": {
    "id": "6bccd81e-86ac-4bd9-98f8-b0c0c5bd9e9a",
    "value": 0.65,
    "effective_from": "2026-09-15T07:34:56",
    "changed_by_admin_id": "cd2ca309-5cdf-4a87-a596-3a8efc5fa2e0",
    "note": "ปรับตามผล validation ล่าสุด"
  }
}
```
มีผลกับ `/predict` คำขอถัดไป**ทันที** ไม่ต้อง restart backend

**422 Unprocessable Entity** — `value` ต้องอยู่ระหว่าง 0.0–1.0
```json
{
  "detail": [
    { "type": "less_than_equal", "loc": ["body", "value"], "msg": "Input should be less than or equal to 1", "input": 1.5, "ctx": {"le": 1.0} }
  ]
}
```

---

## GET /admin/stats

```bash
curl -H "Authorization: Bearer <ADMIN_TOKEN>" http://localhost:8000/admin/stats
```

**200 OK** — `feedback_agreement_rate` เป็น `null` ถ้ายังไม่มี feedback เลยสักรายการ
```json
{
  "total_detections": 4,
  "total_spoof_verdicts": 4,
  "total_real_verdicts": 0,
  "total_users": 1,
  "feedback_agreement_rate": 1.0
}
```

**401 Unauthorized** — เรียกด้วย token ผู้ใช้ทั่วไป (ไม่ใช่แอดมิน)
```json
{ "detail": "ไม่มีสิทธิ์ดำเนินการ" }
```

---

## สรุป error status code ที่ frontend ต้องดักไว้

| Status | ความหมาย | ตัวอย่างจุดที่เจอ |
|---|---|---|
| 401 | ไม่ได้ login / token หมดอายุ / role ไม่ตรง | `/history`, `/admin/*` เมื่อไม่มี/ผิด token |
| 404 | ไม่พบข้อมูล หรือไม่ใช่เจ้าของ | `/history/{id}` ที่ไม่มีจริงหรือเป็นของคนอื่น |
| 409 | ข้อมูลขัดแย้งกับที่มีอยู่ | อีเมลซ้ำตอนสมัคร, feedback ซ้ำ |
| 422 | request body ไม่ผ่าน validation | password สั้นไป, threshold นอกช่วง 0–1 |
| 200 (แต่มี `failed_files`) | ตรวจสอบเสียงสำเร็จบางไฟล์ | อัปโหลดไฟล์ผิดฟอร์แมตปนกับไฟล์ที่ถูกต้อง |
