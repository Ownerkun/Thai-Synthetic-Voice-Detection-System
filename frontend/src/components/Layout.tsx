import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { useTheme } from '../lib/theme';
import { HealthBanner } from './HealthBanner';
import { Icon, type IconName } from './Icon';

interface NavItem {
  to: string;
  label: string;
  icon: IconName;
  end?: boolean;
}

export function Layout() {
  const { role, signOut } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();

  const logout = () => {
    signOut();
    navigate('/');
  };

  const items: NavItem[] = [{ to: '/', label: 'ตรวจเสียง', icon: 'wave', end: true }];
  if (role === 'user') {
    items.push({ to: '/history', label: 'ประวัติ', icon: 'clock' }, { to: '/feedback', label: 'Feedback', icon: 'heart' }, { to: '/profile', label: 'โปรไฟล์', icon: 'user' });
  }
  if (role === 'admin') items.push({ to: '/admin', label: 'แดชบอร์ด', icon: 'shield' });
  items.push({ to: '/about', label: 'เกี่ยวกับ', icon: 'info' });

  return (
    <div className="app">
      <div className="bg-blobs" aria-hidden />

      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/" className="brand">
            <span className="brand-logo">
              <Icon name="wave" size={18} />
            </span>
            <span>
              เสียงจริงไหม<span className="brand-q">?</span>
            </span>
          </NavLink>

          <nav className="nav-pills" aria-label="เมนูหลัก">
            {items.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end}>
                <Icon name={item.icon} size={18} />
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="nav-actions">
            <button
              type="button"
              className="theme-toggle"
              onClick={toggle}
              aria-label={theme === 'dark' ? 'เปลี่ยนเป็นโหมดสว่าง' : 'เปลี่ยนเป็นโหมดมืด'}
              title={theme === 'dark' ? 'โหมดสว่าง' : 'โหมดมืด'}
            >
              <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={18} />
            </button>
            {role ? (
              <button className="btn btn-soft btn-small" onClick={logout}>
                <Icon name="logout" size={16} />
                <span className="hide-sm">ออกจากระบบ{role === 'admin' ? ' (ผู้ดูแล)' : ''}</span>
              </button>
            ) : (
              <>
                <NavLink to="/login" className="btn btn-ghost btn-small hide-sm">
                  เข้าสู่ระบบ
                </NavLink>
                <NavLink to="/register" className="btn btn-primary btn-small">
                  สมัครฟรี
                </NavLink>
              </>
            )}
          </div>
        </div>
      </header>

      <HealthBanner />

      <main className="container">
        <Outlet />
      </main>

      <footer className="footer">
        ระบบตรวจสอบเสียงสังเคราะห์ภาษาไทย · <NavLink to="/about">เกี่ยวกับ & ความเป็นส่วนตัว</NavLink> · <NavLink to="/admin/login">สำหรับผู้ดูแล</NavLink>
      </footer>

      {/* แถบเมนูล่างแบบแอปมือถือ (แสดงเฉพาะจอเล็ก) */}
      <nav className="tabbar" aria-label="เมนูหลัก">
        {items.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end}>
            <Icon name={item.icon} size={22} />
            <span>{item.label}</span>
          </NavLink>
        ))}
        {!role && (
          <NavLink to="/login">
            <Icon name="user" size={22} />
            <span>เข้าสู่ระบบ</span>
          </NavLink>
        )}
      </nav>
    </div>
  );
}
