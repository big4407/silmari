/** 관리자 뷰 라우터 — navConfig.viewId → views/ 컴포넌트 매핑 */
import { Navigate, useParams } from "react-router-dom"
import { DEFAULT_VIEW, isValidViewId } from "./navConfig"
import { ADMIN_VIEWS } from "./views"

export default function AdminViewPage() {
  const { viewId } = useParams()

  if (!viewId) {
    return <Navigate to={`/admin/${DEFAULT_VIEW}`} replace />
  }

  if (!isValidViewId(viewId)) {
    return <Navigate to={`/admin/${DEFAULT_VIEW}`} replace />
  }

  const View = ADMIN_VIEWS[viewId]
  return <View />
}
