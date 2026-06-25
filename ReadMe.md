# 실마리 (Silmari)

실종자 인상착의 파싱 + CCTV 영상 매칭 시스템

## 프로젝트 구조

```
silmari/
├── backend/          # FastAPI + LangChain + Vision
├── frontend/         # React + Leaflet 지도
├── models/yolo/      # YOLO 가중치
├── data/             # CCTV 영상, 탐지 결과
└── docker-compose.yml
```

## 실행 방법

### 백엔드

```bash
cd backend

# 방법 1: 기존 환경 복사됨 (.venv 있으면)
.venv\Scripts\activate        # Windows
uvicorn main:app --reload

# 방법 2: 새로 설치
torchreid 주석 처리후
pip install -r requirements.txt
python -m pip install --no-build-isolation "git+https://github.com/KaiyangZhou/deep-person-reid.git@f8cd150fdf77e8d9e1ed143b7f308c2c609ded50"
uvicorn main:app --reload
```

`.env` 파일은 `missing-person-finder/backend/.env`에서 수동 복사하세요.
YOLO 모델: `models/yolo/yolov8n.pt` (이미 복사됨)

### 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

- 프론트: http://localhost:5173
- API: http://localhost:8000

## API 엔드포인트

| 경로                     | 설명                   |
| ------------------------ | ---------------------- |
| `POST /api/alert/parse`  | 안내문자 인상착의 파싱 |
| `POST /api/cctv/analyze` | CCTV 영상 분석         |
| `GET /api/result/list`   | 실종자 목록 조회       |

## 페이지

- `/` — 대시보드 (지도 + 인상착의 카드)
- `/alert` — 안내문자 입력
- `/cctv` — CCTV 영상 업로드
- `/result` — 탐지 결과

# FashionCLIP 의류 속성 분류 기준

FashionCLIP을 이용해 CCTV 사람 이미지의 인상착의를 분석하기 위한 분류 후보 목록입니다.

> CCTV 영상은 해상도, 조명, 촬영 거리 등의 영향을 받으므로 지나치게 세부적인 속성은 정확하게 구분되지 않을 수 있습니다.

---

## 1. 의류 종류

### 1.1 상의 종류

```python
top_types = [
    "t-shirt",
    "shirt",
    "blouse",
    "polo shirt",
    "tank top",
    "sleeveless top",
    "crop top",
    "sweatshirt",
    "hoodie",
    "sweater",
    "cardigan",
    "vest",
    "jacket",
    "blazer",
    "coat",
    "parka",
    "uniform"
]
```

| 영문             | 의미          |
| ---------------- | ------------- |
| `t-shirt`        | 티셔츠        |
| `shirt`          | 셔츠          |
| `blouse`         | 블라우스      |
| `polo shirt`     | 폴로 셔츠     |
| `tank top`       | 민소매 탱크톱 |
| `sleeveless top` | 민소매 상의   |
| `crop top`       | 크롭톱        |
| `sweatshirt`     | 맨투맨        |
| `hoodie`         | 후드티        |
| `sweater`        | 스웨터        |
| `cardigan`       | 카디건        |
| `vest`           | 조끼          |
| `jacket`         | 재킷          |
| `blazer`         | 블레이저      |
| `coat`           | 코트          |
| `parka`          | 파카          |
| `uniform`        | 제복·유니폼   |

### 1.2 하의 종류

```python
bottom_types = [
    "pants",
    "trousers",
    "jeans",
    "slacks",
    "chinos",
    "cargo pants",
    "sweatpants",
    "joggers",
    "leggings",
    "shorts",
    "denim shorts",
    "skirt",
    "mini skirt",
    "midi skirt",
    "long skirt"
]
```

| 영문           | 의미          |
| -------------- | ------------- |
| `pants`        | 바지          |
| `trousers`     | 긴바지        |
| `jeans`        | 청바지        |
| `slacks`       | 슬랙스        |
| `chinos`       | 치노 팬츠     |
| `cargo pants`  | 카고 바지     |
| `sweatpants`   | 트레이닝 바지 |
| `joggers`      | 조거 팬츠     |
| `leggings`     | 레깅스        |
| `shorts`       | 반바지        |
| `denim shorts` | 청반바지      |
| `skirt`        | 치마          |
| `mini skirt`   | 미니스커트    |
| `midi skirt`   | 미디스커트    |
| `long skirt`   | 긴 치마       |

### 1.3 원피스 및 전신 의류

```python
full_body_types = [
    "dress",
    "mini dress",
    "midi dress",
    "maxi dress",
    "jumpsuit",
    "overalls",
    "suit",
    "tracksuit",
    "uniform"
]
```

| 영문         | 의미        |
| ------------ | ----------- |
| `dress`      | 원피스      |
| `mini dress` | 미니 원피스 |
| `midi dress` | 미디 원피스 |
| `maxi dress` | 긴 원피스   |
| `jumpsuit`   | 점프슈트    |
| `overalls`   | 멜빵바지    |
| `suit`       | 정장        |
| `tracksuit`  | 운동복 세트 |
| `uniform`    | 제복·유니폼 |

---

## 2. 색상

### 2.1 전체 색상 후보

```python
colors = [
    "white",
    "black",
    "gray",
    "silver",
    "red",
    "burgundy",
    "pink",
    "orange",
    "yellow",
    "green",
    "olive",
    "blue",
    "navy",
    "purple",
    "brown",
    "beige",
    "cream",
    "khaki",
    "gold",
    "multicolor"
]
```

### 2.2 CCTV 권장 색상 후보

CCTV 영상에서는 비슷한 색상을 세밀하게 구분하기 어렵기 때문에 다음처럼 단순화해서 사용하는 것을 권장합니다.

```python
cctv_colors = [
    "white",
    "black",
    "gray",
    "red",
    "blue",
    "green",
    "yellow",
    "brown",
    "beige",
    "pink"
]
```

| 영문     | 의미     |
| -------- | -------- |
| `white`  | 흰색     |
| `black`  | 검은색   |
| `gray`   | 회색     |
| `red`    | 빨간색   |
| `blue`   | 파란색   |
| `green`  | 초록색   |
| `yellow` | 노란색   |
| `brown`  | 갈색     |
| `beige`  | 베이지색 |
| `pink`   | 분홍색   |

---

## 3. 소매와 길이

### 3.1 소매 종류

```python
sleeve_types = [
    "sleeveless",
    "short-sleeve",
    "long-sleeve",
    "three-quarter sleeve"
]
```

| 영문                   | 의미     |
| ---------------------- | -------- |
| `sleeveless`           | 민소매   |
| `short-sleeve`         | 반소매   |
| `long-sleeve`          | 긴소매   |
| `three-quarter sleeve` | 칠부소매 |

### 3.2 의류 길이

```python
length_types = [
    "cropped",
    "short",
    "knee-length",
    "midi-length",
    "long",
    "full-length"
]
```

| 영문          | 의미                   |
| ------------- | ---------------------- |
| `cropped`     | 짧게 잘린 형태         |
| `short`       | 짧은 길이              |
| `knee-length` | 무릎 길이              |
| `midi-length` | 종아리 중간 길이       |
| `long`        | 긴 길이                |
| `full-length` | 발목까지 내려오는 길이 |

---

## 4. 핏과 형태

```python
fits = [
    "slim-fit",
    "skinny",
    "regular-fit",
    "relaxed-fit",
    "loose-fit",
    "oversized",
    "wide-leg",
    "straight-leg",
    "tapered",
    "flared"
]
```

| 영문           | 의미                        |
| -------------- | --------------------------- |
| `slim-fit`     | 몸에 비교적 붙는 핏         |
| `skinny`       | 매우 몸에 붙는 핏           |
| `regular-fit`  | 일반적인 핏                 |
| `relaxed-fit`  | 여유 있는 핏                |
| `loose-fit`    | 헐렁한 핏                   |
| `oversized`    | 크게 입는 오버사이즈        |
| `wide-leg`     | 통이 넓은 바지              |
| `straight-leg` | 일자형 바지                 |
| `tapered`      | 아래로 갈수록 좁아지는 형태 |
| `flared`       | 아래로 갈수록 넓어지는 형태 |

---

## 5. 무늬

```python
patterns = [
    "solid",
    "striped",
    "checked",
    "plaid",
    "polka-dot",
    "floral",
    "graphic",
    "logo",
    "camouflage",
    "animal-print",
    "geometric",
    "printed"
]
```

| 영문           | 의미                      |
| -------------- | ------------------------- |
| `solid`        | 단색                      |
| `striped`      | 줄무늬                    |
| `checked`      | 체크무늬                  |
| `plaid`        | 격자무늬                  |
| `polka-dot`    | 물방울무늬                |
| `floral`       | 꽃무늬                    |
| `graphic`      | 그림이나 문자가 있는 무늬 |
| `logo`         | 로고                      |
| `camouflage`   | 군복·위장무늬             |
| `animal-print` | 동물무늬                  |
| `geometric`    | 기하학무늬                |
| `printed`      | 프린트무늬                |

---

## 6. 소재

```python
materials = [
    "cotton",
    "denim",
    "leather",
    "wool",
    "knit",
    "linen",
    "silk",
    "satin",
    "velvet",
    "polyester",
    "nylon",
    "fleece",
    "suede",
    "mesh"
]
```

| 영문        | 의미       |
| ----------- | ---------- |
| `cotton`    | 면         |
| `denim`     | 데님       |
| `leather`   | 가죽       |
| `wool`      | 울         |
| `knit`      | 니트       |
| `linen`     | 리넨       |
| `silk`      | 실크       |
| `satin`     | 새틴       |
| `velvet`    | 벨벳       |
| `polyester` | 폴리에스터 |
| `nylon`     | 나일론     |
| `fleece`    | 플리스     |
| `suede`     | 스웨이드   |
| `mesh`      | 망사       |

> 소재는 CCTV 환경에서 정확히 판별하기 어려울 수 있으므로 보조 정보로 사용하는 것이 좋습니다.

---

## 7. 의류 디테일

```python
details = [
    "button-up",
    "zip-up",
    "hooded",
    "collared",
    "crew-neck",
    "v-neck",
    "turtleneck",
    "round-neck",
    "pocketed",
    "ripped",
    "distressed",
    "embroidered",
    "quilted",
    "padded",
    "belted"
]
```

| 영문          | 의미                    |
| ------------- | ----------------------- |
| `button-up`   | 단추형                  |
| `zip-up`      | 지퍼형                  |
| `hooded`      | 후드가 달린 형태        |
| `collared`    | 깃이 있는 형태          |
| `crew-neck`   | 목을 둥글게 감싸는 형태 |
| `v-neck`      | 브이넥                  |
| `turtleneck`  | 목폴라                  |
| `round-neck`  | 라운드넥                |
| `pocketed`    | 주머니가 있는 형태      |
| `ripped`      | 찢어진 형태             |
| `distressed`  | 빈티지 가공             |
| `embroidered` | 자수                    |
| `quilted`     | 누빔                    |
| `padded`      | 패딩                    |
| `belted`      | 벨트가 있는 형태        |

---

## 8. 액세서리

```python
accessories = [
    "hat",
    "cap",
    "beanie",
    "bucket hat",
    "scarf",
    "glasses",
    "sunglasses",
    "backpack",
    "shoulder bag",
    "crossbody bag",
    "handbag",
    "tote bag"
]
```

| 영문            | 의미        |
| --------------- | ----------- |
| `hat`           | 모자        |
| `cap`           | 야구모자    |
| `beanie`        | 비니        |
| `bucket hat`    | 벙거지 모자 |
| `scarf`         | 목도리      |
| `glasses`       | 안경        |
| `sunglasses`    | 선글라스    |
| `backpack`      | 백팩        |
| `shoulder bag`  | 숄더백      |
| `crossbody bag` | 크로스백    |
| `handbag`       | 핸드백      |
| `tote bag`      | 토트백      |

---

## 9. 신발

```python
shoes = [
    "sneakers",
    "running shoes",
    "boots",
    "ankle boots",
    "sandals",
    "slippers",
    "loafers",
    "heels",
    "dress shoes"
]
```

| 영문            | 의미        |
| --------------- | ----------- |
| `sneakers`      | 운동화      |
| `running shoes` | 러닝화      |
| `boots`         | 부츠        |
| `ankle boots`   | 앵클부츠    |
| `sandals`       | 샌들        |
| `slippers`      | 슬리퍼      |
| `loafers`       | 로퍼        |
| `heels`         | 구두·하이힐 |
| `dress shoes`   | 정장 구두   |

---

## 10. FashionCLIP 문장 생성 예시

### 상의 종류와 색상 조합

```python
top_texts = [
    f"a person wearing a {color} {top_type}"
    for color in cctv_colors
    for top_type in top_types
]
```

생성되는 문장 예시:

```text
a person wearing a white t-shirt
a person wearing a white shirt
a person wearing a black hoodie
a person wearing a blue jacket
```

### 하의 종류와 색상 조합

```python
bottom_texts = [
    f"a person wearing {color} {bottom_type}"
    for color in cctv_colors
    for bottom_type in bottom_types
]
```

생성되는 문장 예시:

```text
a person wearing black pants
a person wearing blue jeans
a person wearing gray sweatpants
a person wearing beige shorts
```

### 액세서리 확인 문장

액세서리는 착용 여부를 판단할 수 있도록 긍정 문장과 부정 문장을 함께 비교할 수 있습니다.

```python
hat_texts = [
    "a person wearing a hat",
    "a person not wearing a hat"
]

bag_texts = [
    "a person carrying a bag",
    "a person not carrying a bag"
]
```

---

## 11. CCTV 초기 권장 분류 범위

초기 구현에서는 너무 세밀한 항목을 모두 사용하기보다 다음 항목부터 적용하는 것이 좋습니다.

```python
cctv_appearance_labels = {
    "top_type": [
        "t-shirt",
        "shirt",
        "hoodie",
        "sweater",
        "jacket",
        "coat",
        "sleeveless top",
        "uniform"
    ],
    "bottom_type": [
        "pants",
        "jeans",
        "sweatpants",
        "leggings",
        "shorts",
        "skirt"
    ],
    "color": [
        "white",
        "black",
        "gray",
        "red",
        "blue",
        "green",
        "yellow",
        "brown",
        "beige",
        "pink"
    ],
    "sleeve": [
        "sleeveless",
        "short-sleeve",
        "long-sleeve"
    ],
    "pattern": [
        "solid",
        "striped",
        "checked",
        "graphic",
        "camouflage"
    ],
    "accessory": [
        "cap",
        "hat",
        "backpack",
        "shoulder bag",
        "crossbody bag"
    ]
}
```

소재, 세부 핏, 목 형태와 같은 정보는 CCTV 화질에서 식별하기 어려우므로 기본 분류가 안정된 후 추가하는 것을 권장합니다.

# Silmari FastAPI Authentication Module (Python 3.10)

Silmari Mission Control용 승인 기반 인증 모듈입니다. 회원가입 신청, 관리자 승인, JWT 로그인/로그아웃, 역할 기반 접근 제어(RBAC), 수사관 전용 보호 API, 세션 철회를 지원합니다.

## 구현 요구사항

| 요구사항         | API                                            | 동작                                            |
| ---------------- | ---------------------------------------------- | ----------------------------------------------- |
| SMR_AUTH_001     | `POST /api/v1/auth/login`                      | 승인된 계정만 access/refresh JWT 발급           |
| SMR_AUTH_002     | `POST /api/v1/auth/logout`                     | DB 세션 철회로 access/refresh token 즉시 무효화 |
| SMR_USER_001     | `POST /api/v1/auth/signup`                     | 승인 상태 `pending`으로 신청                    |
| SMR_USER_002     | `GET /api/v1/users/me`                         | 내 정보와 승인 상태 조회                        |
| SMR_USER_003     | `PATCH /api/v1/users/me`                       | 전화번호·부서·직급·비밀번호 수정                |
| 관리자 승인      | `PATCH /api/v1/admin/users/{user_id}/approval` | 승인·반려·정지 및 역할 부여                     |
| 수사관 전용 예시 | `GET /api/v1/operations/case-search`           | `investigator` 역할만 접근                      |

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
