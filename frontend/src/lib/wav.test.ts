import { describe, expect, it } from 'vitest';
import { encodeWav } from './wav';

const text = (v: DataView, o: number) => String.fromCharCode(v.getUint8(o), v.getUint8(o + 1), v.getUint8(o + 2), v.getUint8(o + 3));

describe('encodeWav (เสียงที่อัดจากไมค์ → WAV ที่ backend รับ)', () => {
  it('สร้าง header PCM 16-bit mono ถูกต้อง', () => {
    const v = new DataView(encodeWav(new Float32Array(100), 16000));
    expect(text(v, 0)).toBe('RIFF');
    expect(text(v, 8)).toBe('WAVE');
    expect(text(v, 12)).toBe('fmt ');
    expect(v.getUint16(20, true)).toBe(1); // PCM
    expect(v.getUint16(22, true)).toBe(1); // mono
    expect(v.getUint32(24, true)).toBe(16000);
    expect(v.getUint32(28, true)).toBe(32000); // byte rate
    expect(v.getUint16(34, true)).toBe(16);
    expect(text(v, 36)).toBe('data');
    expect(v.getUint32(40, true)).toBe(200);
    expect(v.byteLength).toBe(244);
  });

  it('ตัดสัญญาณที่เกิน ±1 ไม่ให้ล้น', () => {
    const v = new DataView(encodeWav(Float32Array.from([2, -2, 0]), 16000));
    expect(v.getInt16(44, true)).toBe(32767);
    expect(v.getInt16(46, true)).toBe(-32768);
    expect(v.getInt16(48, true)).toBe(0);
  });
});
