import { useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { Icon } from '../components/Icon';

function useAfterLogin(fallback: string) {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from;
  return () => navigate(from ?? fallback, { replace: true });
}

function errorMessage(e: unknown, byStatus: Record<number, string>): string {
  if (e instanceof ApiError) return byStatus[e.status] ?? e.message;
  return 'เกิดข้อผิดพลาด ลองใหม่อีกครั้ง';
}

export function LoginPage() {
  const { signIn } = useAuth();
  const done = useAfterLogin('/');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { access_token } = await api.login({ email, password });
      signIn(access_token);
      done();
    } catch (err) {
      setError(
        errorMessage(err, {
          401: 'อีเมลหรือรหัสผ่านไม่ถูกต้อง',
          403: 'บัญชีนี้ถูกระงับการใช้งาน กรุณาติดต่อผู้ดูแล',
          422: 'กรุณากรอกอีเมลให้ถูกต้อง',
        }),
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="card auth-card stack" onSubmit={submit}>
      <div className="auth-head">
        <span className="auth-icon">
          <Icon name="user" size={28} />
        </span>
        <h1>ยินดีต้อนรับกลับ 👋</h1>
        <p className="muted">เข้าสู่ระบบเพื่อดูประวัติและผลที่เคยเช็ก</p>
      </div>
      <label className="field">
        <span>อีเมล</span>
        <input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label className="field">
        <span>รหัสผ่าน</span>
        <input
          type="password"
          required
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>
      {error && <div className="callout callout-danger">{error}</div>}
      <button className="btn btn-primary btn-big" disabled={loading}>
        {loading ? 'กำลังเข้าสู่ระบบ…' : 'เข้าสู่ระบบ'}
      </button>
      <p className="muted small" style={{ textAlign: 'center', margin: 0 }}>
        ยังไม่มีบัญชี? <Link to="/register">สมัครสมาชิก</Link>
      </p>
    </form>
  );
}

export function RegisterPage() {
  const { signIn } = useAuth();
  const done = useAfterLogin('/');
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { access_token } = await api.register({
        email,
        password,
        display_name: displayName.trim() || null,
      });
      signIn(access_token);
      done();
    } catch (err) {
      setError(
        errorMessage(err, {
          409: 'อีเมลนี้ถูกใช้สมัครไปแล้ว',
          422: 'ข้อมูลไม่ถูกต้อง: รหัสผ่านต้องยาว 8–128 ตัวอักษร และอีเมลต้องถูกรูปแบบ',
        }),
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="card auth-card stack" onSubmit={submit}>
      <div className="auth-head">
        <span className="auth-icon">
          <Icon name="sparkle" size={28} />
        </span>
        <h1>สร้างบัญชีฟรี ✨</h1>
        <p className="muted">เก็บผลการตรวจไว้ดูย้อนหลัง และช่วยเราให้แม่นขึ้น</p>
      </div>
      <label className="field">
        <span>อีเมล</span>
        <input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label className="field">
        <span>ชื่อที่แสดง (ไม่บังคับ)</span>
        <input maxLength={100} value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
      </label>
      <label className="field">
        <span>รหัสผ่าน (อย่างน้อย 8 ตัวอักษร)</span>
        <input
          type="password"
          required
          minLength={8}
          maxLength={128}
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>
      {error && <div className="callout callout-danger">{error}</div>}
      <button className="btn btn-primary btn-big" disabled={loading}>
        {loading ? 'กำลังสมัคร…' : 'สมัครสมาชิก'}
      </button>
      <p className="muted small" style={{ textAlign: 'center', margin: 0 }}>
        มีบัญชีแล้ว? <Link to="/login">เข้าสู่ระบบ</Link>
      </p>
    </form>
  );
}

export function AdminLoginPage() {
  const { signIn } = useAuth();
  const done = useAfterLogin('/admin');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { access_token } = await api.adminLogin({ username, password });
      signIn(access_token);
      done();
    } catch (err) {
      setError(errorMessage(err, { 401: 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง' }));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="card auth-card stack" onSubmit={submit}>
      <div className="auth-head">
        <span className="auth-icon is-admin">
          <Icon name="shield" size={28} />
        </span>
        <h1>สำหรับผู้ดูแลระบบ</h1>
        <p className="muted">เข้าสู่ระบบด้วยบัญชีผู้ดูแล</p>
      </div>
      <label className="field">
        <span>ชื่อผู้ใช้</span>
        <input required autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
      </label>
      <label className="field">
        <span>รหัสผ่าน</span>
        <input
          type="password"
          required
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>
      {error && <div className="callout callout-danger">{error}</div>}
      <button className="btn btn-primary btn-big" disabled={loading}>
        {loading ? 'กำลังเข้าสู่ระบบ…' : 'เข้าสู่ระบบ'}
      </button>
    </form>
  );
}
