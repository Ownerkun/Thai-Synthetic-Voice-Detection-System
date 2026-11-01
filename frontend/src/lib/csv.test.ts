import { describe, expect, it } from 'vitest';
import { toCsv } from './csv';

describe('toCsv (A9)', () => {
  it('ขึ้นต้นด้วย BOM และคั่นบรรทัดแบบ CRLF', () => {
    const csv = toCsv(['a', 'b'], [[1, 'x']]);
    expect(csv.startsWith('﻿')).toBe(true);
    expect(csv.slice(1)).toBe('a,b\r\n1,x');
  });

  it('ครอบด้วยเครื่องหมายคำพูดเมื่อมีจุลภาค คำพูด หรือขึ้นบรรทัดใหม่', () => {
    const csv = toCsv(['f'], [['a,b'], ['say "hi"'], ['line1\nline2']]);
    expect(csv.slice(1).split('\r\n').slice(1)).toEqual(['"a,b"', '"say ""hi"""', '"line1\nline2"']);
  });

  it('กันสูตร Excel จากชื่อไฟล์ที่ผู้ใช้ตั้ง (CSV injection)', () => {
    const csv = toCsv(['f'], [['=HYPERLINK("x")'], ['+1'], ['-2'], ['@sum']]);
    const cells = csv.slice(1).split('\r\n').slice(1);
    expect(cells[0]).toBe(`"'=HYPERLINK(""x"")"`);
    expect(cells.slice(1)).toEqual(["'+1", "'-2", "'@sum"]);
  });

  it('ตัวเลขติดลบไม่ถูกแก้ และค่าว่างเป็นช่องว่าง', () => {
    expect(toCsv(['n', 'e'], [[-3, null]]).slice(1)).toBe('n,e\r\n-3,');
  });
});
