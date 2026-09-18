# Thai Synthetic Voice Detection — Backend (FastAPI + ONNX Runtime + PostgreSQL)

Backend API ของโครงงาน SI423-59 ระบบตรวจสอบเสียงสังเคราะห์ภาษาไทย
สร้างตาม UML (ดู `UML_final_product_v2.md` ในโปรเจกต์)

## สถานะปัจจุบัน

โมเดล ONNX ยังอยู่ระหว่างเทรน (ดำเนินการบน Kaggle เพื่อเลี่ยงข้อจำกัด GPU เครื่อง local)
Backend นี้จึงถูกออกแบบให้ **ทำงานได้ครบ pipeline ทันทีแม้ยังไม่มีไฟล์โมเดลจริง**:
ถ้าไม่พบไฟล์ที่ `ONNX_MODEL_PATH` ระบบจะสลับไปใช้ `MockSpoofAnalyzer` โดยอัตโนมัติ
(คืนคะแนนหลอกแบบ deterministic ไว้ทดสอบ frontend/backend/database ร่วมกันได้ก่อน)

เมื่อโมเดลเทรนเสร็จ **แค่วางไฟล์ 2 ไฟล์ในโฟลเดอร์ `models/` แล้ว restart container**:

```
models/
  model.onnx   # ตัวโมเดล (Baseline SincConv+AASIST หรือ XLS-R+AASIST)
  model.json   # metadata: sample_rate, segment_samples, temperature, model_version, spoof_class_index
```

ไม่ต้องแก้โค้ดส่วนอื่นเลย ดู `app/services/onnx_analyzer.py`

> **เหตุผลที่เลือก PostgreSQL**  ดูรายละเอียดได้ที่ [`docs/WHY_POSTGRESQL.md`](docs/WHY_POSTGRESQL.md)

## โครงสร้างโปรเจกต์

```
app/
  core/            config, database session, security (JWT/hash), custom GUID column type
  models/          SQLAlchemy ORM ตรงกับ Class Diagram ทุก field
  schemas/         Pydantic request/response models
  services/
    audio_preprocessor.py   # AudioPreprocessor (Data Cleaning)
    onnx_analyzer.py         # OnnxSpoofAnalyzer จริง + MockSpoofAnalyzer สลับอัตโนมัติ
    threshold_service.py     # อ่านค่า threshold ล่าสุดจาก DB
  features/
    auth/          POST /auth/register, /auth/login, /auth/admin/login
    detection/     POST /predict, GET /health
    history/       GET /history, GET /history/{id}, DELETE /history/{id},
                   POST /history/{id}/feedback  (ทุก endpoint ต้อง login)
    admin/         GET/POST /admin/threshold, GET /admin/stats
  main.py          ประกอบ FastAPI app, CORS, lifespan
alembic/           DB migrations
docker/api/        Dockerfile (multi-stage) + entrypoint.sh (รอ DB พร้อม + migrate อัตโนมัติ)
tests/             pytest smoke test ครอบคลุม flow หลักทั้งหมด (รันจริงผ่านแล้ว ใช้ sqlite แทน postgres)
models/            วางไฟล์ model.onnx / model.json ที่นี่ (mount เข้า container แบบ read-only)
```

## รันด้วย Docker (แนะนำ)

```bash
cp .env.example .env        # แล้วแก้ JWT_SECRET_KEY, BOOTSTRAP_ADMIN_PASSWORD
docker compose up --build   # โหมด dev: hot-reload, mount source code (โหลด docker-compose.override.yml อัตโนมัติ)
```

- API: http://localhost:8000 Swagger UI ที่ http://localhost:8000/docs
- เปิด pgAdmin เสริม (ไม่บังคับ): `docker compose --profile tools up -d`
- ตอน container `api` เริ่มทำงาน จะรอ Postgres พร้อม แล้วรัน `alembic upgrade head` ให้อัตโนมัติเสมอ

Deploy แบบ prod (ไม่ hot-reload, ไม่ mount source):

```bash
docker compose -f docker-compose.yml up -d --build
```

## รันแบบ local (ไม่ใช้ Docker) สำหรับ debug เร็ว ๆ

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # ปรับ DATABASE_URL เป็น postgres ที่รันอยู่ หรือ sqlite:///./dev.db เพื่อทดสอบ
alembic upgrade head
uvicorn app.main:app --reload
```

รันเทส (ใช้ sqlite in-memory ผ่าน GUID type ที่รองรับทั้งสอง dialect ไม่ต้องมี Postgres ก็รันได้):

```bash
pytest -q
```

## ทดสอบ endpoint เร็ว ๆ ด้วย curl

```bash
# ตรวจสอบเสียงแบบไม่ login (ไม่ถูกบันทึกในประวัติ)
curl -F "files=@sample.wav" http://localhost:8000/predict

# สมัครสมาชิก แล้วเก็บ token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"S3cur3Passw0rd!"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# ตรวจสอบเสียงแบบ login (บันทึกลงประวัติ)
curl -F "files=@sample.wav" -H "Authorization: Bearer $TOKEN" http://localhost:8000/predict

# ดูประวัติ
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/history

# ดูรายละเอียดรายการ (แทน {id} ด้วย UUID จากผลข้างบน)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/history/{id}

# ให้ feedback ว่าผลถูกต้องหรือไม่ (ต้อง login guest ไม่สามารถให้ feedback ได้)
curl -X POST http://localhost:8000/history/{id}/feedback \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_agrees": true}'

# ลบรายการประวัติ (ต้อง login ลบได้เฉพาะรายการของตนเอง)
curl -X DELETE -H "Authorization: Bearer $TOKEN" http://localhost:8000/history/{id}
```

## หมายเหตุสถาปัตยกรรม

- **Real-time (ภาคผนวก ก)** ยังไม่ implement ตามที่ตกลงว่าเลื่อนไปก่อน
