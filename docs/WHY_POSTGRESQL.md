# ทำไมเลือก PostgreSQL

> เอกสารนี้บันทึกเหตุผลที่เลือก PostgreSQL เป็น database หลักของระบบ

## เหตุผลหลัก

| ประเด็น | เหตุผล |
|---|---|
| ข้อมูลเป็นแบบ relational ชัดเจน | `UserAccount → DetectionRecord → SegmentScore`, `DetectionRecord → Feedback`, `AdminAccount → ThresholdSetting` ล้วนมี foreign key ตรงตาม Class Diagram ที่ออกแบบไว้แล้ว — ไม่ใช่ข้อมูลแบบ document/schema-less ที่ MongoDB ถนัด |
| ต้องการ referential integrity | เช่น ลบ user แล้วต้องลบประวัติที่เกี่ยวข้องตาม (`ON DELETE CASCADE`), Feedback ต้องอ้างอิง detection ที่มีอยู่จริง Postgres บังคับให้ผ่าน FK constraint ได้เลย ไม่ต้องเขียน logic ตรวจเองฝั่ง backend |
| ThresholdSetting เป็นประวัติที่ห้ามเสีย | ACID ของ Postgres รับประกันว่าเขียนสำเร็จแล้วไม่หาย/ไม่ทับกันเวลามีคนแก้พร้อมกัน |
| ทีมงานยังไม่ได้เลือก frontend | frontend คุยกับ backend ผ่าน REST/JSON เท่านั้น ไม่แตะ database โดยตรง ดังนั้นตัวเลือก DB ไม่ผูกกับ framework ฝั่ง frontend เลย เปลี่ยน DB ทีหลังก็ไม่กระทบ frontend |
| ฟรี, มี official Docker image, เบา | `postgres:16-alpine` ใช้ resource น้อย |

## เมื่อไหรควรพิจารณา MongoDB แทน

ถ้าในอนาคตมีความต้องการใดข้อใดข้อหนึ่งต่อไปนี้ ค่อยประเมินอีกครั้ง:

- ต้องการ full-text search เสียง/ข้อความที่ซับซ้อน
- schema เปลี่ยนบ่อยมากจนการทำ migration ยุ่งยาก
- ปริมาณ document-like data เพิ่มขึ้นมากกว่า relational data

ณ ขอบเขตปัจจุบัน PostgreSQL เหมาะกว่า MongoDB อย่างชัดเจน
