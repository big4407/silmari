"""End-to-end authentication workflow test for the Silmari FastAPI API.

Run from the project root:
    pytest -q app/tests/test_auth_flow.py
"""

from __future__ import annotations

import os
from pathlib import Path

# Set every configuration item BEFORE importing app modules, because the app reads
# configuration when it creates the SQLAlchemy engine.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_DB = PROJECT_ROOT / "silmari_auth_test.db"
if TEST_DB.exists():
    TEST_DB.unlink()

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL_OVERRIDE"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["JWT_SECRET_KEY"] = "test-only-jwt-secret-key-at-least-thirty-two-characters"
os.environ["BOOTSTRAP_ADMIN_USERNAME"] = "bootstrap_admin"
os.environ["BOOTSTRAP_ADMIN_EMAIL"] = "bootstrap_admin@silmari.local"
os.environ.pop("BOOTSTRAP_ADMIN_PASSWORD", None)
os.environ["BOOTSTRAP_ADMIN_NO_PASSWORD"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402
from backend.db.models import ApprovalStatus, UserRole  # noqa: E402


INVESTIGATOR_PAYLOAD = {
    "username": "investigator01",
    "email": "investigator01@example.go.kr",
    "password": "StrongPassword123!",
    "full_name": "홍길동",
    "organization": "서울시 관제센터",
    "department": "실종대응팀",
    "position": "주무관",
    "phone": "010-1234-5678",
    "requested_role": UserRole.INVESTIGATOR.value,
}


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_required_authentication_flow() -> None:
    with TestClient(app) as client:
        # 1. Health endpoint.
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        # 2. Sign-up starts in pending status.
        response = client.post("/api/auth/signup", json=INVESTIGATOR_PAYLOAD)
        assert response.status_code == 201, response.text
        created_user = response.json()["user"]
        assert created_user["approval_status"] == ApprovalStatus.PENDING.value
        user_id = created_user["id"]

        # 3. A pending user cannot log in.
        response = client.post(
            "/api/auth/login",
            json={
                "username": INVESTIGATOR_PAYLOAD["username"],
                "password": INVESTIGATOR_PAYLOAD["password"],
            },
        )
        assert response.status_code == 403

        # 4. Local development/test bootstrap admin receives a token without an admin password.
        response = client.post("/api/auth/dev/bootstrap-login")
        assert response.status_code == 200, response.text
        admin_access_token = response.json()["access_token"]

        # 5. The bootstrap admin can list pending accounts.
        response = client.get(
            "/api/admin/users?approval_status=pending",
            headers=bearer(admin_access_token),
        )
        assert response.status_code == 200, response.text
        assert any(user["id"] == user_id for user in response.json())

        # 6. The bootstrap admin approves the investigator request.
        response = client.patch(
            f"/api/admin/users/{user_id}/approval",
            headers=bearer(admin_access_token),
            json={
                "status": ApprovalStatus.APPROVED.value,
                "role": UserRole.INVESTIGATOR.value,
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["approval_status"] == ApprovalStatus.APPROVED.value
        assert response.json()["role"] == UserRole.INVESTIGATOR.value

        # 7. Approved investigator can log in with their own password.
        response = client.post(
            "/api/auth/login",
            json={
                "username": INVESTIGATOR_PAYLOAD["username"],
                "password": INVESTIGATOR_PAYLOAD["password"],
            },
        )
        assert response.status_code == 200, response.text
        investigator_access_token = response.json()["access_token"]

        # 8. The investigator-only protected endpoint is accessible.
        response = client.get(
            "/api/operations/case-search",
            headers=bearer(investigator_access_token),
        )
        assert response.status_code == 200, response.text
        assert response.json()["role"] == UserRole.INVESTIGATOR.value

        # 9. Logout revokes the active session.
        response = client.post(
            "/api/auth/logout",
            headers=bearer(investigator_access_token),
        )
        assert response.status_code == 204, response.text

        # 10. The revoked access token cannot be reused.
        response = client.get(
            "/api/operations/case-search",
            headers=bearer(investigator_access_token),
        )
        assert response.status_code == 401, response.text


if __name__ == "__main__":
    # Allows: python app/tests/test_auth_flow.py
    test_required_authentication_flow()
    print("All 10 authentication flow checks passed.")
