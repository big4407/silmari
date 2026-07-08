import { useState } from "react"
import { createSearch, fetchSearches, fetchSearch, deleteSearch } from "../../api/search_api"
import { fetchMe } from "../../api/auth_api"
import { API_PREFIX } from "../../api/client"
import ApiResult, { parseApiError } from "./components/ApiResult"
import DevPageHead from "./components/DevPageHead"
import "./DevCommon.css"

/** Dev — 검색 요청 CRUD 테스트 (POST/GET/DELETE /api/search-requests) */
export default function DevSearchPage() {
  // 폼 입력: 검색 ID, 실종자 이름
  const [searchId, setSearchId] = useState("")
  const [missingName, setMissingName] = useState("홍길동")
  // API 호출 상태: idle | loading | ok | err
  const [status, setStatus] = useState("idle")
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  /** 목록·상세·삭제 등 단순 API 호출 공통 래퍼 */
  const run = async (fn) => {
    setStatus("loading")
    setError(null)
    try {
      const result = await fn()
      setData(result ?? { message: "완료 (204 No Content)" })
      setStatus("ok")
    } catch (err) {
      setError(parseApiError(err))
      setStatus("err")
    }
  }

  /** 생성: 로그인 사용자 ID를 /users/me에서 가져와 검색 요청 POST */
  const create = async () => {
    setStatus("loading")
    setError(null)
    try {
      const me = await fetchMe()
      const result = await createSearch({
        user_id: me.id,
        missing_name: missingName,
        gender: "M",
        age: 70,
        clothing: "회색 상의",
        missing_location: "서울",
        search_type: "2",
      })
      setData(result)
      setSearchId(String(result.id))
      setStatus("ok")
    } catch (err) {
      setError(parseApiError(err))
      setStatus("err")
    }
  }

  return (
    <>
      <DevPageHead
        title="검색 요청"
        desc="검색 요청 CRUD. 생성 시 로그인 토큰으로 /users/me 에서 user_id를 가져옵니다."
      />

      <div className="dev-section">
        <h2>생성</h2>
        <div className="dev-form">
          <label htmlFor="dev-search-name">실종자 이름</label>
          <input
            id="dev-search-name"
            value={missingName}
            onChange={(e) => setMissingName(e.target.value)}
          />
          <button type="button" className="dev-btn" onClick={create}>
            POST {API_PREFIX}/search-requests
          </button>
        </div>
      </div>

      <div className="dev-section">
        <h2>조회 · 삭제</h2>
        <div className="dev-form">
          <label htmlFor="dev-search-id">검색 ID</label>
          <input id="dev-search-id" value={searchId} onChange={(e) => setSearchId(e.target.value)} />
          <div className="dev-form__row">
            <button
              type="button"
              className="dev-btn dev-btn--secondary"
              onClick={() => run(() => fetchSearches({ page: 1, size: 10 }))}
            >
              GET {API_PREFIX}/search-requests (목록)
            </button>
            <button
              type="button"
              className="dev-btn"
              disabled={!searchId}
              onClick={() => run(() => fetchSearch(searchId))}
            >
              GET {API_PREFIX}/search-requests/{"{id}"}
            </button>
            <button
              type="button"
              className="dev-btn dev-btn--danger"
              disabled={!searchId}
              onClick={() => run(() => deleteSearch(searchId))}
            >
              DELETE {API_PREFIX}/search-requests/{"{id}"}
            </button>
          </div>
        </div>
        <ApiResult status={status} data={data} error={error} />
      </div>
    </>
  )
}
