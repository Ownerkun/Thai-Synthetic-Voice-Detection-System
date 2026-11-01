import { Link, Route, Routes } from 'react-router-dom';
import { RequireRole } from './auth/RequireRole';
import { Layout } from './components/Layout';
import { AboutPage } from './pages/AboutPage';
import { AdminDetectionDetailPage, AdminDetectionsPage } from './pages/AdminDetectionsPages';
import { AdminPage } from './pages/AdminPage';
import { ProfilePage } from './pages/ProfilePage';
import { AdminLoginPage, LoginPage, RegisterPage } from './pages/AuthPages';
import { DetectPage } from './pages/DetectPage';
import { HistoryDetailPage, HistoryPage, MyFeedbackPage } from './pages/HistoryPages';

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DetectPage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="admin/login" element={<AdminLoginPage />} />
        <Route
          path="history"
          element={
            <RequireRole role="user">
              <HistoryPage />
            </RequireRole>
          }
        />
        <Route
          path="history/:id"
          element={
            <RequireRole role="user">
              <HistoryDetailPage />
            </RequireRole>
          }
        />
        <Route
          path="feedback"
          element={
            <RequireRole role="user">
              <MyFeedbackPage />
            </RequireRole>
          }
        />
        <Route
          path="admin"
          element={
            <RequireRole role="admin">
              <AdminPage />
            </RequireRole>
          }
        />
        <Route
          path="profile"
          element={
            <RequireRole role="user">
              <ProfilePage />
            </RequireRole>
          }
        />
        <Route
          path="admin/detections"
          element={
            <RequireRole role="admin">
              <AdminDetectionsPage />
            </RequireRole>
          }
        />
        <Route
          path="admin/detections/:id"
          element={
            <RequireRole role="admin">
              <AdminDetectionDetailPage />
            </RequireRole>
          }
        />
        <Route
          path="*"
          element={
            <div className="card empty">
              ไม่พบหน้านี้ <Link to="/">กลับหน้าแรก</Link>
            </div>
          }
        />
      </Route>
    </Routes>
  );
}
