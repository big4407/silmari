FROM python:3.10-slim

# 빌드 도구 + OpenCV/torchreid 가 필요로 하는 그래픽 시스템 라이브러리
# (libxcb.so.1 등 — slim 이미지엔 빠져 있어 torchreid 빌드/실행 시 ImportError 발생)
RUN apt-get update && apt-get install -y --no-install-recommends \
        git build-essential \
        libxcb1 libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# 1) 메인 의존성 (torch/numpy/Cython 포함)
RUN pip install --no-cache-dir -r requirements.txt

# 2) 빌드 도구 보장
RUN pip install --no-cache-dir "setuptools<70" wheel

# 3) torchreid 를 git 에서 설치
RUN pip install --no-cache-dir --no-build-isolation \
       "git+https://github.com/KaiyangZhou/deep-person-reid.git@f8cd150fdf77e8d9e1ed143b7f308c2c609ded50"

COPY . .

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]