"""
재난문자 수집·저장 비즈니스 로직.

[흐름] DisasterMessageClient → is_missing_person_message 필터 → MessageRepository
[호출] routes/messages.py, Dashboard 재난문자 연동
"""

import time

from langchain_community.callbacks import get_openai_callback
from sqlalchemy.orm import Session

from backend.core.llm.alert_parser import ALERT_PARSE_MODEL, parse_alert_message
from backend.db.models import LlmCallType, Message
from backend.repositories.message_repository import MessageRepository
from backend.schemas.message_schema import (
    AlertParseResponse,
    MessageCreate,
    MessageResponse,
    MessageListResponse,
)
from backend.services.llm_call_service import LlmCallService
from backend.services.missing_person_case_service import MissingPersonCaseService
from backend.utils.datetime_parser import parse_date, parse_datetime
from backend.utils.message_filter import is_missing_person_message

from fastapi import HTTPException
from datetime import date
import httpx
from backend.core.config import settings


class MessageService:
    def __init__(self, db: Session):
        self.db = db
        # self.client = DisasterMessageClient()
        self.repository = MessageRepository(db)
        self.llm_call_service = LlmCallService(db)
        self.missing_person_case_service = MissingPersonCaseService(db)

    def parse_alert(self, msg_cn: str, *, user_id: str | None = None) -> AlertParseResponse:
        """안내문자 본문에서 LLM으로 실종자 정보(이름·성별·나이·인상착의)를 뽑는다.

        실제 문자는 라벨 없는 자유 서식이라 정규식으로는 한계가 있어 LLM을 쓴다
        (core/llm/alert_parser.py). 대시보드의 "실종자 검색" 흐름에서
        검색 요청(SearchCreate) 필드를 채우는 데 그대로 쓰인다.

        챗봇 호출(chatbot_service.py)과 동일하게 get_openai_callback()으로 감싸서
        llm_call 테이블에 기록한다(call_type="3" = 안내문자 파싱) — LLM 운영
        관리 화면(모델별 사용량·프롬프트 로그)에서 같이 집계되도록.
        """
        start = time.perf_counter()
        call_status = "1"
        error_msg = None
        result = None
        callback = None

        try:
            with get_openai_callback() as cb:
                callback = cb
                result = parse_alert_message(msg_cn)
        except Exception as e:
            call_status = "0"
            error_msg = str(e)[:255]
            raise
        finally:
            self.llm_call_service.record_call(
                call_type=LlmCallType.ALERT_PARSE,
                model_name=ALERT_PARSE_MODEL,
                prompt=msg_cn,
                response=result.model_dump_json() if result else None,
                start_time=start,
                callback=callback,
                status=call_status,
                error_msg=error_msg,
                user_id=user_id,
            )

        return AlertParseResponse(**result.model_dump())

    def _get_or_404(self, sn: str):
        """
        문자를 sn으로 조회하고 없으면 404 예외를 발생시킵니다.
        """
        message = self.repository.find_by_sn(sn)
        if not message:
            raise HTTPException(status_code=404, detail="문자를 찾을 수 없습니다.")

        return message

    async def collect_messages(
        self,
        page_no: int = 1,
        num_of_rows: int = 10,
        crt_dt: str | None = None,
        rgn_nm: str | None = None,
    ) -> dict:
        items = await self.fetch_messages(
            page_no=page_no,
            num_of_rows=num_of_rows,
            crt_dt=crt_dt,
            rgn_nm=rgn_nm,
        )

        fetched_count = len(items)
        filtered_out_count = 0
        saved_count = 0
        skipped_duplicate_count = 0

        try:
            for item in items:
                msg_cn = item.get("MSG_CN", "")
                dst_se_nm = item.get("DST_SE_NM")

                if not is_missing_person_message(
                    msg_cn=msg_cn,
                    dst_se_nm=dst_se_nm,
                ):
                    filtered_out_count += 1
                    continue

                sn = str(item["SN"])

                if self.repository.find_by_sn(sn):
                    skipped_duplicate_count += 1
                    continue

                message = Message(
                    sn=sn,
                    crt_dt=parse_datetime(item.get("CRT_DT")),
                    msg_cn=msg_cn,
                    rcptn_rgn_nm=item.get("RCPTN_RGN_NM"),
                    emrg_step_nm=item.get("EMRG_STEP_NM"),
                    dst_se_nm=dst_se_nm,
                    reg_ymd=parse_date(item.get("REG_YMD")),
                    mdfcn_ymd=parse_date(item.get("MDFCN_YMD")),
                )

                self.repository.save(message)
                saved_count += 1

                # 실종자 관리 케이스 자동 생성 — sn 하나당 케이스 하나(멱등).
                # 이름/성별/나이/인상착의는 여기서 LLM으로 안 뽑는다 — 수집은
                # 문자를 한 번에 여러 건씩 배치로 가져오는데, 매번 LLM을
                # 돌리면 비용이 커진다. 원문(msg_cn)과 수신지역명(이미 구조화된
                # 값이라 LLM 불필요)만 저장해두고, 담당자가 실제로 케이스를
                # 열 때 필요하면 그 1건만 파싱한다(missing_person_case_service.
                # enrich_from_message).
                self.missing_person_case_service.create_from_message(
                    sn,
                    msg_cn=msg_cn,
                    missing_location=(
                        item.get("RCPTN_RGN_NM")[:20] if item.get("RCPTN_RGN_NM") else None
                    ),
                )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return {
            "fetched_count": fetched_count,
            "filtered_out_count": filtered_out_count,
            "saved_count": saved_count,
            "skipped_duplicate_count": skipped_duplicate_count,
        }

    def manual_input_message(self, message_data: MessageCreate) -> MessageResponse:
        """
        수동으로 문자를 입력하는 서비스 함수
        """
        message = self.repository.insert(
            sn=message_data.sn,
            crt_dt=message_data.crt_dt,
            msg_cn=message_data.msg_cn,
            rcptn_rgn_nm=message_data.rcptn_rgn_nm,
            emrg_step_nm=message_data.emrg_step_nm,
            dst_se_nm=message_data.dst_se_nm,
            reg_ymd=message_data.reg_ymd,
            mdfcn_ymd=message_data.mdfcn_ymd,
        )

        return MessageResponse.model_validate(message)

    def get_message(self, sn: str) -> MessageResponse:
        message = self._get_or_404(sn)
        return MessageResponse.model_validate(message)

    # services/message_service.py

    def get_message_list(
        self,
        page: int,
        per_page: int,
        search_content: str | None,
        start_date: date | None = None,
        end_date: date | None = None,
        region: str | None = None,
        order_by: str = "latest",
    ) -> MessageListResponse:

        messages, total = self.repository.find_all(
            page=page,
            per_page=per_page,
            search_content=search_content,
            start_date=start_date,
            end_date=end_date,
            region=region,
            order_by=order_by,
        )

        return MessageListResponse(
            items=[MessageResponse.model_validate(message) for message in messages],
            total=total,
            page=page,
            size=per_page,
        )

    def delete_message(self, sn: str) -> None:
        """
        sn을 받아서 메시지를 삭제하는 함수
        """
        message = self._get_or_404(sn)
        self.repository.delete(message)

    async def fetch_messages(
        self,
        page_no: int = 1,
        num_of_rows: int = 10,
        crt_dt: str | None = None,
        rgn_nm: str | None = None,
    ) -> list[dict]:
        service_key = settings.disaster_service_key
        if not service_key:
            raise HTTPException(
                status_code=503,
                detail=(
                    "재난문자 API 키가 설정되지 않았습니다. "
                    "프로젝트 루트 .env 에 SAFETYDATA_SERVICE_KEY 를 채운 뒤 "
                    "백엔드를 재시작하세요."
                ),
            )

        params = {
            "serviceKey": service_key,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
            "returnType": "json",
        }

        if crt_dt:
            params["crtDt"] = crt_dt

        if rgn_nm:
            params["rgnNm"] = rgn_nm

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    settings.disaster_api_url,
                    params=params,
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise HTTPException(
                    status_code=502,
                    detail=f"재난안전데이터 API 호출에 실패했습니다: {exc}",
                ) from exc

        data = response.json()

        body = data.get("body")

        if isinstance(body, list):
            return body

        if isinstance(body, dict):
            items = body.get("items") or body.get("item") or []
            if isinstance(items, list):
                return items
            return [items]

        return []