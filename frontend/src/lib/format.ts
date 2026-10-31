import type { FailureReason, Verdict } from '../api/types';

export const pct = (value: number, digits = 1) => `${(value * 100).toFixed(digits)}%`;

export const seconds = (value: number) => `${value.toFixed(1)} วิ`;

// backend เก็บเวลาเป็น UTC; บางฐานข้อมูล (sqlite ตอน dev) ส่งมาโดยไม่มี timezone ต่อท้าย จึงถือว่าเป็น UTC
const parseUtc = (iso: string) => new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);

export const dateTime = (iso: string | null | undefined) =>
  iso ? parseUtc(iso).toLocaleString('th-TH', { dateStyle: 'medium', timeStyle: 'short' }) : '-';

export const verdictLabel = (verdict: Verdict) => (verdict === 'spoof' ? 'เสียง AI' : 'เสียงจริง');

export const verdictEmoji = (verdict: Verdict) => (verdict === 'spoof' ? '🤖' : '🙋');

// ข้อความตามตาราง reason ใน docs/API_MOCKUP.md — อ่านจาก reason ไม่ใช่ message
const REASON_TEXT: Record<string, string> = {
  unsupported_format: 'ไฟล์ชนิดนี้ไม่รองรับ (รองรับเฉพาะ .wav และ .flac)',
  file_too_large: 'ไฟล์ใหญ่เกินไป (ไม่เกิน 20 MB)',
  empty_audio: 'ไฟล์นี้ไม่มีเสียง',
  decode_failed: 'เปิดไฟล์ไม่ได้ ไฟล์อาจเสียหาย ลองอัดหรือบันทึกใหม่',
  // ฝั่ง frontend เช็กเอง (src/lib/audioRules.ts)
  too_many_files: 'ตรวจได้ครั้งละไม่เกิน 10 ไฟล์ ไฟล์นี้จะไม่ถูกส่ง',
};

export const failureText = (reason: FailureReason) => REASON_TEXT[reason] ?? 'ไฟล์นี้ตรวจสอบไม่ได้';

export const fileSize = (bytes: number) =>
  bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
