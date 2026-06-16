from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import alert, cctv, result, disaster_alerts
from services.storage import ensure_dirs
from db.database import init_db

app = FastAPI(title="실마리 (Silmari) API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alert.router, prefix="/api/alert", tags=["alert"])
app.include_router(cctv.router, prefix="/api/cctv", tags=["cctv"])
app.include_router(result.router, prefix="/api/result", tags=["result"])
app.include_router(disaster_alerts.router, prefix="/api/alerts", tags=["alerts"])

# 하위 호환: 기존 프론트엔드 경로
app.include_router(alert.router, prefix="/api/sms", tags=["legacy"])
app.include_router(cctv.router, prefix="/api/video", tags=["legacy"])
app.include_router(result.router, prefix="/api/missing", tags=["legacy"])


@app.on_event("startup")
def startup():
    ensure_dirs()
    init_db()


@app.get("/")
def root():
    return {"message": "실마리(Silmari) API 서버 실행 중"}
