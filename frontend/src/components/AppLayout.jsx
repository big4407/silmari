/** CCTV 업로드 등 단순 페이지용 상단 네비 레이아웃 */
import { NavLink, Outlet } from 'react-router-dom';
import '../App.css';

export default function AppLayout() {
  return (
    <>
      <nav className="nav">
        <span className="nav__brand">실마리 Silmari</span>
        <NavLink
          to="/dashboard"
          end
          className={({ isActive }) =>
            isActive ? 'nav__link active' : 'nav__link'
          }
        >
          대시보드
        </NavLink>
        <NavLink
          to="/cctv"
          className={({ isActive }) =>
            isActive ? 'nav__link active' : 'nav__link'
          }
        >
          CCTV 분석
        </NavLink>
        <NavLink
          to="/search-results"
          className={({ isActive }) =>
            isActive ? 'nav__link active' : 'nav__link'
          }
        >
          검색결과
        </NavLink>
      </nav>
      <Outlet />
    </>
  );
}
