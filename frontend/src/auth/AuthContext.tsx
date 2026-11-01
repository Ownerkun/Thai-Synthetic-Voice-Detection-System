import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { configureApi } from '../api/client';

export type Role = 'user' | 'admin';

interface Session {
  token: string;
  role: Role;
  expiresAt: number; // ms
}

interface AuthState {
  session: Session | null;
  role: Role | null;
  signIn: (token: string) => void;
  signOut: () => void;
}

const STORAGE_KEY = 'tsvd.session';
const AuthContext = createContext<AuthState | null>(null);

// อ่าน payload ของ JWT (sub, role, exp) ฝั่ง client เพื่อรู้ role/วันหมดอายุเท่านั้น
// การตรวจลายเซ็นจริงเกิดที่ backend ทุก request
function parseToken(token: string): Session | null {
  try {
    const part = token.split('.')[1];
    const json = atob(part.replace(/-/g, '+').replace(/_/g, '/'));
    const payload = JSON.parse(json) as { role?: string; exp?: number };
    if (payload.role !== 'user' && payload.role !== 'admin') return null;
    const expiresAt = (payload.exp ?? 0) * 1000;
    if (expiresAt <= Date.now()) return null;
    return { token, role: payload.role, expiresAt };
  } catch {
    return null;
  }
}

function loadSession(): Session | null {
  try {
    const token = localStorage.getItem(STORAGE_KEY);
    return token ? parseToken(token) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(loadSession);

  const signOut = useCallback(() => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* storage ใช้ไม่ได้ ก็แค่ไม่จำ session */
    }
    setSession(null);
  }, []);

  const signIn = useCallback((token: string) => {
    const next = parseToken(token);
    if (!next) return;
    try {
      localStorage.setItem(STORAGE_KEY, token);
    } catch {
      /* ignore */
    }
    setSession(next);
  }, []);

  // ให้ API client ใช้ token ล่าสุดเสมอ
  configureApi({ getToken: () => session?.token ?? null, onUnauthorized: signOut });

  // logout อัตโนมัติเมื่อ token หมดอายุระหว่างเปิดหน้าเว็บค้างไว้
  useEffect(() => {
    if (!session) return;
    const ms = session.expiresAt - Date.now();
    const timer = window.setTimeout(signOut, Math.min(Math.max(ms, 0), 2 ** 31 - 1));
    return () => window.clearTimeout(timer);
  }, [session, signOut]);

  const value = useMemo(
    () => ({ session, role: session?.role ?? null, signIn, signOut }),
    [session, signIn, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
