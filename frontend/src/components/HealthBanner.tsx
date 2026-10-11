import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Health } from '../api/types';

type State = { kind: 'loading' } | { kind: 'ok'; health: Health } | { kind: 'down' };

export function HealthBanner() {
  const [state, setState] = useState<State>({ kind: 'loading' });

  useEffect(() => {
    api
      .health()
      .then((health) => setState({ kind: 'ok', health }))
      .catch(() => setState({ kind: 'down' }));
  }, []);

  if (state.kind === 'down') {
    return <div className="banner banner-danger">😴 เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ ตอนนี้ยังตรวจเสียงไม่ได้</div>;
  }
  if (state.kind === 'ok' && state.health.using_mock_model) {
    return (
      <div className="banner banner-warn" title={state.health.model_version}>
        🧪 โหมดทดสอบ: ยังใช้โมเดลจำลอง ผลยังไม่ใช่ของจริง
      </div>
    );
  }
  return null;
}
