from backend.db.database import SessionLocal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.services.message_service import MessageService
from datetime import date, timedelta

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


async def process_videos_job():
    """매일 전날 생성된 CCTV 영상을 Video/VideoDetail 및 Chroma 에 저장.

    영상 경로 수집은 VideoService.collect_video_paths 에 위임한다.
    같은 file_path 는 이미 처리된 것으로 보고 건너뛴다(중복 방지).
    """
    db = SessionLocal()
    try:
        from backend.services.video_service import VideoService

        service = VideoService(db=db)

        # 전날 하루 (start=end=어제)
        yesterday = date.today() - timedelta(days=1)
        video_paths = service.collect_video_paths(yesterday, yesterday)

        if not video_paths:
            print("[영상 처리] 대상 영상이 없습니다.")
            return

        result = service.process_videos(video_paths)
        print(
            f"[영상 처리 완료] 대상 {len(video_paths)}건 "
            f"| 처리 {result['processed']} | 중복 건너뜀 {result['skipped']}"
        )
    except Exception as e:
        db.rollback()
        print("[영상 처리 실패]", e)
    finally:
        db.close()


def start_scheduler():
    """
    스케줄러에 작업을 등록하고 시작하는 함수
    """

    scheduler.add_job(
        collect_messages_job,
        # 매일 일정 시간에 실행
        trigger=CronTrigger(minute=16, second=30),
        # 작업 고유 ID
        id="collect_messages_daily",
        # 같은 ID의 작업이 이미 있으면 덮어쓰기
        replace_existing=True,
    )

    scheduler.add_job(
        process_videos_job,
        # 매일 새벽, 전날 영상 처리 (문자 수집과 시간 분리)
        trigger=CronTrigger(hour=17, minute=40, second=59),
        id="process_videos_daily",
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
