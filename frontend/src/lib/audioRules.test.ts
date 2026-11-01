import { describe, expect, it } from 'vitest';
import { checkFile, MAX_FILE_BYTES } from './audioRules';

const file = (name: string, size: number) => new File([new Uint8Array(size)], name);

describe('checkFile (เช็กไฟล์ก่อนส่ง F2)', () => {
  it('รับ .wav และ .flac ไม่สนตัวพิมพ์', () => {
    expect(checkFile(file('a.wav', 10))).toBeNull();
    expect(checkFile(file('B.FLAC', 10))).toBeNull();
  });

  it('ปฏิเสธนามสกุลอื่นและไฟล์ที่ไม่มีนามสกุล', () => {
    expect(checkFile(file('song.mp3', 10))).toBe('unsupported_format');
    expect(checkFile(file('noext', 10))).toBe('unsupported_format');
    expect(checkFile(file('fake.wav.mp3', 10))).toBe('unsupported_format');
  });

  it('ตรวจนามสกุลก่อนขนาด เหมือน backend', () => {
    expect(checkFile(file('empty.mp3', 0))).toBe('unsupported_format');
  });

  it('ปฏิเสธไฟล์ว่าง', () => {
    expect(checkFile(file('empty.wav', 0))).toBe('empty_audio');
  });

  it('รับพอดี 20 MB แต่ไม่รับเกิน', () => {
    expect(checkFile(file('max.wav', MAX_FILE_BYTES))).toBeNull();
    expect(checkFile(file('big.wav', MAX_FILE_BYTES + 1))).toBe('file_too_large');
  });
});
