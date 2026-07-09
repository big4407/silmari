/** 로그아웃 공용 훅 — logout API 호출 후 로그인 페이지로 이동. */
import { useCallback, useState } from 'react';
import { logout } from '../api/client';

export default function useLogout() {
  const [loading, setLoading] = useState(false);

  const doLogout = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    try {
      await logout();
    } finally {
      setLoading(false);
      window.location.replace('/login');
    }
  }, [loading]);

  return { doLogout, loading };
}
