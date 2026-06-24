# Silmari FastAPI Authentication Module (Python 3.10)

Silmari Mission Control용 승인 기반 인증 모듈입니다. 회원가입 신청, 관리자 승인, JWT 로그인/로그아웃, 역할 기반 접근 제어(RBAC), 수사관 전용 보호 API, 세션 철회를 지원합니다.

## 구현 요구사항

| 요구사항 | API | 동작 |
|---|---|---|
| SMR_AUTH_001 | `POST /api/v1/auth/login` | 승인된 계정만 access/refresh JWT 발급 |
| SMR_AUTH_002 | `POST /api/v1/auth/logout` | DB 세션 철회로 access/refresh token 즉시 무효화 |
| SMR_USER_001 | `POST /api/v1/auth/signup` | 승인 상태 `pending`으로 신청 |
| SMR_USER_002 | `GET /api/v1/users/me` | 내 정보와 승인 상태 조회 |
| SMR_USER_003 | `PATCH /api/v1/users/me` | 전화번호·부서·직급·비밀번호 수정 |
| 관리자 승인 | `PATCH /api/v1/admin/users/{user_id}/approval` | 승인·반려·정지 및 역할 부여 |
| 수사관 전용 예시 | `GET /api/v1/operations/case-search` | `investigator` 역할만 접근 |

## 개발용 bootstrap 관리자: 비밀번호 없이 토큰 발급

`BOOTSTRAP_ADMIN_NO_PASSWORD=true`는 **오직 `ENVIRONMENT=development` 또는 `test`에서만** 작동합니다. 이 모드에서 초기 관리자 계정에는 알 수 없는 랜덤 비밀번호가 저장되고, 로컬 요청에 한해 아래 API로 관리자 JWT를 발급할 수 있습니다.

```text
POST /api/v1/auth/dev/bootstrap-login
```

운영 환경에서는 설정 검증 단계에서 애플리케이션 시작이 차단됩니다. 실제 배포에서는 `BOOTSTRAP_ADMIN_NO_PASSWORD=false`로 두고, 강한 `BOOTSTRAP_ADMIN_PASSWORD`를 설정하십시오.

## 1. Python 3.10 가상환경

Windows PowerShell:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`Python 3.10.x`가 표시되어야 합니다.

## 2. MariaDB 데이터베이스 만들기

MariaDB에 로그인 후 한 번만 실행합니다.

```sql
CREATE DATABASE silmari_auth
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

## 3. `.env` 작성

`.env.example`을 복사합니다.

```powershell
Copy-Item .env.example .env
```

MariaDB가 `localhost:3307`, root 계정, DB `silmari_auth`일 경우 개발·테스트 `.env` 예시입니다.

```env
APP_NAME=Silmari Auth API
ENVIRONMENT=development
DATABASE_URL=mysql+pymysql://root:YOUR_DB_PASSWORD@localhost:3307/silmari_auth?charset=utf8mb4

JWT_SECRET_KEY=replace_this_with_a_random_secret_of_at_least_32_characters
JWT_ALGORITHM=HS256
JWT_ISSUER=silmari-auth
JWT_AUDIENCE=silmari-api
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

BOOTSTRAP_ADMIN_USERNAME=silmari_admin
BOOTSTRAP_ADMIN_EMAIL=admin@silmari.local
BOOTSTRAP_ADMIN_NO_PASSWORD=true
```

비밀번호에 `@`, `:`, `/`, `#`, `%`가 포함되면 URL 인코딩이 필요합니다. 예: `Silmari@2026!` → `Silmari%402026%21`.

## 4. 서버 실행

```powershell
python -m uvicorn app.main:app --reload
```

- Health: `http://127.0.0.1:8000/health`
- Swagger: `http://127.0.0.1:8000/docs`

## 5. 자동 10단계 테스트

서버를 실행한 별도 PowerShell 창에서 다음을 실행합니다.

```powershell
python .\scripts\smoke_test_auth.py
```

또는:

```powershell
.\scripts\run_auth_smoke_test.ps1
```

테스트는 아래 순서로 수행합니다.

1. `/health` 정상 응답
2. 회원가입 신청 성공 및 `pending`
3. 승인 전 로그인 403 차단
4. 개발용 bootstrap 관리자 토큰 발급
5. `pending` 사용자 목록 조회
6. 관리자 승인
7. 승인된 수사관 로그인
8. 수사관 전용 `/operations/case-search` 접근
9. 로그아웃 204
10. 동일 access token 재사용 시 401

프로젝트 내부 테스트도 가능합니다.

```powershell
pytest -q app/tests/test_auth_flow.py
```

## 보호 API 권한 예시

`/api/v1/operations/case-search`는 현재 오직 `investigator`만 접근할 수 있습니다.

```python
@router.get("/case-search")
def case_search_access(
    current_user: User = Depends(require_roles(UserRole.INVESTIGATOR)),
):
    ...
```

향후 영상 원본 접근, 사건 생성, 사용자 관리 API마다 `require_roles(...)` 의 허용 역할을 다르게 지정하십시오.

## 운영 전 필수 변경

- `ENVIRONMENT=production`
- `BOOTSTRAP_ADMIN_NO_PASSWORD=false` 또는 해당 행 제거
- 초기 관리자 비밀번호 및 JWT 키를 강한 무작위 값으로 변경
- HTTPS, 로그인 rate limit, 감사 로그, Alembic migration, 정확한 CORS 도메인 설정
- `.env`와 DB 파일을 Git에 올리지 않도록 `.gitignore`에 등록

## 반복 테스트 시 참고

`scripts/smoke_test_auth.py`는 매번 새로운 수사관 아이디를 생성하므로 반복 실행할 수 있습니다. 다만 bootstrap 관리자 계정의 아이디·이메일을 변경했거나, 처음부터 완전히 새 데이터베이스로 점검하고 싶다면 개발 DB에서만 다음을 실행한 뒤 서버를 재시작하십시오.

```sql
DROP DATABASE silmari_auth;
CREATE DATABASE silmari_auth
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

이 명령은 해당 데이터베이스의 모든 사용자·세션 데이터를 삭제합니다.
