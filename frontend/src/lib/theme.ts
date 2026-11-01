import { useCallback, useEffect, useState } from 'react';

// ธีมจริงถูกตั้งเป็น <html data-theme="light|dark"> (ดู script ใน index.html ที่ตั้งก่อน render เพื่อไม่ให้จอกระพริบ)
// ถ้าผู้ใช้ยังไม่เคยกดเลือก จะตามการตั้งค่าของเครื่องและเปลี่ยนตามทันทีเมื่อเครื่องเปลี่ยน

export type Theme = 'light' | 'dark';

const STORAGE_KEY = 'tsvd.theme';
const media = () => window.matchMedia('(prefers-color-scheme: dark)');

function readSaved(): Theme | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value === 'light' || value === 'dark' ? value : null;
  } catch {
    return null;
  }
}

function apply(theme: Theme) {
  document.documentElement.dataset.theme = theme;
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => readSaved() ?? (media().matches ? 'dark' : 'light'));

  useEffect(() => apply(theme), [theme]);

  // ยังไม่ได้เลือกเอง → ตามเครื่อง
  useEffect(() => {
    const mq = media();
    const onChange = () => {
      if (!readSaved()) setTheme(mq.matches ? 'dark' : 'light');
    };
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);

  const toggle = useCallback(() => {
    setTheme((current) => {
      const next: Theme = current === 'dark' ? 'light' : 'dark';
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch {
        /* จำไม่ได้ก็แค่ใช้ได้เฉพาะรอบนี้ */
      }
      return next;
    });
  }, []);

  return { theme, toggle };
}
