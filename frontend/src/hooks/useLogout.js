/** 로그아웃 공용 훅 — logout API 호출 후 로그인 페이지로 이동. */
import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { logout } from '../api/client';

export default function useLogout() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const doLogout = useCallback(async () => {
    setLoading(true);
    try {
      await logout(); // 서버 세션 무효화 + 로컬 토큰 삭제 (실패해도 토큰은 지워짐)
    } finally {
      setLoading(false);
      navigate('/login');
    }
  }, [navigate]);

  return { doLogout, loading };
}
