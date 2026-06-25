"""Run the ten authentication checks against an already-running local API server.

Example:
    python scripts/smoke_test_auth.py
    python scripts/smoke_test_auth.py --base-url http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import sys
import time
import uuid
from typing import Any

import httpx


_RUN_ID = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"

SIGNUP_PAYLOAD = {
    "username": f"investigator_{_RUN_ID}",
    "email": f"investigator_{_RUN_ID}@example.go.kr",
    "password": "StrongPassword123!",
    "full_name": "홍길동",
    "organization": "서울시 관제센터",
    "department": "실종대응팀",
    "position": "주무관",
    "phone": "010-1234-5678",
    "requested_role": "investigator",
}


def show_step(number: int, passed: bool, message: str) -> None:
    icon = "PASS" if passed else "FAIL"
    print(f"[{icon}] {number}. {message}")


def require(response: httpx.Response, expected_status: int, step: int, label: str) -> dict[str, Any] | None:
    if response.status_code != expected_status:
        show_step(step, False, f"{label} | expected={expected_status}, actual={response.status_code}, body={response.text}")
        raise RuntimeError(f"Step {step} failed")
    show_step(step, True, label)
    content_type = response.headers.get("content-type", "")
    # FastAPI 204 responses have no body even if a JSON content-type header remains.
    return response.json() if response.content and "application/json" in content_type else None


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    try:
        with httpx.Client(timeout=15.0) as client:
            # 1.
            health = require(client.get(f"{base}/health"), 200, 1, "/health 정상 응답")
            if health is None or health.get("status") != "ok":
                raise RuntimeError("Health body is invalid")

            # 2.
            signup = require(client.post(f"{base}/api/v1/auth/signup", json=SIGNUP_PAYLOAD), 201, 2, "회원가입 신청 → pending")
            assert signup is not None
            user_id = signup["user"]["id"]
            if signup["user"]["approval_status"] != "pending":
                raise RuntimeError("Signup did not create a pending account")

            # 3.
            require(
                client.post(
                    f"{base}/api/v1/auth/login",
                    json={"username": SIGNUP_PAYLOAD["username"], "password": SIGNUP_PAYLOAD["password"]},
                ),
                403,
                3,
                "승인 전 로그인 차단",
            )

            # 4.
            bootstrap = require(
                client.post(f"{base}/api/v1/auth/dev/bootstrap-login"),
                200,
                4,
                "개발용 bootstrap 관리자 토큰 발급",
            )
            assert bootstrap is not None
            admin_token = bootstrap["access_token"]

            # 5.
            pending = require(
                client.get(f"{base}/api/v1/admin/users?approval_status=pending", headers=bearer(admin_token)),
                200,
                5,
                "pending 사용자 목록 조회",
            )
            assert pending is not None
            if not any(item["id"] == user_id for item in pending):
                raise RuntimeError("New pending user was not returned")

            # 6.
            require(
                client.patch(
                    f"{base}/api/v1/admin/users/{user_id}/approval",
                    headers=bearer(admin_token),
                    json={"status": "approved", "role": "investigator"},
                ),
                200,
                6,
                "관리자 승인 처리",
            )

            # 7.
            investigator_login = require(
                client.post(
                    f"{base}/api/v1/auth/login",
                    json={"username": SIGNUP_PAYLOAD["username"], "password": SIGNUP_PAYLOAD["password"]},
                ),
                200,
                7,
                "승인된 수사관 로그인",
            )
            assert investigator_login is not None
            investigator_token = investigator_login["access_token"]

            # 8.
            require(
                client.get(f"{base}/api/v1/operations/case-search", headers=bearer(investigator_token)),
                200,
                8,
                "수사관 전용 case-search 접근",
            )

            # 9.
            require(
                client.post(f"{base}/api/v1/auth/logout", headers=bearer(investigator_token)),
                204,
                9,
                "로그아웃 성공",
            )

            # 10.
            require(
                client.get(f"{base}/api/v1/operations/case-search", headers=bearer(investigator_token)),
                401,
                10,
                "동일 access token 재사용 차단",
            )

    except (httpx.HTTPError, RuntimeError, AssertionError) as exc:
        print(f"\nAuthentication smoke test failed: {exc}")
        return 1

    print("\nAll 10 authentication checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
