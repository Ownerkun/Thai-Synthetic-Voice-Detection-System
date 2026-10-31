import { afterEach, describe, expect, it, vi } from 'vitest';
import { inPeriod, thaiDate } from '../components/Filters';
import { failureText, fileSize, pct } from './format';

describe('failureText', () => {
  it('แปลเหตุผลจาก backend เป็นภาษาไทย', () => {
    expect(failureText('unsupported_format')).toContain('.wav');
    expect(failureText('decode_failed')).toContain('เสียหาย');
    expect(failureText('too_many_files')).toContain('10 ไฟล์');
  });

  it('เหตุผลใหม่ที่ไม่รู้จัก ใช้ข้อความกลาง', () => {
    expect(failureText('something_new')).toBe('ไฟล์นี้ตรวจสอบไม่ได้');
  });
});

describe('pct / fileSize', () => {
  it('จัดรูปแบบตัวเลข', () => {
    expect(pct(0.4567)).toBe('45.7%');
    expect(pct(0.5, 0)).toBe('50%');
    expect(fileSize(300)).toBe('1 KB');
    expect(fileSize(2.5 * 1024 * 1024)).toBe('2.5 MB');
  });
});

describe('ตัวกรองช่วงเวลา (ตามเวลาไทย)', () => {
  afterEach(() => vi.useRealTimers());

  it('thaiDate ใช้วันที่ไทย แม้เวลา UTC ยังเป็นเมื่อวาน', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-10-30T20:00:00Z')); // = 31 ต.ค. 03:00 เวลาไทย
    expect(thaiDate()).toBe('2026-10-31');
    expect(thaiDate(-6)).toBe('2026-10-25');
  });

  it('inPeriod นับย้อนจากตอนนี้ และรับเวลาที่ไม่มี timezone เป็น UTC', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-10-31T12:00:00Z'));
    expect(inPeriod('2026-10-26T12:00:00', '7')).toBe(true);
    expect(inPeriod('2026-10-20T12:00:00Z', '7')).toBe(false);
    expect(inPeriod('2020-01-01T00:00:00Z', '')).toBe(true);
  });
});
