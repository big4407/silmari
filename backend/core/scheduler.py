from backend.db.database import SessionLocal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.services.message_service import MessageService
from datetime import date

import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def collect_messages_job():
    """
    매일 정해진 시간에 문자 API를 호출하는 작업 함수
    """

    # DB 세션 직접 생성
    db = SessionLocal()

    try:
        # 실제 비즈니스 로직 담당 객체
        service = MessageService(db=db)

        # 이미 service.collect_messages() 안에서 commit/rollback 처리함
        result = await service.collect_messages(
            page_no=1,
            num_of_rows=100,
            crt_dt=date.today(),
            rgn_nm=None,
        )

        print("[문자 수집 완료]", result)

    except Exception as e:
        # collect_messages 내부에서 rollback을 하지만,
        # 혹시 service 생성 전후 예외도 있을 수 있으니 로그는 남김
        print("[문자 수집 실패]", e)

    finally:
        # DB 연결 반환
        db.close()


def start_scheduler():
    """
    스케줄러에 작업을 등록하고 시작하는 함수
    """

    scheduler.add_job(
        collect_messages_job,
        # 매일 일정 시간에 실행
        trigger=CronTrigger(hour=16, minute=14),
        # 작업 고유 ID
        id="collect_messages_daily",
        # 같은 ID의 작업이 이미 있으면 덮어쓰기
        replace_existing=True,
    )

    for job in scheduler.get_jobs():
        logger.info(
            "ID=%s, Trigger=%s",
            job.id,
            job.trigger,
        )

    scheduler.start()
    print("[스케줄러 시작]")
