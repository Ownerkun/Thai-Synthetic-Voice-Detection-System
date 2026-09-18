# UML Diagram ระบบตรวจสอบเสียงสังเคราะห์ภาษาไทย

โครงงาน SI423-59 | Thai Synthetic Voice Detection System Using Machine Learning

> **ขอบเขตของเอกสารนี้**
> ทุกไดอะแกรมอ้างอิงจาก**โค้ดที่มีอยู่จริงและผ่านการทดสอบแล้ว** (96 unit tests)
> ส่วนที่ยังไม่ได้พัฒนาจะระบุกำกับไว้ว่า *(อยู่นอกขอบเขต / ยังไม่พัฒนา)*

---

## สารบัญ

| # | ไดอะแกรม | ประเภท UML | ตอบคำถามอะไร |
|---|---|---|---|
| 1 | Use Case Diagram | Behavioural | ใครทำอะไรกับระบบได้บ้าง |
| 2 | Context & Data Flow Diagram | Structured Analysis | ข้อมูลไหลจากไหนไปไหน |
| 3 | Class Diagram | Structural | โค้ดมีคลาสอะไร สัมพันธ์กันอย่างไร |
| 4 | Activity Diagram | Behavioural | ขั้นตอนการทำงานตั้งแต่ต้นจนจบ |
| 5 | Sequence Diagram (Offline) | Interaction | ลำดับการคุยกันของแต่ละส่วนในโหมดปกติ |
| 6 | Sequence Diagram (Near Real-Time) | Interaction | ลำดับการคุยกันในโหมด streaming |
| 7 | State Machine Diagram | Behavioural | สถานะของ session การเฝ้าฟังสด |
| 8 | Component Diagram | Structural | โมดูลซอฟต์แวร์และ interface ระหว่างกัน |
| 9 | Deployment Diagram | Structural | ซอฟต์แวร์ไปรันอยู่บนอะไร |
| 10 | Training Pipeline Activity | Behavioural | ขั้นตอนฝั่งวิจัย (เทรน → export) |

---

## 1. Use Case Diagram

แสดงความสามารถของระบบแยกตาม actor
Mermaid ไม่มีสัญลักษณ์ use case มาตรฐาน จึงใช้ flowchart แทน โดยวงรี `(...)` = use case

```mermaid
flowchart LR
  guest(["ผู้ใช้ทั่วไป (Guest)<br/>ไม่ต้องล็อกอิน"])
  reguser(["ผู้ใช้ที่ล็อกอิน<br/>Registered User"])
  admin(["ผู้ดูแลระบบ<br/>Administrator"])
  researcher(["ผู้จัดทำโครงงาน<br/>Researcher"])

  subgraph SYS["ระบบตรวจสอบเสียงสังเคราะห์ภาษาไทย"]
    direction TB
    uc1(["UC1: อัปโหลดไฟล์เสียง"])
    uc2(["UC2: บันทึกเสียงผ่านไมโครโฟน"])
    uc3(["UC3: ดูผลการตรวจสอบ"])
    uc4(["UC4: ดูช่วงเวลาที่น่าสงสัย"])
    uc5(["UC5: เปรียบเทียบหลายไฟล์"])
    uc6(["UC6: ให้ Feedback ความถูกต้อง"])
    uc7(["UC7: ดูประวัติการตรวจสอบ"])
    uc7b(["UC7b: ลบรายการประวัติ"])
    uc8(["UC8: เฝ้าฟังสด Near Real-Time"])
    uc9(["UC9: เข้าสู่ระบบผู้ดูแล"])
    uc10(["UC10: ดูสถิติภาพรวม"])
    uc11(["UC11: ปรับค่า Threshold"])
    uc12(["UC12: เทรนโมเดล"])
    uc13(["UC13: ประเมินผล EER / min-DCF"])
    uc14(["UC14: Export เป็น ONNX"])
  end

  guest --> uc1
  guest --> uc2
  guest --> uc3
  guest --> uc5
  guest --> uc8

  reguser -. "ขยายสิทธิ์จาก" .-> guest
  reguser --> uc6
  reguser --> uc7

  admin --> uc9
  admin --> uc10
  admin --> uc11

  researcher --> uc12
  researcher --> uc13
  researcher --> uc14

  uc1 -. include .-> uc3
  uc2 -. include .-> uc3
  uc3 -. extend .-> uc4
  uc7b -. extend .-> uc7
  uc9 -. include .-> uc10
  uc9 -. include .-> uc11
  uc12 -. include .-> uc13
  uc13 -. include .-> uc14

  classDef actor fill:#EAF3EF,stroke:#2E5E4E,stroke-width:2px,color:#1A3A30
  classDef regactor fill:#D6E8F6,stroke:#2E5E8E,stroke-width:2px,color:#1A303A
  classDef uc fill:#FFFFFF,stroke:#2E5E4E,color:#1F2A26
  classDef admincase fill:#FBE9D6,stroke:#D9822B,color:#1F2A26
  class guest,admin,researcher actor
  class reguser regactor
  class uc1,uc2,uc3,uc4,uc5,uc6,uc7,uc7b,uc8 uc
  class uc9,uc10,uc11,uc12,uc13,uc14 admincase
```

**หมายเหตุการออกแบบ**
- UC1–UC5, UC8 **ไม่ต้อง login** ตามหลัก Data Minimization (พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล)
- UC6, UC7, UC7b **ต้อง login** Feedback และประวัติต้องผูกกับ `user_id` ในฐานข้อมูล guest ไม่สามารถดำเนินการใด ๆ เหล่านี้ได้ (API คืน 401 ถ้าไม่มี token)
- UC7b (ลบประวัติ) เป็น extend ของ UC7: ผู้ใช้ลบได้เฉพาะรายการของตนเอง การลบจะลบ SegmentScore และ Feedback ที่เกี่ยวข้องด้วย (cascade)
- UC9–UC11 **ต้อง login (Admin)** เพราะกระทบระบบส่วนรวม (RBAC แบบชั้นเดียว)
- UC12–UC14 เป็นงานฝั่งวิจัย ทำผ่าน command line ไม่ได้อยู่ในเว็บแอป

---

## 2. Context Diagram และ Data Flow Diagram

### 2.1 Context Diagram (DFD Level 0)

```mermaid
flowchart LR
  U["ผู้ใช้งานทั่วไป"]
  A["ผู้ดูแลระบบ"]
  S(("ระบบตรวจสอบ<br/>เสียงสังเคราะห์<br/>ภาษาไทย"))

  U -- "ไฟล์เสียง / คำขอตรวจสอบ" --> S
  S -- "ผลลัพธ์ + ช่วงที่น่าสงสัย" --> U
  U -- "Feedback ถูก/ผิด" --> S

  A -- "คำขอสถิติ / ค่า Threshold ใหม่" --> S
  S -- "สถิติภาพรวม" --> A

  classDef ext fill:#EAF3EF,stroke:#2E5E4E,stroke-width:2px,color:#1A3A30
  classDef sys fill:#1A3A30,stroke:#1A3A30,color:#FFFFFF
  class U,A ext
  class S sys
```

### 2.2 Data Flow Diagram (DFD Level 1)

```mermaid
flowchart TB
  U["ผู้ใช้งาน"]
  A["ผู้ดูแลระบบ"]

  P1["P1: รับและตรวจสอบไฟล์<br/>validate + resample"]
  P2["P2: แบ่งเป็นช่วง<br/>segment + pad"]
  P3["P3: อนุมานด้วยโมเดล<br/>ONNX Runtime"]
  P4["P4: ปรับเทียบและตัดสิน<br/>temperature + threshold"]
  P5["P5: รวบรวมสถิติ"]

  D1[("D1: model.onnx<br/>+ model.json")]
  D2[("D2: ผลลัพธ์และ Feedback<br/>PostgreSQL")]
  D3[("D3: ค่า Threshold ปัจจุบัน")]

  U -- "ไฟล์เสียง" --> P1
  P1 -- "สัญญาณ 16 kHz mono" --> P2
  P2 -- "ช่วงเสียงความยาวคงที่" --> P3
  D1 -- "กราฟโมเดล + metadata" --> P3
  P3 -- "logits ต่อช่วง" --> P4
  D3 -- "threshold" --> P4
  P4 -- "ผลลัพธ์ + ช่วงที่น่าสงสัย" --> U
  P4 -- "metadata ผลลัพธ์<br/>ไม่มีไฟล์เสียง" --> D2

  U -- "Feedback" --> D2
  D2 -- "ข้อมูลสะสม" --> P5
  P5 -- "สถิติภาพรวม" --> A
  A -- "ค่า Threshold ใหม่" --> D3

  classDef proc fill:#FFFFFF,stroke:#2E5E4E,stroke-width:2px,color:#1F2A26
  classDef store fill:#EAF3EF,stroke:#2E5E4E,color:#1A3A30
  classDef ext fill:#FBE9D6,stroke:#D9822B,color:#1F2A26
  class P1,P2,P3,P4,P5 proc
  class D1,D2,D3 store
  class U,A ext
```

> **จุดสำคัญด้านความเป็นส่วนตัว** ไม่มีลูกศรใดที่ส่ง "ไฟล์เสียง" เข้าสู่ D2
> ไฟล์เสียงถูกใช้แล้วปล่อยทิ้งใน memory ทันที (ดู `scripts/serve_fastapi.py`)

---

## 3. Class Diagram

อ้างอิงจากคลาสจริงในโปรเจกต์ แยกเป็น 3 กลุ่มตามหน้าที่

### 3.1 กลุ่มจัดการข้อมูล (`src/data/`)

```mermaid
classDiagram
  class Utterance {
    +str path
    +str label
    +str speaker
    +str attack
    +target() int
    +is_bonafide() bool
  }

  class SpoofDataset {
    +List~Utterance~ utterances
    +int num_samples
    +int sample_rate
    +bool train
    +Callable augment
    +__len__() int
    +__getitem__(index) tuple
    +load_waveform(index) Tensor
  }

  class RawBoost {
    +int algo
    +float probability
    +set_epoch(epoch) void
    +__call__(waveform, sample_rate) Tensor
  }

  class ManifestIO {
    <<module>>
    +write_manifest(utterances, path) Path
    +read_manifest(path) List~Utterance~
    +label_counts(utterances) dict
    +speaker_overlap(a, b) set
  }

  class Adapters {
    <<module>>
    +from_asvspoof_protocol(protocol, audio_dir) List~Utterance~
    +from_directory_layout(root) List~Utterance~
    +from_csv(path) List~Utterance~
  }

  SpoofDataset o-- Utterance : contains
  SpoofDataset ..> RawBoost : uses when training
  ManifestIO ..> Utterance : reads/writes
  Adapters ..> Utterance : produces
```

### 3.2 กลุ่มโมเดล (`src/models/`)

```mermaid
classDiagram
  class Module {
    <<abstract>>
    +forward(x) Tensor
  }

  class SincConv1d {
    +int out_channels
    +int kernel_size
    +Parameter low_hz_
    +Parameter band_hz_
    +build_filters() Tensor
    +forward(x) Tensor
  }

  class ResidualEncoder {
    +int out_channels
    +forward(x) Tensor
  }

  class GraphAttentionLayer {
    +forward(x) Tensor
  }

  class HtrgGraphAttentionLayer {
    +forward(x1, x2, master) tuple
  }

  class GraphPool {
    +float ratio
    +forward(x) Tensor
  }

  class AASISTBackend {
    +int graph_dim
    +forward(feature_map) Tensor
  }

  class SincAASIST {
    +forward(waveform) Tensor
  }

  class XLSRAASIST {
    +bool ssl_frozen
    +freeze_ssl() void
    +unfreeze_ssl() void
    +forward(waveform) Tensor
  }

  class LCNNRealtime {
    +int chunk_samples
    +chunk_seconds() float
    +spectrogram(waveform) Tensor
    +forward(waveform) Tensor
  }

  class ModelFactory {
    <<module>>
    +build_model(config) Module
    +available_models() list
  }

  Module <|-- SincConv1d
  Module <|-- ResidualEncoder
  Module <|-- GraphAttentionLayer
  Module <|-- HtrgGraphAttentionLayer
  Module <|-- GraphPool
  Module <|-- AASISTBackend
  Module <|-- SincAASIST
  Module <|-- XLSRAASIST
  Module <|-- LCNNRealtime

  AASISTBackend *-- GraphAttentionLayer
  AASISTBackend *-- HtrgGraphAttentionLayer
  AASISTBackend *-- GraphPool

  SincAASIST *-- SincConv1d : front-end
  SincAASIST *-- ResidualEncoder
  SincAASIST *-- AASISTBackend : back-end

  XLSRAASIST *-- ResidualEncoder
  XLSRAASIST *-- AASISTBackend : back-end เดิม

  ModelFactory ..> SincAASIST : creates
  ModelFactory ..> XLSRAASIST : creates
  ModelFactory ..> LCNNRealtime : creates
```

> **จุดที่ไดอะแกรมนี้อธิบายได้ชัดกว่าคำพูด** `SincAASIST` กับ `XLSRAASIST`
> ใช้ `AASISTBackend` **ตัวเดียวกัน** ต่างกันแค่ front-end

### 3.3 กลุ่มอนุมานและ serving

```mermaid
classDiagram
  class Calibrator {
    +float temperature
    +float threshold
    +probability(logits) ndarray
    +percentage(logits) ndarray
    +verdict(probability) str
    +to_dict() dict
    +from_dict(payload) Calibrator
  }

  class Segment {
    +int index
    +float start_seconds
    +float end_seconds
    +percentage() float
    +verdict(threshold) str
    +to_dict(threshold) dict
  }

  class FileAnalysis {
    +List~Segment~ segments
    +scored_segments() List~Segment~
    +mean_probability() float
    +max_probability() float
    +verdict() str
    +rtf() float
    +suspicious_segments(limit) List~Segment~
  }

  class SpoofAnalyzer {
    <<PyTorch — ใช้ตอนวิจัย>>
    +int segment_samples
    +int sample_rate
    +from_checkpoint(path) SpoofAnalyzer
    +analyze(waveform) FileAnalysis
    +analyze_file(path) FileAnalysis
  }

  class OnnxSpoofAnalyzer {
    <<ONNX Runtime — ใช้ตอน deploy>>
    +dict meta
    +int segment_samples
    +float temperature
    +float threshold
    +analyze(waveform) dict
    +analyze_file(file) dict
  }

  class SegmentResult {
    +int index
    +float start_seconds
    +float end_seconds
    +float spoof_probability
    +bool is_spoof
  }

  SpoofAnalyzer --> FileAnalysis : produces
  SpoofAnalyzer *-- Calibrator
  FileAnalysis o-- Segment
  OnnxSpoofAnalyzer --> SegmentResult : produces

  note for OnnxSpoofAnalyzer "อ่าน temperature/threshold จาก model.json<br/>ไม่ต้องพึ่ง torch ให้ผลตรงกับ SpoofAnalyzer ที่ ~1e-7"
```

---

## 4. Activity Diagram การตรวจสอบไฟล์เสียง

```mermaid
flowchart TB
  start(["เริ่ม"]) --> choose{"เลือกวิธี<br/>นำเข้าเสียง"}
  choose -- "อัปโหลด" --> upload["เลือกไฟล์จากอุปกรณ์"]
  choose -- "อัดเสียง" --> record["บันทึกผ่านไมโครโฟน"]

  upload --> validate{"ไฟล์ถูกต้อง<br/>และขนาดไม่เกิน?"}
  record --> validate
  validate -- "ไม่ผ่าน" --> err["แสดงข้อความแจ้งเตือน"] --> choose
  validate -- "ผ่าน" --> resample["แปลงเป็น mono 16 kHz"]

  resample --> lenChk{"ยาวกว่า<br/>1 ช่วงหรือไม่?"}
  lenChk -- "สั้นกว่า" --> pad["เติมด้วยการวนซ้ำ<br/>ไม่ใช่เติมศูนย์"]
  lenChk -- "ยาวกว่า" --> split["แบ่งเป็นหลายช่วง"]

  pad --> infer["อนุมานด้วย ONNX Runtime"]
  split --> infer
  infer --> calib["ปรับเทียบด้วย temperature"]
  calib --> aggregate["รวมคะแนน mean และ max"]

  aggregate --> partial{"mean ต่ำ<br/>แต่ max สูง?"}
  partial -- "ใช่" --> warnPartial["ตั้งธงอาจถูกตัดต่อเฉพาะจุด"]
  partial -- "ไม่ใช่" --> decide
  warnPartial --> decide{"คะแนนเกิน<br/>threshold?"}

  decide -- "เกิน" --> spoof["แสดงผล: มีแนวโน้มเป็นเสียงสังเคราะห์"]
  decide -- "ไม่เกิน" --> bona["แสดงผล: มีแนวโน้มเป็นเสียงจริง"]

  spoof --> chart["แสดงกราฟช่วงที่น่าสงสัย"]
  bona --> chart
  chart --> save["บันทึกผลลง Local Storage<br/>ไม่เก็บไฟล์เสียง"]
  save --> chkLogin{"ผู้ใช้<br/>ล็อกอินอยู่?"}
  chkLogin -- "ไม่ได้ล็อกอิน" --> finish
  chkLogin -- "ล็อกอินแล้ว" --> fb{"ต้องการให้<br/>Feedback?"}
  fb -- "ให้" --> store[("บันทึก Feedback<br/>ลงฐานข้อมูล")]
  fb -- "ไม่ให้" --> finish
  store --> finish(["จบ"])

  classDef act fill:#FFFFFF,stroke:#2E5E4E,color:#1F2A26
  classDef dec fill:#FBE9D6,stroke:#D9822B,color:#1F2A26
  classDef res fill:#1A3A30,stroke:#1A3A30,color:#FFFFFF
  class upload,record,resample,pad,split,infer,calib,aggregate,chart,save,warnPartial,err act
  class choose,validate,lenChk,decide,fb,partial,chkLogin dec
  class spoof,bona res
```

---

## 5. Sequence Diagram โหมดปกติ (Offline / Post-hoc)

```mermaid
sequenceDiagram
  autonumber
  actor U as ผู้ใช้งาน
  participant W as Web App<br/>(Streamlit)
  participant API as FastAPI<br/>/predict
  participant ENG as OnnxSpoofAnalyzer
  participant ORT as ONNX Runtime
  participant DB as PostgreSQL

  U->>W: เลือก/อัดไฟล์เสียง
  W->>W: ตรวจขนาดและนามสกุลไฟล์
  W->>API: POST multipart/form-data (HTTPS)
  activate API

  API->>API: ตรวจขนาด <= 20 MB
  alt ไฟล์ว่างหรือใหญ่เกิน
    API-->>W: 400 / 413 พร้อมข้อความแจ้งเหตุ
  else ไฟล์ผ่านการตรวจ
    API->>ENG: analyze_file(BytesIO)
    activate ENG
    ENG->>ENG: mono + resample 16 kHz
    ENG->>ENG: แบ่งเป็นช่วงความยาวคงที่

    loop ทุก batch ของช่วงเสียง
      ENG->>ORT: run(waveform)
      ORT-->>ENG: logits
    end

    ENG->>ENG: temperature scaling + softmax
    ENG->>ENG: รวมคะแนน mean / max
    ENG-->>API: report (verdict, segments)
    deactivate ENG

    API->>DB: บันทึก metadata ผลลัพธ์<br/>(ไม่มีไฟล์เสียง)
    API-->>W: 200 OK + JSON
  end
  deactivate API

  W-->>U: แสดงผล + กราฟช่วงที่น่าสงสัย
  Note over API,DB: ไฟล์เสียงถูกปล่อยจาก memory ทันที<br/>หลังประมวลผลเสร็จ (Data Minimization)

  opt ผู้ใช้ล็อกอินแล้วเท่านั้น (มี Authorization token)
    U->>W: กด Feedback ถูก/ผิด
    W->>API: POST /history/{id}/feedback<br/>(Authorization: Bearer token)
    API->>API: ตรวจสอบ token — 401 ถ้าไม่มีหรือหมดอายุ
    API->>DB: บันทึก Feedback (user_id ผูกกับ token)
    API-->>W: 201 Created
    W-->>U: แสดงว่า Feedback ถูกบันทึกแล้ว
  end

  opt ผู้ใช้ต้องการลบรายการประวัติ (ต้องล็อกอิน)
    U->>W: กดลบรายการประวัติ
    W->>API: DELETE /history/{id}<br/>(Authorization: Bearer token)
    API->>API: ตรวจสอบ token + ความเป็นเจ้าของรายการ
    alt ไม่ใช่รายการของผู้ใช้
      API-->>W: 404 Not Found
    else เป็นรายการของผู้ใช้
      API->>DB: ลบ DetectionRecord<br/>(cascade: SegmentScore, Feedback)
      API-->>W: 204 No Content
      W-->>U: นำรายการออกจากหน้าประวัติ
    end
  end
```

---

## 6. Sequence Diagram โหมด Near Real-Time

> *(สถานะ: ยังเป็นการศึกษาเชิงสำรวจ — ยังไม่มีงานวิจัยรองรับในบริบทภาษาไทย)*

```mermaid
sequenceDiagram
  autonumber
  actor U as ผู้ใช้งาน
  participant W as Web App
  participant WS as WebSocket<br/>Endpoint
  participant ENG as OnnxSpoofAnalyzer<br/>(LCNN)
  participant ORT as ONNX Runtime

  U->>W: กดเริ่มเฝ้าฟัง
  W->>W: ขออนุญาตใช้ไมโครโฟน
  W->>WS: เปิดการเชื่อมต่อ
  activate WS

  loop ทุก ~1 วินาที จนกว่าผู้ใช้จะหยุด
    W->>WS: ส่ง chunk เสียง
    WS->>ENG: score chunk
    ENG->>ORT: run(chunk)
    ORT-->>ENG: logits
    ENG-->>WS: คะแนนของ chunk
    WS-->>W: อัปเดตคะแนนสด
    W-->>U: แสดงมิเตอร์ + กราฟ 10 ช่วงล่าสุด
  end

  U->>W: กดหยุดฟัง
  W->>WS: ปิดการเชื่อมต่อ
  WS->>WS: รวมคะแนนทุก chunk
  WS-->>W: คะแนนสรุประดับสาย
  deactivate WS
  W-->>U: แสดงผลสรุป + คำเตือนว่าเป็นค่าเฝ้าระวัง

  Note over W,ORT: ใช้ LCNN (0.02M params) เพราะ XLS-R หนักเกินไป<br/>แลกด้วยความแม่นยำที่ลดลง
```

---

## 7. State Machine Diagram Session การเฝ้าฟังสด

```mermaid
stateDiagram-v2
  [*] --> Idle : เปิดหน้าจอ

  Idle --> RequestingMic : กดเริ่มเฝ้าฟัง
  RequestingMic --> Idle : ผู้ใช้ปฏิเสธสิทธิ์
  RequestingMic --> Connecting : ได้รับสิทธิ์ไมโครโฟน

  Connecting --> Listening : เชื่อมต่อสำเร็จ
  Connecting --> Error : เชื่อมต่อไม่สำเร็จ

  Listening --> Scoring : ครบ 1 chunk
  Scoring --> Listening : อัปเดตคะแนนบนหน้าจอ

  Listening --> Summarising : ผู้ใช้กดหยุด
  Scoring --> Summarising : ผู้ใช้กดหยุด
  Listening --> Error : การเชื่อมต่อหลุด

  Summarising --> Finished : คำนวณคะแนนรวมเสร็จ
  Finished --> Idle : เริ่มรอบใหม่
  Error --> Idle : ผู้ใช้กดลองใหม่

  Finished --> [*]

  note right of Listening
    บัฟเฟอร์เสียงถูกทับด้วยข้อมูลใหม่เรื่อย ๆ
    ไม่มีการเขียนลงดิสก์
  end note
```

---

## 8. Component Diagram

```mermaid
flowchart TB
  subgraph FE["Frontend Layer"]
    ui["Web UI<br/>Streamlit"]
    adminui["Admin Dashboard"]
  end

  subgraph BE["Backend Layer"]
    api["REST API<br/>FastAPI"]
    wsapi["WebSocket API<br/>(ยังไม่พัฒนา)"]
    engine["Inference Engine<br/>src/onnx_infer.py"]
    calib["Calibration<br/>src/calibration.py"]
  end

  subgraph ML["Model Artefacts"]
    onnx[["model.onnx"]]
    meta[["model.json<br/>sample_rate / threshold"]]
  end

  subgraph RS["Research Layer (Command Line)"]
    train["src/train.py"]
    eval["src/evaluate.py"]
    export["scripts/export_onnx.py"]
    models["src/models/*"]
    data["src/data/*"]
  end

  subgraph ST["Storage"]
    db[("PostgreSQL<br/>metadata + feedback")]
    local[("Browser Local Storage<br/>ประวัติผู้ใช้")]
  end

  ui -->|HTTPS| api
  adminui -->|HTTPS| api
  ui -.->|"อนาคต"| wsapi
  api --> engine
  engine --> calib
  engine --> onnx
  engine --> meta
  api --> db
  ui --> local

  data --> train
  models --> train
  train --> eval
  eval --> export
  export --> onnx
  export --> meta

  classDef fe fill:#EAF3EF,stroke:#2E5E4E,color:#1A3A30
  classDef be fill:#FFFFFF,stroke:#2E5E4E,color:#1F2A26
  classDef ml fill:#FBE9D6,stroke:#D9822B,color:#1F2A26
  classDef rs fill:#F4F8F6,stroke:#8A9A94,color:#1F2A26
  class ui,adminui fe
  class api,wsapi,engine,calib be
  class onnx,meta ml
  class train,eval,export,models,data rs
```

> Research Layer กับ Backend Layer **ไม่แชร์ dependency กัน**
> ฝั่ง deploy ต้องการแค่ `onnxruntime + numpy + soundfile` ไม่ต้องติดตั้ง
> `torch` และ `transformers` (ประหยัดหลาย GB และ cold start เร็วกว่ามาก)

---

## 9. Deployment Diagram

```mermaid
flowchart TB
  subgraph client["อุปกรณ์ผู้ใช้"]
    browser["เว็บเบราว์เซอร์<br/>+ Local Storage"]
  end

  subgraph server["เซิร์ฟเวอร์ (Docker)"]
    subgraph c1["Container: web"]
      st["Streamlit"]
    end
    subgraph c2["Container: api"]
      fa["FastAPI + Uvicorn"]
      ortnode["ONNX Runtime<br/>CPUExecutionProvider"]
      vol[["Volume: /models<br/>model.onnx + model.json"]]
    end
    subgraph c3["Container: db"]
      pg[("PostgreSQL")]
    end
  end

  subgraph dev["เครื่องสำหรับเทรน (Colab / Kaggle GPU)"]
    gpu["PyTorch + CUDA<br/>เทรนและ export"]
  end

  browser -- "HTTPS" --> st
  st -- "HTTP ภายใน" --> fa
  fa --> ortnode
  ortnode --> vol
  fa -- "TCP 5432" --> pg
  gpu -. "คัดลอกไฟล์โมเดล<br/>ตอน deploy" .-> vol

  classDef node fill:#FFFFFF,stroke:#2E5E4E,color:#1F2A26
  classDef store fill:#EAF3EF,stroke:#2E5E4E,color:#1A3A30
  classDef gpunode fill:#FBE9D6,stroke:#D9822B,color:#1F2A26
  class browser,st,fa,ortnode node
  class pg,vol store
  class gpu gpunode
```

---

## 10. Activity Diagram ขั้นตอนฝั่งวิจัย (เทรน → Export)

```mermaid
flowchart TB
  s(["เริ่ม"]) --> prep["แปลง protocol เป็น manifest<br/>src/data/adapters.py"]
  prep --> check{"speaker overlap<br/>ระหว่าง split?"}
  check -- "พบ" --> warn["แจ้งเตือน identity leakage<br/>แก้ไข split ก่อน"] --> prep
  check -- "ไม่พบ" --> cfg["กำหนดค่าใน YAML config"]

  cfg --> build["build_model(config)"]
  build --> which{"เลือกโมเดล"}
  which -- "sinc_aasist" --> m1["SincConv + AASIST"]
  which -- "xlsr_aasist" --> m2["XLS-R + AASIST<br/>freeze SSL ตอนแรก"]
  which -- "lcnn_realtime" --> m3["LCNN"]

  m1 --> loop
  m2 --> loop
  m3 --> loop["วนเทรนทีละ epoch"]

  loop --> aug["RawBoost augmentation<br/>จำลองสัญญาณโทรศัพท์"]
  aug --> fwd["forward + loss + backward"]
  fwd --> unf{"ถึง epoch<br/>ปลดล็อก SSL?"}
  unf -- "ใช่" --> unfreeze["unfreeze_ssl()<br/>สร้าง optimizer ใหม่ lr ต่ำลง"] --> devval
  unf -- "ไม่ใช่" --> devval["ประเมินบน dev: EER + min-DCF"]

  devval --> best{"EER ดีกว่าเดิม?"}
  best -- "ใช่" --> savec["บันทึก checkpoint + calibration"]
  best -- "ไม่" --> more
  savec --> more{"ครบทุก epoch?"}
  more -- "ยัง" --> loop
  more -- "ครบ" --> evalset["ประเมินบน eval set<br/>แยกผลตาม attack"]

  evalset --> exp["export_onnx.py"]
  exp --> parity{"ONNX ตรงกับ<br/>PyTorch?"}
  parity -- "ไม่ตรง" --> stop["หยุด"]
  parity -- "ตรง" --> done(["ได้ model.onnx + model.json<br/>พร้อม deploy"])

  classDef act fill:#FFFFFF,stroke:#2E5E4E,color:#1F2A26
  classDef dec fill:#FBE9D6,stroke:#D9822B,color:#1F2A26
  classDef bad fill:#F6E4DC,stroke:#B84C3E,color:#B84C3E
  classDef good fill:#1A3A30,stroke:#1A3A30,color:#FFFFFF
  class prep,cfg,build,m1,m2,m3,loop,aug,fwd,unfreeze,devval,savec,evalset,exp,warn act
  class check,which,unf,best,more,parity dec
  class stop bad
  class done good
```

---

## ภาคผนวก: ตารางตรวจสอบขอบเขต

| ส่วน | สถานะในโค้ดจริง | อ้างอิงไฟล์ |
|---|---|---|
| SincConv + AASIST | พัฒนาและทดสอบแล้ว | `src/models/sinc_aasist.py` |
| XLS-R + AASIST | พัฒนาและทดสอบแล้ว | `src/models/xlsr_aasist.py` |
| LCNN (real-time) | พัฒนาและทดสอบแล้ว | `src/models/realtime.py` |
| RawBoost augmentation | พัฒนาและทดสอบแล้ว | `src/data/rawboost.py` |
| EER / min-DCF | พัฒนาและทดสอบแล้ว | `src/metrics/eer.py` |
| Temperature calibration | พัฒนาและทดสอบแล้ว | `src/calibration.py` |
| ONNX export + parity check | พัฒนาและทดสอบแล้ว | `scripts/export_onnx.py` |
| ONNX inference engine | พัฒนาและทดสอบแล้ว | `src/onnx_infer.py` |
| FastAPI backend | ตัวอย่างอ้างอิง ทดสอบรันได้ | `scripts/serve_fastapi.py` |
| Streamlit UI | **ยังไม่พัฒนา** (มีเพียง UX mockup) | — |
| PostgreSQL + Feedback | **ยังไม่พัฒนา** | — |
| WebSocket streaming | **ยังไม่พัฒนา** (ออกแบบไว้เท่านั้น) | — |
| Admin authentication | **ยังไม่พัฒนา** | — |

> ไดอะแกรมที่ 6, 7 และส่วนที่ทำเครื่องหมาย *(ยังไม่พัฒนา)* เป็นการออกแบบล่วงหน้า
