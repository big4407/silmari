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
pip install -r requirements.txt
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
