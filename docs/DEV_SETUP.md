# Dev Setup — เตรียมเครื่องก่อนรัน Backend

เอกสารนี้ครอบคลุมทุกอย่างที่ต้องติดตั้งในเครื่องก่อน `docker compose up --build` ครั้งแรก
และ VS Code extensions ที่ทำให้พัฒนาโปรเจกต์นี้สะดวกขึ้นมาก

---

## 1. ซอฟต์แวร์ที่ต้องติดตั้ง (Required)

### Docker Desktop
ตัวหลักสำหรับรัน backend + database บนเครื่อง dev

| OS | ลิ้งค์ | หมายเหตุ |
|---|---|---|
| Windows | https://docs.docker.com/desktop/install/windows-install/ | ต้องเปิด **WSL 2** ก่อน (ดูด้านล่าง) |
| macOS | https://docs.docker.com/desktop/install/mac-install/ | ใช้ได้เลย |
| Linux | https://docs.docker.com/engine/install/ | ติดตั้ง Docker Engine + Compose Plugin แทน Desktop |

ตรวจสอบว่าติดตั้งสำเร็จ:
```bash
docker --version          # Docker version 27.x.x หรือใหม่กว่า
docker compose version    # Docker Compose version v2.x.x
```

#### Windows: เปิด WSL 2 ก่อน
Docker Desktop บน Windows ต้องใช้ WSL 2 (Windows Subsystem for Linux)

1. เปิด PowerShell แบบ **Run as Administrator**
2. รัน:
```powershell
wsl --install
wsl --set-default-version 2
```
3. Restart เครื่อง แล้วค่อยติดตั้ง Docker Desktop

---

### Git
ใช้ clone repo และจัดการ version control

| OS | วิธีติดตั้ง |
|---|---|
| Windows | https://git-scm.com/download/win |
| macOS | `xcode-select --install` หรือ https://git-scm.com/download/mac |
| Linux | `sudo apt install git` หรือ package manager ของ distro |

```bash
git --version   # ตรวจสอบ
```

---

### Bruno (API Testing)
แทน Postman ใช้ทดสอบ API — เปิด collection ใน `bruno/` ได้เลย

ดาวน์โหลดที่ https://www.usebruno.com/downloads

> ต้องการ Bruno เวอร์ชัน **1.x** ขึ้นไป (รองรับ open collection format `.yml`)

---

## 2. เครื่องมือเสริม (แนะนำแต่ไม่บังคับ)

### Python 3.12+
จำเป็นเฉพาะตอนรัน **local โดยไม่ใช้ Docker** (เช่น debug เร็ว หรือรัน pytest)

```bash
# ตรวจสอบ
python --version   # Python 3.12.x หรือใหม่กว่า
```

---

## 3. VS Code Extensions

เปิด VS Code แล้วกด `Ctrl+Shift+X` (Windows/Linux) หรือ `Cmd+Shift+X` (macOS) เพื่อเปิด Extensions

### หมวด: Docker / Container

| Extension | Extension ID | ทำอะไร |
|---|---|---|
| **Container Tools** | `ms-azuretools.vscode-containers` | เห็น container, image, volume ใน sidebar; ดู log, exec shell เข้า container ได้ทันที |
| **Dev Containers** | `ms-vscode-remote.remote-containers` | เปิด VS Code ทำงาน *ภายใน* container โดยตรง — Python IntelliSense ตรงกับ env จริง |

> **หมายเหตุ**: Microsoft เปลี่ยนชื่อ extension "Docker" เป็น "Container Tools" ใน 2025
> ถ้าหาไม่เจอให้ค้นด้วย extension ID `ms-azuretools.vscode-containers`

### หมวด: Git / GitHub

| Extension | Extension ID | ทำอะไร |
|---|---|---|
| **GitLens** | `eamodio.gitlens` | เห็น git blame inline, ประวัติ commit รายบรรทัด, เปรียบเทียบ branch |
| **GitHub Pull Requests** | `GitHub.vscode-pull-request-github` | สร้าง/รีวิว PR ใน VS Code โดยตรง |
| **Git Graph** | `mhutchie.git-graph` | กราฟ branch/commit แบบ visual |

### หมวด: Python

| Extension | Extension ID | ทำอะไร |
|---|---|---|
| **Python** | `ms-python.python` | IntelliSense, run/debug, virtual env |
| **Pylance** | `ms-python.vscode-pylance` | Type checking เร็วกว่า mypy, autocomplete ละเอียด |
| **Ruff** | `charliermarsh.ruff` | Linter + formatter เดียวกับที่ใช้ใน CI |

### หมวด: Database

| Extension | Extension ID | ทำอะไร |
|---|---|---|
| **Database Client** | `cweijan.vscode-database-client2` | เชื่อมต่อ PostgreSQL ดูตาราง/query ผ่าน GUI โดยไม่ต้องเปิด pgAdmin |
| **SQLTools** | `mtxr.sqltools` | อีกทางเลือก เพิ่ม driver `mtxr.sqltools-driver-pg` สำหรับ PostgreSQL |

### หมวด: Config / Markup

| Extension | Extension ID | ทำอะไร |
|---|---|---|
| **YAML** | `redhat.vscode-yaml` | Syntax highlight + validation สำหรับ `.yml` (docker-compose, Bruno, alembic) |
| **Even Better TOML** | `tamasfe.even-better-toml` | สำหรับ `pyproject.toml` |
| **DotENV** | `mikestead.dotenv` | Syntax highlight สำหรับ `.env`, `.env.dev` |

### หมวด: Bruno (API Testing ใน VS Code)

| Extension | Extension ID | ทำอะไร |
|---|---|---|
| **Bruno** | `bruno-api-client.bruno` | เปิดและรัน Bruno collection ใน VS Code โดยตรง (ไม่ต้องเปิด Bruno app แยก) |

---

## 4. ขั้นตอน Setup ครั้งแรก

```bash
# 1. Clone repo
git clone <repo-url>
cd Thai-Synthetic-Voice-Detection-System

# 2. ตรวจสอบว่ามี .env.dev แล้ว (committed ใน git)
cat .env.dev   # ดูค่า default — ใช้ได้เลยสำหรับ dev

# 3. รัน Docker (ครั้งแรกใช้เวลาดาวน์โหลด image ~2-5 นาที)
docker compose up --build

# 4. ตรวจสอบว่าทำงานได้
curl http://localhost:8000/health
# ควรได้: {"status":"ok","model_version":"mock-v0 ...","using_mock_model":true}
```

Swagger UI ที่ http://localhost:8000/docs — ทดสอบ API ได้ทันที

### เปิด pgAdmin (optional)
```bash
docker compose --profile tools up -d
# เข้าที่ http://localhost:5050
# Email: dev@example.com | Password: ดูใน .env.dev
```

### รัน Test
```bash
# จาก container (ไม่ต้องติดตั้ง Python บนเครื่อง)
docker compose exec api pytest -q

# หรือบนเครื่อง local (ต้องมี Python 3.12+ และ pip install -r requirements-dev.txt)
pytest -q
```

---

## 5. การตั้งค่า VS Code สำหรับโปรเจกต์นี้

### เชื่อม Python interpreter กับ virtual env

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements-dev.txt
```

จากนั้น VS Code จะถาม "Select interpreter" — เลือก `.venv` ที่สร้างไว้

### เชื่อม Database Client กับ PostgreSQL

ใช้ค่าจาก `.env.dev`:

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| User | `postgres` |
| Password | `postgres` (หรือค่าใน `.env.dev`) |
| Database | `spoof_detection` |

> **หมายเหตุ**: PostgreSQL จะรับการเชื่อมต่อจากเครื่อง host ที่ port 5432 ก็ต่อเมื่อ `docker compose up` รันอยู่

---

## 6. ปัญหาที่พบบ่อย

**`docker compose up` ค้างหรือ error ตอนรอ DB**
- ตรวจสอบว่า Docker Desktop เปิดอยู่ก่อนรัน compose

**Port 8000 หรือ 5432 ถูกใช้งานแล้ว**
- เปลี่ยน `API_PORT` หรือ `POSTGRES_PORT` ใน `.env.dev` (หรือสร้าง `.env` ใหม่เพื่อ override)

**`alembic upgrade head` ล้มเหลว**
- มักเกิดจาก DB ยังไม่พร้อม — `entrypoint.sh` retry อัตโนมัติแล้ว ถ้ายังไม่ผ่านให้ `docker compose down -v && docker compose up --build`

**Windows: `docker: command not found` ใน WSL**
- เปิด Docker Desktop Settings → Resources → WSL Integration → เปิด toggle สำหรับ distro ที่ใช้

**เปลี่ยน POSTGRES_PASSWORD ใน `.env.dev` แต่ login ไม่ได้**
- Volume เดิมถูก init ด้วยรหัสผ่านเก่าแล้ว ต้องลบ volume: `docker compose down -v`
