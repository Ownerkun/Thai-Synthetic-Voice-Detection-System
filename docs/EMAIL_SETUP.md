# ตั้งค่าการส่งอีเมล (ยืนยันอีเมลตอนสมัคร + รีเซ็ตรหัสผ่าน)

## ภาพรวมการทำงาน

```
สมัคร:    POST /auth/register ──► สร้างบัญชี (ยังล็อกอินไม่ได้) ──► ส่งอีเมล "ยืนยันอีเมล"
                                              │
          ผู้ใช้กดลิงก์ {FRONTEND_BASE_URL}/verify-email?token=...  (หน้าเว็บ)
                                              │
          หน้าเว็บเรียก POST /auth/verify-email {token} ──► ได้ access_token เข้าสู่ระบบทันที

ลืมรหัส:  POST /auth/forgot-password ──► ส่งอีเมล "ตั้งรหัสผ่านใหม่" (ถ้าอีเมลนี้มีในระบบ)
          ผู้ใช้กดลิงก์ {FRONTEND_BASE_URL}/reset-password?token=...
          หน้าเว็บเรียก POST /auth/reset-password {token, new_password} ──► login ใหม่ด้วยรหัสใหม่
```

ทั้งสองอย่างใช้ระบบเดียวกัน: โทเคนสุ่มใช้ครั้งเดียว (เก็บเฉพาะ hash ในตาราง `email_token`) + `app/services/mail_service.py`
ซึ่งเลือกวิธีส่งด้วย `MAIL_BACKEND`

| MAIL_BACKEND | ทำอะไร | ใช้เมื่อ |
|---|---|---|
| `console` (ค่าเริ่มต้น) | พิมพ์อีเมลลง log ไม่ส่งจริง | dev: เปิด `docker compose logs api` แล้วคัดลอกลิงก์มาเปิดเอง |
| `smtp` | ส่งจริงผ่าน SMTP | ใช้งานจริง · เปลี่ยนผู้ให้บริการด้วยการแก้ `SMTP_*` ไม่ต้องแก้โค้ด |
| `memory` | เก็บไว้ในหน่วยความจำ | เทสต์อัตโนมัติ (ตั้งโดย `tests/conftest.py` เอง) |

การส่งอีเมลทำ **หลังตอบ client แล้ว** (FastAPI `BackgroundTasks`) ถ้า SMTP ช้าหรือล่ม หน้าสมัครไม่ค้าง และผู้ใช้กด "ส่งลิงก์ยืนยันอีกครั้ง"
(`POST /auth/resend-verification`) ได้ ข้อผิดพลาดการส่งดูได้ใน `docker compose logs api`

## ตัวแปรใน `.env`

| ตัวแปร | ค่าเริ่มต้น | ความหมาย |
|---|---|---|
| `MAIL_BACKEND` | `console` | `console` / `smtp` / `memory` |
| `MAIL_FROM_ADDRESS` | `no-reply@example.com` | ผู้ส่งที่แสดงในอีเมล · **ใช้ Gmail ต้องเป็นที่อยู่ Gmail เดียวกับ `SMTP_USERNAME`** |
| `MAIL_FROM_NAME` | `Thai Synthetic Voice Detection` | ชื่อผู้ส่ง |
| `SMTP_HOST` / `SMTP_PORT` | `smtp.gmail.com` / `587` | เซิร์ฟเวอร์ SMTP |
| `SMTP_SECURITY` | `starttls` | `starttls` (พอร์ต 587) · `ssl` (พอร์ต 465) · `none` (เฉพาะทดสอบในเครื่อง) |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | ว่าง | บัญชี SMTP (Gmail ใช้ App Password) |
| `SMTP_TIMEOUT_SECONDS` | `10` | รอเซิร์ฟเวอร์ได้นานแค่ไหน |
| `FRONTEND_BASE_URL` | `http://localhost:3000` | ฐานของลิงก์ในอีเมล ตอน deploy ใส่ `https://ชื่อของคุณ.duckdns.org` (ไม่ต้องมี `/` ท้าย) |
| `VERIFY_EMAIL_TTL_MINUTES` | `1440` | ลิงก์ยืนยันอีเมลใช้ได้ 24 ชั่วโมง |
| `RESET_PASSWORD_TTL_MINUTES` | `60` | ลิงก์รีเซ็ตรหัสผ่านใช้ได้ 1 ชั่วโมง |
| `EMAIL_TOKEN_COOLDOWN_SECONDS` | `60` | ขอลิงก์ประเภทเดียวกันซ้ำได้ทุกกี่วินาที (กันถูกใช้ยิงอีเมลรบกวนผู้อื่น) |

## เลือกผู้ให้บริการส่งอีเมล

ข้อมูลโควตา/ราคาอ่านจากหน้าทางการเมื่อ 12 พ.ย. 2569 ซึ่งเปลี่ยนได้ ตรวจอีกรอบก่อนตัดสินใจ

| ผู้ให้บริการ | ฟรี | ต้องมีโดเมนของตัวเองไหม | หมายเหตุ |
|---|---|---|---|
| **Gmail SMTP** (App Password) | 0 บาท · หน้าทางการเตือนเมื่อส่งเกิน 500 อีเมล/วัน | **ไม่ต้อง** | ส่งจากที่อยู่ Gmail ของคุณเอง · เหมาะกับโครงงาน/ผู้ใช้หลักสิบถึงหลักร้อยคน |
| **Resend** | 3,000 อีเมล/เดือน, 100/วัน, 3 โดเมน | **ต้อง** verify โดเมนก่อนส่ง | ตั้งค่าง่าย, SMTP: `smtp.resend.com` user `resend` password = API key · ต้องเพิ่มระเบียน DNS (SPF/DKIM) |
| Brevo | 300 อีเมล/วัน ตลอดไป | แนะนำโดเมน (ใช้ที่อยู่ Gmail เป็นผู้ส่งผ่าน Brevo ยังไม่มีเอกสารยืนยัน) | ต้องรออนุมัติบัญชี และขอเปิด SMTP ผ่านฝ่ายสนับสนุน |
| Mailjet | 6,000 อีเมล/เดือน (200/วัน) | ไม่พบข้อมูลชัดเจน | |
| Amazon SES | ไม่พบโควตาฟรีสำหรับบัญชีใหม่ (มีเครดิต AWS $200 ใช้ได้ 6 เดือน) · ราคา $0.10–0.16 ต่อ 1,000 อีเมล | ไม่บังคับ แต่ช่วยให้อนุมัติเร็ว | บัญชีใหม่อยู่ใน sandbox (ส่งได้เฉพาะผู้รับที่ verify ไว้ 200 อีเมล/วัน) ต้องขอ production access รอตอบราว 96 ชั่วโมง |
| SendGrid | ทดลองใช้ 60 วัน แล้วต้องจ่าย | | ไม่เหมาะ |

### ข้อจำกัดของ DuckDNS (สำคัญ)

DuckDNS เป็นโดเมนฟรีที่ตั้งได้แค่ IP (A/AAAA) กับ TXT หนึ่งค่า (ใช้ทำ SSL ได้) จากหน้า spec ของ DuckDNS ไม่พบการรองรับ MX, CNAME หรือระเบียน
DKIM แยกชื่อ จึง **ยืนยันโดเมนกับ Resend/Mailgun ไม่ได้** (ข้อสรุปนี้อนุมานจากเอกสาร ไม่ได้ลองจริง) ถ้าไม่มีโดเมนของตัวเองให้ใช้ Gmail SMTP
ถ้าต้องการ Resend ภายหลังต้องซื้อโดเมนจริง (ราคาขึ้นกับนามสกุลและผู้ขาย ยังไม่ได้ตรวจราคา) แล้วเปลี่ยนแค่ `SMTP_*` / `MAIL_FROM_ADDRESS` ใน `.env`

## ตั้งค่า Gmail SMTP ทีละขั้น

1. ใช้บัญชี Gmail ส่วนตัว (บัญชีองค์กร/โรงเรียนของ Google Workspace สร้าง App Password ไม่ได้) แนะนำสร้างบัญชีใหม่สำหรับโครงงานโดยเฉพาะ
   เช่น `thaispoof.noreply@gmail.com` อย่าใช้บัญชีส่วนตัวหลักของคุณ
2. เปิด **การยืนยันแบบ 2 ขั้นตอน (2-Step Verification)** ที่ https://myaccount.google.com/security
3. สร้าง **App Password** ที่ https://myaccount.google.com/apppasswords ตั้งชื่ออะไรก็ได้ ได้รหัส 16 ตัวอักษร
   (Google ระบุว่า App Password "ไม่แนะนำ และไม่จำเป็นในกรณีส่วนใหญ่" ใช้ได้กับกรณีนี้ที่แอปของเรา login ด้วย Google ไม่ได้ ถ้าเปลี่ยนรหัส Gmail รหัสนี้จะถูกเพิกถอนทั้งหมด)
4. ใส่ใน `.env` (ไม่ commit):

   ```env
   MAIL_BACKEND=smtp
   MAIL_FROM_ADDRESS=thaispoof.noreply@gmail.com
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_SECURITY=starttls
   SMTP_USERNAME=thaispoof.noreply@gmail.com
   SMTP_PASSWORD=abcdefghijklmnop
   FRONTEND_BASE_URL=https://ชื่อของคุณ.duckdns.org
   ```

5. ทดสอบ: `docker compose exec api python scripts/send_test_email.py อีเมลของคุณ@example.com` · restart `api` หลังแก้ `.env` ทุกครั้ง
6. ลองสมัครผ่านหน้าเว็บ/Bruno จริงอีกรอบ ดูว่าอีเมลเข้า inbox (ครั้งแรกอาจเข้าโฟลเดอร์สแปม กด "ไม่ใช่สแปม")

ค่า `smtp.gmail.com` พอร์ต 587 (STARTTLS) / 465 (SSL) เป็นค่ามาตรฐานของ Gmail แต่ไม่ได้ตรวจกับหน้าทางการของ Google ในรอบที่เขียนเอกสารนี้ — ให้สคริปต์ทดสอบข้อ 5 เป็นตัวยืนยัน

## ปัญหาที่พบบ่อย

| อาการ | สาเหตุที่เป็นไปได้ |
|---|---|
| `SMTPAuthenticationError 535` | ใช้รหัสผ่าน Gmail ปกติแทน App Password · ยังไม่เปิด 2-Step Verification · ลบ/เปลี่ยนรหัส Gmail แล้ว (App Password ถูกเพิกถอน) |
| `TimeoutError` / `ConnectionRefusedError` | VPS บล็อกพอร์ต SMTP ขาออก → ลอง `SMTP_PORT=465` + `SMTP_SECURITY=ssl` · ตรวจด้วย `nc -vz smtp.gmail.com 587` จากเครื่อง VPS · บางผู้ให้บริการ VPS ต้องเปิดคำขอปลดบล็อก |
| อีเมลเข้าสแปม | ปกติสำหรับผู้ส่งใหม่ · ถ้ามีโดเมนจริงให้ตั้ง SPF/DKIM/DMARC |
| ผู้ส่งไม่ตรงกับ `MAIL_FROM_ADDRESS` | Gmail เขียนทับผู้ส่งเป็นบัญชีที่ login ถ้าไม่ได้ตั้งเป็น alias ที่ยืนยันแล้ว → ใช้ที่อยู่เดียวกับ `SMTP_USERNAME` |
| ลิงก์ในอีเมลชี้ `localhost` | ยังไม่ได้ตั้ง `FRONTEND_BASE_URL` |
| เทสต์ `pytest` ส่งอีเมลจริง? | ไม่: `tests/conftest.py` บังคับ `MAIL_BACKEND=memory` แม้ `.env` จะตั้ง smtp ไว้ |

## สิ่งที่ Frontend ต้องทำ

- หน้า `/verify-email` อ่าน `token` จาก query string แล้ว `POST /auth/verify-email {"token": "..."}` — สำเร็จได้ `access_token` (เก็บแล้วเข้าสู่ระบบเลย) · 400 → แสดงปุ่ม "ส่งลิงก์ยืนยันอีกครั้ง"
- หน้า `/reset-password` อ่าน `token` แล้วแสดงฟอร์มรหัสผ่านใหม่ → `POST /auth/reset-password {"token","new_password"}` → ไปหน้า login
- หน้าสมัคร: `201` **ไม่มี `access_token` แล้ว** ให้แสดงหน้า "ตรวจกล่องอีเมลของคุณ" พร้อมปุ่มส่งซ้ำ
- หน้า login: `403` ที่ `detail` = `"Email not verified"` → แสดงปุ่มส่งลิงก์ยืนยันอีกครั้ง (คนละกรณีกับ `"Account suspended"`)
- ต้องเรียก API ด้วย POST จากหน้าเว็บ ห้ามให้ลิงก์ในอีเมลชี้ไป API ตรงๆ เพราะโปรแกรมสแกนลิงก์ของผู้ให้บริการอีเมลมัก GET ล่วงหน้าแล้วทำให้โทเคนถูกใช้ไปก่อนผู้ใช้กด

## ข้อจำกัดที่ยังมี

- ส่งอีเมลจริงยังไม่ได้ทดสอบกับ Gmail/Resend จริงในสภาพแวดล้อมที่เขียนโค้ด (ทดสอบกับเซิร์ฟเวอร์ SMTP จำลองในเครื่องและ mock เท่านั้น) — ต้องรัน `scripts/send_test_email.py` บน VPS เอง
- ยังไม่มี rate limit ระดับ IP (มีเฉพาะช่วงรอต่อบัญชีต่อประเภทลิงก์) และยังไม่มีการลบบัญชีที่ไม่เคยยืนยันทิ้งอัตโนมัติ: อีเมลที่พิมพ์ผิดตอนสมัครจะค้างในระบบ
  (เจ้าของอีเมลตัวจริงเรียกใช้ "ลืมรหัสผ่าน" เพื่อกู้บัญชีนั้นได้)
- `PUT /users/me/password` (เปลี่ยนรหัสขณะ login) ยังไม่เพิกถอน token เดิม เพิกถอนเฉพาะกรณีรีเซ็ตรหัสผ่านผ่านอีเมล
