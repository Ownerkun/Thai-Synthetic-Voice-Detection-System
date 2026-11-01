import type { SegmentResult, Verdict } from '../api/types';
import { dateTime, pct, seconds } from './format';
import { isBorderline, modelLabel } from './result';

// สร้างรูปการ์ดผลตรวจ (A6) วาดเองบน canvas ไม่ต้องใช้ library
// สีคงที่โทนสว่างเสมอ เพื่อให้แนบรายงาน/ส่งต่อแล้วอ่านง่ายไม่ว่าแอปจะอยู่ในโหมดไหน

export interface ResultImageInput {
  filename: string;
  verdict: Verdict;
  meanProbability: number;
  maxProbability: number;
  threshold: number;
  durationSeconds: number;
  possiblePartialSpoof: boolean;
  modelVersion: string;
  segments: SegmentResult[];
  checkedAt?: string | null;
}

const W = 1080;
const H = 1350;
const C = {
  bg1: '#efe9ff',
  bg2: '#ffe6ef',
  card: '#ffffff',
  ink: '#2b2540',
  muted: '#6a6283',
  track: '#f1ecfb',
  spoof: '#ff8fb8',
  spoofInk: '#b8305f',
  real: '#5fcf9f',
  realInk: '#137a55',
  warn: '#84560a',
  warnBg: '#fff3d9',
  line: '#e8e0f6',
  lav: '#7c5cff',
};
const HEAD = "'Prompt', 'Anuphan', sans-serif";
const BODY = "'Anuphan', 'Prompt', sans-serif";

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function fitText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string {
  if (ctx.measureText(text).width <= maxWidth) return text;
  let t = text;
  while (t.length > 1 && ctx.measureText(`${t}…`).width > maxWidth) t = t.slice(0, -1);
  return `${t}…`;
}

export async function drawResultImage(r: ResultImageInput): Promise<Blob> {
  await document.fonts?.ready;
  const canvas = document.createElement('canvas');
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('canvas unavailable');

  const spoof = r.verdict === 'spoof';
  const accent = spoof ? C.spoof : C.real;
  const accentInk = spoof ? C.spoofInk : C.realInk;

  // พื้นหลัง + การ์ด
  const bg = ctx.createLinearGradient(0, 0, W, H);
  bg.addColorStop(0, C.bg1);
  bg.addColorStop(1, C.bg2);
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = C.card;
  roundRect(ctx, 60, 60, W - 120, H - 120, 56);
  ctx.fill();

  // หัว
  ctx.fillStyle = C.lav;
  ctx.font = `700 40px ${HEAD}`;
  ctx.fillText('เสียงจริงไหม?', 120, 160);
  ctx.fillStyle = C.muted;
  ctx.font = `400 28px ${BODY}`;
  ctx.fillText('ผลตรวจเสียงสังเคราะห์ภาษาไทย', 120, 205);
  ctx.fillText(fitText(ctx, `ไฟล์: ${r.filename}`, W - 240), 120, 250);

  // วงแหวนคะแนน
  const cx = 280;
  const cy = 470;
  const radius = 150;
  ctx.lineWidth = 46;
  ctx.lineCap = 'round';
  ctx.strokeStyle = C.track;
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.stroke();
  ctx.strokeStyle = accent;
  ctx.beginPath();
  ctx.arc(cx, cy, radius, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * Math.max(0.005, r.meanProbability));
  ctx.stroke();
  ctx.fillStyle = C.ink;
  ctx.textAlign = 'center';
  ctx.font = `700 72px ${HEAD}`;
  ctx.fillText(pct(r.meanProbability, 0), cx, cy + 18);
  ctx.fillStyle = C.muted;
  ctx.font = `400 24px ${BODY}`;
  ctx.fillText('คะแนนความน่าสงสัย', cx, cy + 60);
  ctx.textAlign = 'left';

  // คำตัดสิน
  ctx.fillStyle = accentInk;
  ctx.font = `700 54px ${HEAD}`;
  ctx.fillText(spoof ? 'น่าจะเป็นเสียง AI' : 'น่าจะเป็นเสียงคนจริง', 500, 440);
  ctx.fillStyle = C.muted;
  ctx.font = `400 28px ${BODY}`;
  ctx.fillText(`เกณฑ์ตัดสิน ${pct(r.threshold, 0)} · สูงสุดรายช่วง ${pct(r.maxProbability, 0)}`, 500, 495);
  ctx.fillText(`วิเคราะห์ ${seconds(r.durationSeconds)} · ${r.segments.length} ช่วง`, 500, 540);

  // แถบเตือน
  const notes: string[] = [];
  if (isBorderline(r.meanProbability, r.threshold)) notes.push('ก้ำกึ่ง: คะแนนใกล้เกณฑ์มาก ควรใช้หลักฐานอื่นประกอบ');
  if (r.possiblePartialSpoof) notes.push('คะแนนแต่ละช่วงต่างกันมาก เสียงอาจถูกตัดต่อบางส่วน');
  let y = 690;
  for (const note of notes) {
    ctx.fillStyle = C.warnBg;
    roundRect(ctx, 120, y, W - 240, 70, 20);
    ctx.fill();
    ctx.fillStyle = C.warn;
    ctx.font = `500 28px ${BODY}`;
    ctx.fillText(fitText(ctx, note, W - 300), 150, y + 45);
    y += 90;
  }

  // กราฟรายช่วง
  const top = Math.max(y + 30, 820);
  const chartH = 260;
  const left = 120;
  const width = W - 240;
  ctx.fillStyle = C.ink;
  ctx.font = `600 30px ${HEAD}`;
  ctx.fillText('คะแนนรายช่วงเวลา', left, top);
  const base = top + 40 + chartH;
  const total = r.segments[r.segments.length - 1]?.end_seconds || 1;
  const gap = 14;
  const usable = width - gap * Math.max(0, r.segments.length - 1);
  let x = left;
  ctx.font = `500 22px ${BODY}`;
  ctx.textAlign = 'center';
  for (const s of r.segments) {
    const w = Math.max(18, (Math.max(s.end_seconds - s.start_seconds, 0.01) / total) * usable);
    const h = Math.max(6, s.spoof_probability * chartH);
    ctx.fillStyle = s.is_spoof ? C.spoof : C.real;
    roundRect(ctx, x, base - h, w, h, 14);
    ctx.fill();
    ctx.fillStyle = C.muted;
    ctx.fillText(pct(s.spoof_probability, 0), x + w / 2, base - h - 12);
    ctx.fillText(`${s.start_seconds.toFixed(0)}–${s.end_seconds.toFixed(0)} วิ`, x + w / 2, base + 34);
    x += w + gap;
  }
  ctx.textAlign = 'left';
  // เส้นเกณฑ์
  const ty = base - r.threshold * chartH;
  ctx.setLineDash([12, 10]);
  ctx.strokeStyle = C.muted;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(left, ty);
  ctx.lineTo(left + width, ty);
  ctx.stroke();
  ctx.setLineDash([]);

  // ท้าย
  ctx.fillStyle = C.line;
  ctx.fillRect(120, H - 210, W - 240, 2);
  ctx.fillStyle = C.muted;
  ctx.font = `400 24px ${BODY}`;
  ctx.fillText(fitText(ctx, `โมเดล: ${modelLabel(r.modelVersion)}`, W - 240), 120, H - 160);
  ctx.fillText(`ตรวจเมื่อ ${dateTime(r.checkedAt ?? new Date().toISOString())}`, 120, H - 122);
  ctx.fillText('ผลนี้เป็นการประเมินด้วยสถิติ ไม่ใช่คำยืนยัน 100%', 120, H - 84);

  return new Promise((resolve, reject) =>
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('toBlob failed'))), 'image/png'),
  );
}
