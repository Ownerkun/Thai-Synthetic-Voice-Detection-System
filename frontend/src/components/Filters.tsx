import { useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Icon } from './Icon';

/**
 * useSearchParams ที่เปลี่ยนหลายค่าติดกันได้โดยไม่ทับกัน
 * (setSearchParams ของ react-router ไม่ต่อคิวเหมือน setState จึงเก็บค่าล่าสุดไว้ใน ref เอง)
 */
export function useLatestSearchParams() {
  const [params, setParams] = useSearchParams();
  const latest = useRef(params);
  latest.current = params;
  const update = useCallback(
    (change: (draft: URLSearchParams) => void, replace = false) => {
      const next = new URLSearchParams(latest.current);
      change(next);
      latest.current = next;
      setParams(next, { replace });
    },
    [setParams],
  );
  return [params, update] as const;
}

export interface ChipOption {
  value: string;
  label: string;
}

/** ปุ่มเลือกได้ทีละค่า ('' = ทั้งหมด) */
export function ChipGroup({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: ChipOption[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="chip-group" role="radiogroup" aria-label={label}>
      <span className="chip-group-label">{label}</span>
      {[{ value: '', label: 'ทั้งหมด' }, ...options].map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          className={`fchip ${value === o.value ? 'is-on' : ''}`}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function SearchBox({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}) {
  return (
    <label className="searchbox">
      <Icon name="search" size={16} />
      <input type="search" value={value} placeholder={placeholder} aria-label={placeholder} onChange={(e) => onChange(e.target.value)} />
      {value && (
        <button type="button" className="btn-icon" aria-label="ล้างคำค้นหา" onClick={() => onChange('')}>
          <Icon name="close" size={14} />
        </button>
      )}
    </label>
  );
}

/** "แสดง 3 จาก 12 รายการ · ล้างตัวกรอง" */
export function FilterSummary({
  shown,
  total,
  active,
  onReset,
  note,
}: {
  shown: number;
  total: number;
  active: boolean;
  onReset: () => void;
  note?: string;
}) {
  return (
    <div className="filter-summary">
      <span className="muted small">
        {active ? `แสดง ${shown} จาก ${total} รายการ` : `ทั้งหมด ${total} รายการ`}
        {note ? ` · ${note}` : ''}
      </span>
      {active && (
        <button type="button" className="btn btn-ghost btn-small" onClick={onReset}>
          ล้างตัวกรอง
        </button>
      )}
    </div>
  );
}

/** ตัวกรองฝั่งหน้าเว็บเก็บใน URL (?verdict=spoof) กดย้อนกลับ/รีเฟรช/แชร์ลิงก์แล้วได้ผลเดิม */
export function useUrlFilters<K extends string>(keys: readonly K[]) {
  const [params, update] = useLatestSearchParams();
  const values = Object.fromEntries(keys.map((k) => [k, params.get(k) ?? ''])) as Record<K, string>;
  const set = (key: K, value: string) =>
    update((next) => {
      if (value) next.set(key, value);
      else next.delete(key);
    }, true);
  const reset = () => update((next) => keys.forEach((k) => next.delete(k)), true);
  const active = keys.some((k) => k !== 'sort' && values[k] !== '');
  return { values, set, reset, active };
}

/** วันที่แบบ YYYY-MM-DD ตามเวลาไทย (ตรงกับที่ backend ใช้กรอง date_from/date_to) */
export function thaiDate(offsetDays = 0): string {
  return new Date(Date.now() + 7 * 3600_000 + offsetDays * 86_400_000).toISOString().slice(0, 10);
}

/** ผ่านช่วงเวลาไหม: period = '' | '7' | '30' (วันล่าสุด) */
export function inPeriod(iso: string, period: string): boolean {
  if (!period) return true;
  const withZone = /[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`;
  return Date.now() - new Date(withZone).getTime() <= Number(period) * 86_400_000;
}
