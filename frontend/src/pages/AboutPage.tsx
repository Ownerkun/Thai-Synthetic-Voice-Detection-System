import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { api } from '../api/client';
import type { Health } from '../api/types';
import { Icon, type IconName } from '../components/Icon';
import { Gauge } from '../components/ResultView';

const STEPS: { icon: IconName; title: string; text: string }[] = [
  { icon: 'upload', title: '1. ส่งเสียงเข้ามา', text: 'อัปโหลดไฟล์ .wav / .flac หรืออัดจากไมค์ ระบบใช้ 10 วินาทีแรก' },
  { icon: 'wave', title: '2. เตรียมเสียง', text: 'แปลงเป็นเสียงโมโน 16 kHz แล้วหั่นเป็นช่วงละ 4 วินาที' },
  { icon: 'sparkle', title: '3. โมเดลให้คะแนน', text: 'โมเดลดูทีละช่วงว่ามีร่องรอยของเสียงที่สร้างด้วย AI มากแค่ไหน' },
  { icon: 'chart', title: '4. สรุปผล', text: 'เอาคะแนนทุกช่วงมาเฉลี่ย ถ้าเกินเกณฑ์ = น่าจะเป็นเสียง AI' },
];

export function AboutPage() {
  const [health, setHealth] = useState<Health | null>(null);

  const { hash } = useLocation();

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  // มาจากลิงก์ "คะแนนนี้คืออะไร" (/about#read) → เลื่อนไปที่หัวข้ออ่านผล
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView({ block: 'start' });
  }, [hash]);

  return (
    <div className="stack">
      <section className="hero">
        <span className="eyebrow">
          <Icon name="info" size={14} /> เกี่ยวกับระบบ
        </span>
        <h1>
          เสียงจริงไหม<span className="grad-pink">?</span> ทำงานยังไง
        </h1>
        <p className="muted">ระบบตรวจสอบเสียงสังเคราะห์ภาษาไทย ช่วยเช็กว่าเสียงพูดเป็นคนจริงหรือ AI สร้างขึ้น</p>
      </section>

      <section className="steps">
        {STEPS.map((s) => (
          <div key={s.title} className="card step">
            <span className="kpi-icon tone-lavender-icon">
              <Icon name={s.icon} size={20} />
            </span>
            <h3>{s.title}</h3>
            <p className="muted small">{s.text}</p>
          </div>
        ))}
      </section>

      <section className="card stack-sm" id="read">
        <h2>อ่านผลยังไง</h2>
        <div className="about-legend">
          <Gauge value={0.82} verdict="spoof" size={96} />
          <div>
            <p>
              <strong>เปอร์เซ็นต์ในวงกลม</strong> = คะแนนความน่าสงสัยว่าเป็นเสียง AI (เฉลี่ยจากทุกช่วง) ยิ่งสูงยิ่งน่าสงสัย
              คะแนนนี้ยังไม่ใช่ความน่าจะเป็นที่วัดเทียบกับข้อมูลจริง จึงใช้เปรียบเทียบกับเกณฑ์เท่านั้น
            </p>
            <p>
              <strong>เกณฑ์ตัดสิน</strong> = เส้นแบ่งที่ผู้ดูแลตั้งไว้ ถ้าคะแนนเฉลี่ยถึงเกณฑ์ ระบบจะบอกว่า 🤖 เสียง AI
              ถ้าไม่ถึงจะบอกว่า 🙋 เสียงจริง
            </p>
          </div>
        </div>
        <ul className="about-list">
          <li>
            <span className="dot is-spoof" /> <strong>แท่งสีชมพู</strong> ในกราฟคือช่วงที่คะแนนเกินเกณฑ์ ส่วน
            <span className="dot is-real" /> <strong>สีมิ้นต์</strong> คือช่วงปกติ แตะแท่งเพื่อฟังเสียงช่วงนั้นได้ (เฉพาะตอนเพิ่งตรวจ)
          </li>
          <li>
            <span className="tag">อาจตัดต่อ</span> จะขึ้นเมื่อคะแนนแต่ละช่วงต่างกันมาก เช่น บางช่วงเป็นเสียงจริง
            บางช่วงถูกแทรกเสียง AI
          </li>
          <li>
            <span className="tag tag-mid">⚖️ ก้ำกึ่ง</span> จะขึ้นเมื่อคะแนนเฉลี่ยห่างจากเกณฑ์ไม่เกิน 5 จุด ผลแบบนี้ไม่ชัดเจน ควรฟังประกอบ
          </li>
          <li>ผลเป็นการประเมินด้วยสถิติ ไม่ใช่คำตัดสินที่ถูก 100% ควรใช้ประกอบกับหลักฐานอื่นเสมอ</li>
        </ul>
      </section>

      <section className="card stack-sm">
        <h2>
          <Icon name="lock" size={20} /> ความเป็นส่วนตัว
        </h2>
        <ul className="about-list">
          <li>
            <strong>ไม่เก็บไฟล์เสียง</strong> ระบบอ่านเสียงในหน่วยความจำเพื่อให้คะแนน แล้วทิ้งทันที
          </li>
          <li>
            สิ่งที่บันทึกคือข้อมูลประกอบผล ได้แก่ ชื่อไฟล์ ขนาด ความยาว และคะแนน เพื่อใช้ทำสถิติภาพรวมของระบบ
          </li>
          <li>
            ถ้า<strong>ไม่ได้ login</strong> ผลจะไม่ผูกกับบัญชีใด และผลล่าสุดจะเก็บไว้แค่ในเบราว์เซอร์ของคุณเอง
          </li>
          <li>
            ถ้า<strong>login</strong> ผลจะอยู่ในหน้าประวัติของคุณ ลบออกเมื่อไหร่ก็ได้ และ feedback ที่ให้ไว้จะถูกลบไปด้วย
          </li>
          <li>ตรวจเสียงได้โดยไม่ต้องสมัคร ระบบขอแค่อีเมลกับรหัสผ่านเมื่ออยากเก็บประวัติ</li>
        </ul>
      </section>

      <section className="card stack-sm">
        <h2>ข้อจำกัดตอนนี้</h2>
        <ul className="about-list">
          <li>รองรับเฉพาะไฟล์ .wav และ .flac ขนาดไม่เกิน 20 MB ตรวจได้ครั้งละไม่เกิน 10 ไฟล์</li>
          <li>วิเคราะห์ 10 วินาทีแรกของไฟล์เท่านั้น เสียงหลังจากนั้นจะไม่ถูกนำมาคิด</li>
          <li>ยังไม่มีโหมดฟังสดแบบเรียลไทม์</li>
          <li>
            สถานะโมเดล:{' '}
            {health ? (
              health.using_mock_model ? (
                <span className="tag">🧪 โมเดลจำลอง (ผลยังไม่ใช่ของจริง)</span>
              ) : (
                <span className="badge badge-real">✓ {health.model_version}</span>
              )
            ) : (
              <span className="muted">ตรวจสอบไม่ได้</span>
            )}
          </li>
        </ul>
      </section>

      <div className="row" style={{ justifyContent: 'center' }}>
        <Link to="/" className="btn btn-primary">
          <Icon name="sparkle" size={18} /> ลองเช็กเสียงเลย
        </Link>
      </div>
    </div>
  );
}
