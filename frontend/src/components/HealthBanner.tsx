import { useEffect, useState } from 'react';
import { api, isDemo } from '../api/client';
import type { Health } from '../api/types';
import { Icon } from './Icon';

const DISMISS_KEY = 'tsvd.bannerDismissed';

function readDismissed(): boolean {
  try {
    return sessionStorage.getItem(DISMISS_KEY) === '1';
  } catch {
    return false;
  }
}

type State = { kind: 'loading' } | { kind: 'ok'; health: Health } | { kind: 'down' };

export function HealthBanner() {
  const [state, setState] = useState<State>({ kind: 'loading' });
  // ปิดแถบแจ้งข้อมูลได้ (จำไว้จนปิดแท็บ) ส่วนแถบเชื่อมต่อไม่ได้ปิดไม่ได้ เพราะใช้งานไม่ได้จริง
  const [dismissed, setDismissed] = useState(readDismissed);
  const dismiss = () => {
    try {
      sessionStorage.setItem(DISMISS_KEY, '1');
    } catch {
      /* จำไม่ได้ก็แค่ขึ้นใหม่รอบหน้า */
    }
    setDismissed(true);
  };
  const closeBtn = (
    <button type="button" className="banner-close" aria-label="ปิดแถบแจ้งเตือน" onClick={dismiss}>
      <Icon name="close" size={14} />
    </button>
  );

  useEffect(() => {
    api
      .health()
      .then((health) => setState({ kind: 'ok', health }))
      .catch(() => setState({ kind: 'down' }));
  }, []);

  if (isDemo) {
    if (dismissed) return null;
    return (
      <div className="banner banner-info">
        <span>🎭 โหมดสาธิต: ทำงานในเบราว์เซอร์ล้วน ไม่ได้เชื่อม backend จริง ผลตรวจเป็นค่าจำลอง ข้อมูลอยู่แค่ในเครื่องคุณ</span>
        {closeBtn}
      </div>
    );
  }
  if (state.kind === 'down') {
    return <div className="banner banner-danger">😴 เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ ตอนนี้ยังตรวจเสียงไม่ได้</div>;
  }
  if (state.kind === 'ok' && state.health.using_mock_model && !dismissed) {
    return (
      <div className="banner banner-warn" title={state.health.model_version}>
        <span>🧪 โหมดทดสอบ: ยังใช้โมเดลจำลอง ผลยังไม่ใช่ของจริง</span>
        {closeBtn}
      </div>
    );
  }
  return null;
}
