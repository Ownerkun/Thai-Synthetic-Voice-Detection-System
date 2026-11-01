import { describe, expect, it } from 'vitest';
import { parseFlacDuration, parseWavDuration } from './audioInfo';
import { encodeWav } from './wav';

describe('parseWavDuration (A3)', () => {
  it('อ่านความยาวจาก WAV ที่แอปสร้างเอง', () => {
    const wav = encodeWav(new Float32Array(16000 * 12), 16000);
    expect(parseWavDuration(wav)).toBeCloseTo(12, 5);
  });

  it('ใช้ขนาดไฟล์แทนเมื่อ data size เป็น 0xFFFFFFFF (ไฟล์จากการอัดสด)', () => {
    const wav = encodeWav(new Float32Array(16000 * 3), 16000);
    new DataView(wav).setUint32(40, 0xffffffff, true);
    expect(parseWavDuration(wav)).toBeCloseTo(3, 5);
  });

  it('อ่านจากแค่ส่วนหัว แต่คำนวณด้วยขนาดไฟล์จริง', () => {
    const wav = encodeWav(new Float32Array(16000 * 30), 16000);
    expect(parseWavDuration(wav.slice(0, 1024), wav.byteLength)).toBeCloseTo(30, 5);
  });

  it('คืน null เมื่อไม่ใช่ WAV', () => {
    expect(parseWavDuration(new TextEncoder().encode('not a wav file at all').buffer)).toBeNull();
  });
});

describe('parseFlacDuration', () => {
  it('อ่าน STREAMINFO: 44.1 kHz, 441000 samples = 10 วินาที', () => {
    const b = new Uint8Array(42);
    b.set([0x66, 0x4c, 0x61, 0x43]); // fLaC
    b[4] = 0x80; // last-metadata-block + type 0 (STREAMINFO)
    const sampleRate = 44100;
    const total = 441000;
    b[18] = (sampleRate >> 12) & 0xff;
    b[19] = (sampleRate >> 4) & 0xff;
    b[20] = ((sampleRate & 0x0f) << 4) | 0x02; // + channels/bps bits
    b[21] = 0xf0; // bps bits + total samples high nibble = 0
    b[22] = (total >>> 24) & 0xff;
    b[23] = (total >>> 16) & 0xff;
    b[24] = (total >>> 8) & 0xff;
    b[25] = total & 0xff;
    expect(parseFlacDuration(b.buffer)).toBeCloseTo(10, 5);
  });

  it('คืน null เมื่อไม่ใช่ FLAC', () => {
    expect(parseFlacDuration(new Uint8Array(40).buffer)).toBeNull();
  });
});
