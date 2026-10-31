import { describe, expect, it } from 'vitest';
import type { SegmentResult } from '../api/types';
import { BORDERLINE_MARGIN, flaggedSegments, isBorderline, modelLabel } from './result';

describe('isBorderline (ป้ายก้ำกึ่ง A4)', () => {
  it('ก้ำกึ่งเมื่อห่างจากเกณฑ์ไม่เกินช่วงที่กำหนด ทั้งสองฝั่ง', () => {
    expect(isBorderline(0.5, 0.5)).toBe(true);
    expect(isBorderline(0.5 + BORDERLINE_MARGIN, 0.5)).toBe(true);
    expect(isBorderline(0.5 - BORDERLINE_MARGIN, 0.5)).toBe(true);
  });

  it('ไม่ก้ำกึ่งเมื่อห่างเกินช่วง', () => {
    expect(isBorderline(0.56, 0.5)).toBe(false);
    expect(isBorderline(0.05, 0.5)).toBe(false);
  });
});

describe('flaggedSegments', () => {
  it('คืนเฉพาะช่วงที่เกินเกณฑ์', () => {
    const seg = (index: number, is_spoof: boolean): SegmentResult => ({
      index,
      start_seconds: index * 4,
      end_seconds: index * 4 + 4,
      spoof_probability: is_spoof ? 0.6 : 0.3,
      is_spoof,
    });
    expect(flaggedSegments([seg(0, true), seg(1, false), seg(2, true)]).map((s) => s.index)).toEqual([0, 2]);
  });
});

describe('modelLabel', () => {
  it('แปลชื่อโมเดลจำลองเป็นภาษาไทย', () => {
    expect(modelLabel('mock-v0 (real model not yet available)')).toBe('โมเดลทดลอง (ยังไม่ใช่โมเดลจริง)');
    expect(modelLabel('demo (จำลองในเบราว์เซอร์)')).toContain('โหมดสาธิต');
  });

  it('โมเดลจริงแสดงชื่อเวอร์ชันตามเดิม', () => {
    expect(modelLabel('aasist-v1.2')).toBe('aasist-v1.2');
  });
});
