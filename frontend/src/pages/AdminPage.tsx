import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { api, ApiError } from '../api/client';
import type { AdminUser, AdminUserList, StatsOverview, Threshold } from '../api/types';
import { Link } from 'react-router-dom';
import { Icon, type IconName } from '../components/Icon';
import { useUi } from '../components/UiProvider';
import { AdminTabs } from './AdminDetectionsPages';
import { dateTime, pct } from '../lib/format';

const errText = (e: unknown, fallback: string) => (e instanceof ApiError ? e.message : fallback);

export function AdminPage() {
  const [stats, setStats] = useState<StatsOverview | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);

  const loadStats = useCallback(() => {
    api
      .getStats()
      .then(setStats)
      .catch((e) => setStatsError(errText(e, 'โหลดสถิติไม่สำเร็จ')));
  }, []);

  useEffect(loadStats, [loadStats]);

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>แดชบอร์ดผู้ดูแล</h1>
          <p className="muted">ภาพรวมระบบ ปรับเกณฑ์ และจัดการผู้ใช้</p>
        </div>
      </div>
      <AdminTabs />

      {statsError && <div className="callout callout-danger">{statsError}</div>}
      <section className="kpi-grid">
        <Kpi tone="lavender" icon="wave" label="ตรวจทั้งหมด" value={stats?.total_detections} />
        <Kpi tone="pink" icon="sparkle" label="ผล: เสียง AI" value={stats?.total_spoof_verdicts} />
        <Kpi tone="mint" icon="check" label="ผล: เสียงจริง" value={stats?.total_real_verdicts} />
        <Kpi tone="sky" icon="user" label="ผู้ใช้" value={stats?.total_users} />
        <Kpi
          tone="peach"
          icon="heart"
          label="ผู้ใช้เห็นด้วยกับผล"
          value={stats ? (stats.feedback_agreement_rate === null ? '—' : pct(stats.feedback_agreement_rate)) : undefined}
        />
      </section>

      <ThresholdCard />
      <UsersCard onChanged={loadStats} />
    </div>
  );
}

function Kpi({
  label,
  value,
  tone,
  icon,
}: {
  label: string;
  value: number | string | undefined;
  tone: string;
  icon: IconName;
}) {
  return (
    <div className={`card kpi tone-${tone}`}>
      <span className="kpi-icon">
        <Icon name={icon} size={20} />
      </span>
      <div className="kpi-value">{value ?? '…'}</div>
      <div className="muted small">{label}</div>
    </div>
  );
}

// ประเมินว่าถ้าใช้เกณฑ์ใหม่ ผลตรวจล่าสุดกี่รายการจะได้คำตัดสินต่างจากเดิม (ดึงสูงสุด 1,000 รายการจาก /admin/detections)
async function estimateImpact(newValue: number) {
  let offset = 0;
  let checked = 0;
  let toReal = 0;
  let toSpoof = 0;
  for (let i = 0; i < 5; i++) {
    const page = await api.listDetections({ limit: 200, offset, sort: 'created_at', order: 'desc' });
    for (const d of page.items) {
      const next = d.mean_probability >= newValue ? 'spoof' : 'real';
      if (d.verdict === 'spoof' && next === 'real') toReal++;
      if (d.verdict === 'real' && next === 'spoof') toSpoof++;
    }
    checked += page.items.length;
    offset += page.items.length;
    if (offset >= page.total || page.items.length === 0) break;
  }
  return { checked, toReal, toSpoof };
}

function ThresholdCard() {
  const { confirm, toast } = useUi();
  const [current, setCurrent] = useState<Threshold | null | undefined>(undefined);
  const [value, setValue] = useState('0.5');
  const [note, setNote] = useState('');
  const [message, setMessage] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .getThreshold()
      .then((t) => {
        setCurrent(t);
        if (t) setValue(String(t.value));
      })
      .catch((e) => setMessage({ kind: 'error', text: errText(e, 'โหลด threshold ไม่สำเร็จ') }));
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const num = Number(value);
    if (!Number.isFinite(num) || num < 0 || num > 1) {
      setMessage({ kind: 'error', text: 'threshold ต้องอยู่ระหว่าง 0 ถึง 1' });
      return;
    }
    const before = current?.value ?? 0.5;
    setSaving(true);
    setMessage(null);

    let impact: ReactNode = null;
    try {
      const r = await estimateImpact(num);
      impact =
        r.checked === 0 ? (
          'ยังไม่มีผลตรวจในระบบ'
        ) : r.toReal + r.toSpoof === 0 ? (
          `จากผลตรวจล่าสุด ${r.checked} รายการ คำตัดสินจะไม่เปลี่ยนเลย`
        ) : (
          <>
            จากผลตรวจล่าสุด {r.checked} รายการ ถ้าตรวจด้วยเกณฑ์ใหม่ <b>{r.toReal}</b> รายการจะเปลี่ยนจาก AI เป็นเสียงจริง และ{' '}
            <b>{r.toSpoof}</b> รายการจะเปลี่ยนจากเสียงจริงเป็น AI
          </>
        );
    } catch {
      impact = 'ประเมินผลกระทบไม่ได้ในตอนนี้';
    }

    const ok = await confirm({
      title: `เปลี่ยนเกณฑ์จาก ${pct(before, 0)} เป็น ${pct(num, 0)}?`,
      message: (
        <>
          <p>{impact}</p>
          <p>ผลเก่าที่บันทึกไว้แล้วจะไม่ถูกแก้ แต่การตรวจครั้งถัดไปของทุกคนจะใช้เกณฑ์ใหม่ทันที</p>
        </>
      ),
      confirmLabel: `ใช้เกณฑ์ ${pct(num, 0)}`,
    });
    if (!ok) {
      setSaving(false);
      return;
    }

    try {
      const res = await api.setThreshold(num, note.trim());
      setCurrent(res.current);
      setNote('');
      const prev = res.previous_value === null ? 'ค่าเริ่มต้น' : res.previous_value;
      setMessage({ kind: 'ok', text: `อัปเดตแล้ว: ${prev} → ${res.current.value} (มีผลกับการตรวจครั้งถัดไปทันที)` });
      toast('เปลี่ยนเกณฑ์แล้ว');
    } catch (err) {
      setMessage({ kind: 'error', text: errText(err, 'บันทึกไม่สำเร็จ') });
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="card stack">
      <h3>เกณฑ์ตัดสิน (threshold)</h3>
      <p className="muted small">
        ถ้าคะแนนเฉลี่ย ≥ threshold ระบบจะตัดสินว่าเป็นเสียงสังเคราะห์ ·{' '}
        {current === undefined
          ? 'กำลังโหลด…'
          : current
            ? `ปัจจุบัน ${current.value} (ตั้งเมื่อ ${dateTime(current.effective_from)}${current.note ? `, ${current.note}` : ''})`
            : 'ยังไม่เคยตั้ง ใช้ค่าเริ่มต้นของระบบ (0.5)'}
      </p>
      <form className="row wrap" onSubmit={submit}>
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          aria-label="threshold"
          className="grow"
        />
        <input
          type="number"
          min={0}
          max={1}
          step={0.01}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="input-narrow"
        />
        <input placeholder="หมายเหตุ (ไม่บังคับ)" value={note} onChange={(e) => setNote(e.target.value)} />
        <button className="btn btn-primary" disabled={saving}>
          {saving ? 'กำลังประเมิน…' : 'บันทึก'}
        </button>
      </form>
      {message && (
        <div className={`callout ${message.kind === 'ok' ? 'callout-ok' : 'callout-danger'}`}>{message.text}</div>
      )}
    </section>
  );
}

const PAGE_SIZE = 20;

function UsersCard({ onChanged }: { onChanged: () => void }) {
  const { confirm, toast } = useUi();
  const [q, setQ] = useState('');
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<'all' | 'active' | 'suspended'>('all');
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<AdminUserList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<{ id: string; name: string } | null>(null);

  // หน่วงการค้นหาเล็กน้อย ไม่ยิง API ทุกตัวอักษร
  useEffect(() => {
    const t = window.setTimeout(() => {
      setQuery(q.trim());
      setOffset(0);
    }, 300);
    return () => window.clearTimeout(t);
  }, [q]);

  const load = useCallback(() => {
    api
      .listUsers({
        q: query || undefined,
        is_active: status === 'all' ? null : status === 'active',
        limit: PAGE_SIZE,
        offset,
      })
      .then((res) => {
        setData(res);
        setError(null);
      })
      .catch((e) => setError(errText(e, 'โหลดรายชื่อผู้ใช้ไม่สำเร็จ')));
  }, [query, status, offset]);

  useEffect(load, [load]);

  const replaceUser = (user: AdminUser) =>
    setData((d) => (d ? { ...d, items: d.items.map((u) => (u.id === user.id ? user : u)) } : d));

  const toggleActive = async (user: AdminUser) => {
    const action = user.is_active ? 'ระงับ' : 'เปิดใช้งาน';
    const ok = await confirm({
      title: `${action}บัญชีนี้?`,
      message: user.is_active
        ? `${user.email} จะเข้าสู่ระบบไม่ได้ และถ้ากำลังใช้งานอยู่จะถูกออกจากระบบในการกดครั้งถัดไป เปิดใช้งานคืนได้ภายหลัง`
        : `${user.email} จะกลับมาเข้าสู่ระบบได้ตามปกติ`,
      confirmLabel: `${action}บัญชี`,
      danger: user.is_active,
    });
    if (!ok) return;
    try {
      replaceUser(await api.updateUser(user.id, { is_active: !user.is_active }));
      onChanged();
      toast(`${action}บัญชี ${user.email} แล้ว`);
    } catch (e) {
      toast(errText(e, `${action}ไม่สำเร็จ`), 'error');
    }
  };

  const saveName = async () => {
    if (!editing) return;
    try {
      replaceUser(await api.updateUser(editing.id, { display_name: editing.name.trim() || null }));
      setEditing(null);
      toast('บันทึกชื่อแล้ว');
    } catch (e) {
      toast(errText(e, 'แก้ชื่อไม่สำเร็จ'), 'error');
    }
  };

  const total = data?.total ?? 0;
  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section className="card stack">
      <div className="row between wrap">
        <h3>ผู้ใช้ {data ? `(${total})` : ''}</h3>
        <div className="row wrap">
          <input placeholder="ค้นหาอีเมลหรือชื่อ" value={q} maxLength={100} onChange={(e) => setQ(e.target.value)} />
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as typeof status);
              setOffset(0);
            }}
          >
            <option value="all">ทุกสถานะ</option>
            <option value="active">ใช้งานปกติ</option>
            <option value="suspended">ถูกระงับ</option>
          </select>
          {(q || status !== 'all') && (
            <button
              type="button"
              className="btn btn-ghost btn-small"
              onClick={() => {
                setQ('');
                setStatus('all');
                setOffset(0);
              }}
            >
              ล้างตัวกรอง
            </button>
          )}
        </div>
      </div>

      {error && <div className="callout callout-danger">{error}</div>}

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>อีเมล</th>
              <th>ชื่อที่แสดง</th>
              <th>สมัครเมื่อ</th>
              <th>เข้าระบบล่าสุด</th>
              <th className="num">ตรวจ</th>
              <th>สถานะ</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data?.items.map((u) => (
              <tr key={u.id}>
                <td>{u.email}</td>
                <td>
                  {editing?.id === u.id ? (
                    <span className="row">
                      <input
                        autoFocus
                        maxLength={100}
                        value={editing.name}
                        onChange={(e) => setEditing({ id: u.id, name: e.target.value })}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') void saveName();
                          if (e.key === 'Escape') setEditing(null);
                        }}
                      />
                      <button className="btn btn-small btn-primary" onClick={saveName}>
                        บันทึก
                      </button>
                    </span>
                  ) : (
                    <button className="link-btn" onClick={() => setEditing({ id: u.id, name: u.display_name ?? '' })}>
                      {u.display_name ?? <span className="muted">— ตั้งชื่อ</span>}
                    </button>
                  )}
                </td>
                <td className="nowrap">{dateTime(u.created_at)}</td>
                <td className="nowrap">{dateTime(u.last_login_at)}</td>
                <td className="num">
                  <Link
                    to={`/admin/detections?user_id=${u.id}&user_label=${encodeURIComponent(u.email)}`}
                    title="ดูผลตรวจของผู้ใช้นี้"
                  >
                    {u.detection_count}
                  </Link>
                </td>
                <td>
                  <span className={`badge ${u.is_active ? 'badge-real' : 'badge-muted'}`}>
                    {u.is_active ? 'ใช้งานปกติ' : 'ถูกระงับ'}
                  </span>
                </td>
                <td>
                  <button
                    className={`btn btn-small ${u.is_active ? 'btn-danger-soft' : 'btn-soft'}`}
                    onClick={() => toggleActive(u)}
                  >
                    {u.is_active ? 'ระงับ' : 'เปิดใช้งาน'}
                  </button>
                </td>
              </tr>
            ))}
            {data && data.items.length === 0 && (
              <tr>
                <td colSpan={7} className="muted empty">
                  ไม่พบผู้ใช้
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="row between">
        <span className="muted small">
          หน้า {page} / {pages}
        </span>
        <div className="row">
          <button className="btn btn-soft btn-small" disabled={offset === 0} onClick={() => setOffset(offset - PAGE_SIZE)}>
            ก่อนหน้า
          </button>
          <button
            className="btn btn-soft btn-small"
            disabled={offset + PAGE_SIZE >= total}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            ถัดไป
          </button>
        </div>
      </div>
    </section>
  );
}
