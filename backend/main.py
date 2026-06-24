from fastapi import FastAPI

from backend.db.database import Base, engine
from backend.routers import message_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

# CORS 처리
# 실제 운영에서는 보안 이슈로 수정해야 할 필요 있음
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Silmari API",
    description="실마리 API 서버",
)

app.include_router(message_router.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
