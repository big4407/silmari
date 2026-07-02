/** 로그인 가드 — 미로그인 시 /login 으로 리다이렉트. */
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { isAuthenticated } from '../api/client';

export default function RequireAuth() {
  const location = useLocation();

  if (!isAuthenticated()) {
    // 로그인 후 원래 가려던 곳으로 돌아올 수 있게 from 전달
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}
