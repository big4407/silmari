import { useState } from "react"
import { fetchAdminUsers, updateUserApproval } from "../../api/auth_api"
import ApiResult, { parseApiError } from "./components/ApiResult"
import "./DevCommon.css"

export default function DevAdminPage() {
  const [approvalFilter, setApprovalFilter] = useState("")
  const [userId, setUserId] = useState("")
  const [status, setStatus] = useState("idle")
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const run = async (fn) => {
    setStatus("loading")
    setError(null)
    try {
      const result = await fn()
      setData(result ?? { message: "완료" })
      setStatus("ok")
    } catch (err) {
      setError(parseApiError(err))
      setStatus("err")
    }
  }

  return (
    <>
      <h1 className="dev-page__title">관리자</h1>
      <p className="dev-page__desc">
        admin 역할 토큰이 필요합니다.{" "}
        <a href="/dev/auth">인증</a> 페이지에서 bootstrap-login 또는 관리자 계정으로 로그인하세요.
      </p>

      <div className="dev-section">
        <h2>회원 목록</h2>
        <div className="dev-form">
          <label htmlFor="dev-admin-filter">승인 상태 필터</label>
          <select
            id="dev-admin-filter"
            value={approvalFilter}
            onChange={(e) => setApprovalFilter(e.target.value)}
          >
            <option value="">전체</option>
            <option value="pending">pending</option>
            <option value="approved">approved</option>
            <option value="rejected">rejected</option>
            <option value="suspended">suspended</option>
          </select>
          <button
            type="button"
            className="dev-btn"
            onClick={() =>
              run(() => fetchAdminUsers(approvalFilter || undefined))
            }
          >
            GET /api/v1/admin/users
          </button>
        </div>
      </div>

      <div className="dev-section">
        <h2>승인 처리</h2>
        <div className="dev-form">
          <label htmlFor="dev-admin-user-id">사용자 ID (UUID)</label>
          <input
            id="dev-admin-user-id"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="목록에서 복사"
          />
          <div className="dev-form__row">
            <button
              type="button"
              className="dev-btn"
              disabled={!userId}
              onClick={() =>
                run(() =>
                  updateUserApproval(userId, {
                    status: "approved",
                    role: "investigator",
                  }),
                )
              }
            >
              승인 (investigator)
            </button>
            <button
              type="button"
              className="dev-btn dev-btn--danger"
              disabled={!userId}
              onClick={() =>
                run(() =>
                  updateUserApproval(userId, {
                    status: "rejected",
                    rejection_reason: "dev 테스트 반려",
                  }),
                )
              }
            >
              반려
            </button>
          </div>
        </div>
        <ApiResult status={status} data={data} error={error} />
      </div>
    </>
  )
}
