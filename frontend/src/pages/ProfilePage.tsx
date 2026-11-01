import { useEffect, useState, type FormEvent } from 'react';
import { api, ApiError } from '../api/client';
import type { UserProfile } from '../api/types';
import { Icon } from '../components/Icon';
import { SkeletonCard } from '../components/Skeleton';
import { dateTime } from '../lib/format';

type Message = { kind: 'ok' | 'error'; text: string } | null;

function Callout({ message }: { message: Message }) {
  if (!message) return null;
  return <div className={`callout ${message.kind === 'ok' ? 'callout-ok' : 'callout-danger'}`}>{message.text}</div>;
}

export function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getMe()
      .then(setProfile)
      .catch((e) => setLoadError(e instanceof ApiError ? e.message : 'โหลดข้อมูลบัญชีไม่สำเร็จ'));
  }, []);

  if (loadError) return <div className="callout callout-danger">{loadError}</div>;
  if (!profile) return <SkeletonCard lines={2} />;

  const initial = (profile.display_name || profile.email).trim().charAt(0).toUpperCase();

  return (
    <div className="stack">
      <section className="card profile-hero">
        <span className="avatar" aria-hidden>
          {initial}
        </span>
        <div className="profile-text">
          <h1>{profile.display_name || 'ยังไม่ได้ตั้งชื่อ'}</h1>
          <span className="muted">{profile.email}</span>
          <span className="muted small">เป็นสมาชิกตั้งแต่ {dateTime(profile.created_at)}</span>
        </div>
      </section>

      <NameCard profile={profile} onSaved={setProfile} />
      <PasswordCard />
    </div>
  );
}

function NameCard({ profile, onSaved }: { profile: UserProfile; onSaved: (p: UserProfile) => void }) {
  const [name, setName] = useState(profile.display_name ?? '');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<Message>(null);
  const unchanged = name.trim() === (profile.display_name ?? '');

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const updated = await api.updateMe({ display_name: name.trim() || null });
      onSaved(updated);
      setName(updated.display_name ?? '');
      setMessage({ kind: 'ok', text: updated.display_name ? 'บันทึกชื่อแล้ว ✨' : 'ล้างชื่อแล้ว' });
    } catch (err) {
      setMessage({ kind: 'error', text: err instanceof ApiError ? err.message : 'บันทึกไม่สำเร็จ' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="card stack-sm" onSubmit={submit}>
      <h3>
        <Icon name="user" size={18} /> ชื่อที่แสดง
      </h3>
      <p className="muted small" style={{ margin: 0 }}>
        ชื่อนี้ใช้แสดงในระบบ เว้นว่างไว้ถ้าไม่อยากตั้งชื่อ
      </p>
      <div className="row wrap">
        <input
          className="grow"
          maxLength={100}
          placeholder="เช่น มายด์"
          value={name}
          onChange={(e) => setName(e.target.value)}
          aria-label="ชื่อที่แสดง"
        />
        <button className="btn btn-primary" disabled={saving || unchanged}>
          {saving ? 'กำลังบันทึก…' : 'บันทึก'}
        </button>
      </div>
      <Callout message={message} />
    </form>
  );
}

function PasswordCard() {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<Message>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setMessage(null);
    if (next.length < 8) return setMessage({ kind: 'error', text: 'รหัสผ่านใหม่ต้องยาวอย่างน้อย 8 ตัวอักษร' });
    if (next !== confirm) return setMessage({ kind: 'error', text: 'ยืนยันรหัสผ่านใหม่ไม่ตรงกัน' });
    if (next === current) return setMessage({ kind: 'error', text: 'รหัสผ่านใหม่ต้องไม่ซ้ำกับรหัสเดิม' });

    setSaving(true);
    try {
      await api.changePassword({ current_password: current, new_password: next });
      setCurrent('');
      setNext('');
      setConfirm('');
      setMessage({ kind: 'ok', text: 'เปลี่ยนรหัสผ่านแล้ว 🔒 ครั้งหน้าให้เข้าสู่ระบบด้วยรหัสใหม่' });
    } catch (err) {
      // backend ตอบ 400 เมื่อรหัสเดิมผิด (ไม่ใช่ 401 เพื่อไม่ให้ถูก logout)
      const text =
        err instanceof ApiError && err.status === 400
          ? 'รหัสผ่านเดิมไม่ถูกต้อง'
          : err instanceof ApiError
            ? err.message
            : 'เปลี่ยนรหัสผ่านไม่สำเร็จ';
      setMessage({ kind: 'error', text });
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="card stack-sm" onSubmit={submit}>
      <h3>
        <Icon name="lock" size={18} /> เปลี่ยนรหัสผ่าน
      </h3>
      <label className="field">
        <span>รหัสผ่านปัจจุบัน</span>
        <input
          type="password"
          required
          autoComplete="current-password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
        />
      </label>
      <div className="two-col">
        <label className="field">
          <span>รหัสผ่านใหม่ (อย่างน้อย 8 ตัวอักษร)</span>
          <input
            type="password"
            required
            minLength={8}
            maxLength={128}
            autoComplete="new-password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
          />
        </label>
        <label className="field">
          <span>ยืนยันรหัสผ่านใหม่</span>
          <input
            type="password"
            required
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
        </label>
      </div>
      <div>
        <button className="btn btn-primary" disabled={saving}>
          {saving ? 'กำลังเปลี่ยน…' : 'เปลี่ยนรหัสผ่าน'}
        </button>
      </div>
      <Callout message={message} />
    </form>
  );
}
