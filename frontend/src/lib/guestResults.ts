import type { DetectionResult } from '../api/types';

// ผลของผู้ที่ไม่ได้ login ไม่ถูกเก็บในประวัติฝั่ง server จึงเก็บไว้ใน Local Storage ของเบราว์เซอร์แทน
// (ตาม Activity / Component Diagram ใน docs/UML) เก็บเฉพาะคะแนน ไม่เก็บไฟล์เสียง

export interface LocalResult extends DetectionResult {
  saved_at: string;
}

const KEY = 'tsvd.guestResults';
const MAX_ITEMS = 20;

export function loadGuestResults(): LocalResult[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(KEY) ?? '[]');
    // ข้อมูลในเครื่องอาจเก่าหรือเสียรูป เก็บเฉพาะรายการที่เปิดดูได้จริง
    return Array.isArray(parsed) ? (parsed as LocalResult[]).filter(isUsable) : [];
  } catch {
    return [];
  }
}

function isUsable(r: LocalResult): boolean {
  return (
    !!r &&
    typeof r.original_filename === 'string' &&
    typeof r.mean_probability === 'number' &&
    (r.verdict === 'spoof' || r.verdict === 'real') &&
    Array.isArray(r.segments)
  );
}

export function addGuestResults(results: DetectionResult[]): LocalResult[] {
  const savedAt = new Date().toISOString();
  const next = [...results.map((r) => ({ ...r, saved_at: savedAt })), ...loadGuestResults()].slice(0, MAX_ITEMS);
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* storage เต็มหรือถูกปิด ก็แค่ไม่จำ */
  }
  return next;
}

export function clearGuestResults() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
