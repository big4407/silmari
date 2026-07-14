"""Manual API test checklist.

This file intentionally contains API payload examples rather than a database-isolated test fixture.
Run the app first, then execute the curl commands in README.md.
"""

SIGNUP_PAYLOAD = {
    "username": "investigator01",
    "email": "investigator01@example.go.kr",
    "password": "StrongPassword123!",
    "full_name": "홍길동",
    "organization": "서울시 관제센터",
    "department": "실종대응팀",
    "position": "주무관",
    "phone": "010-1234-5678",
    "requested_role": "2",  # UserRole: 1=admin, 2=investigator, 3=public_official
}
