import type { SegmentResult } from '../api/types';

/**
 * ช่วง "ก้ำกึ่ง" (A4): คะแนนเฉลี่ยห่างจากเกณฑ์ไม่เกินค่านี้ (0.05 = 5 จุดเปอร์เซ็นต์)
 * ใช้แสดงผลเท่านั้น คำตัดสินยังเป็นของ backend ถ้าทีมตกลงช่วงใหม่ แก้ที่นี่ที่เดียว
 */
export const BORDERLINE_MARGIN = 0.05;

export const isBorderline = (mean: number, threshold: number) =>
  Math.abs(mean - threshold) <= BORDERLINE_MARGIN + 1e-9;

export const flaggedSegments = (segments: SegmentResult[]) => segments.filter((s) => s.is_spoof);

/** ชื่อโมเดลที่ผู้ใช้อ่านเข้าใจ (ชื่อจริงยังดูได้จาก tooltip) */
export function modelLabel(version: string): string {
  const v = version.toLowerCase();
  if (v.startsWith('demo')) return 'โมเดลจำลองในเบราว์เซอร์ (โหมดสาธิต)';
  if (v.includes('mock')) return 'โมเดลทดลอง (ยังไม่ใช่โมเดลจริง)';
  return version;
}
