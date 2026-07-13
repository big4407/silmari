from backend.core.chatbot.schemas import ExtractedSearchSlots
from backend.schemas.search_schema import SearchCreate
from backend.services.search_service import SearchService

from backend.repositories.region_repository import RegionRepository
from backend.repositories.video_repository import VideoRepository
from backend.services.region_resolver import RegionResolver, RegionResolveStatus
from backend.services.video_period_validator import (
    VideoPeriodValidator,
    VideoPeriodValidationStatus,
)

from datetime import date


def extract_slots_node(state, config):
    llm = config["configurable"]["llm"]

    extractor = llm.with_structured_output(ExtractedSearchSlots)
    slots = extractor.invoke(state["messages"])

    return {
        "region": slots.region or state.get("region"),
        "start_date": slots.start_date or state.get("start_date"),
        "end_date": slots.end_date or state.get("end_date"),
        "appearance": slots.appearance or state.get("appearance"),
        "missing_name": slots.missing_name or state.get("missing_name"),
        "gender": slots.gender or state.get("gender"),
        "age": slots.age or state.get("age"),
    }



def create_search_node(state, config):
    db = config["configurable"]["db"]

    service = SearchService(db)

    search_data = SearchCreate(
        user_id=state["user_id"],
        message_sn=state.get("message_sn"),
        missing_name=state.get("missing_name"),
        gender=state.get("gender"),
        age=state.get("age"),
        clothing=state.get("appearance"),
        missing_location=state.get("region"),
        missing_time=state.get("start_time"),
        start_date=state.get("start_date"),
        end_date=state.get("end_date"),
        search_type="2",
    )

    search = service.create_search(search_data)

    return {
        "search_id": search.id,
        "response": f"검색 조건을 저장했습니다. 검색 ID는 {search.id}입니다.",
        "search_inserted": True,
    }


def validate_region_node(state, config):
    """
    입력된 지역의 존재 여부를 확인하고 지역 코드를 확정한다.

    지역이 없거나 유효하지 않은 경우 사용자에게 지역을 다시 요청한다.
    """

    region = (state.get("region") or "").strip()

    if not region:
        return {
            "validation_status": "invalid",
            "response": ("검색할 지역을 알려주세요. 예: 대전 동구, 고흥읍 등암리"),
        }

    db = config["configurable"]["db"]

    region_repository = RegionRepository(db)
    region_resolver = RegionResolver(region_repository)

    result = region_resolver.resolve(region)

    if result.status == RegionResolveStatus.NOT_FOUND:
        return {
            "region": None,
            "region_code": None,
            "validation_status": "invalid",
            "response": (
                "입력한 지역을 찾을 수 없습니다. 검색할 지역을 다시 알려주세요."
            ),
        }

    if result.status == RegionResolveStatus.AMBIGUOUS:
        candidate_names = ", ".join(
            candidate.full_name for candidate in result.candidates[:5]
        )

        return {
            "region": None,
            "region_code": None,
            "validation_status": "invalid",
            "response": (
                "입력한 지역과 일치하는 후보가 여러 개 있습니다. "
                f"다음 후보를 참고하여 더 구체적으로 입력해 주세요: "
                f"{candidate_names}"
            ),
        }

    return {
        "region": result.full_name,
        "region_code": result.region_code,
        "validation_status": "valid",
        "response": None,
    }


def validate_period_node(state, config):
    """
    시작일과 종료일이 입력되었는지 확인하고,
    확정된 지역과 기간에 영상이 존재하는지 검증한다.
    """

    start_date = state.get("start_date")
    end_date = state.get("end_date")

    if not start_date or not end_date:
        return {
            "validation_status": "invalid",
            "response": ("검색할 일자를 알려주세요. 예: 2026년 6월 28일 ~ 6월 29일"),
        }

    region_code = state.get("region_code")

    if not region_code:
        return {
            "region": None,
            "validation_status": "invalid",
            "response": "먼저 검색할 지역을 알려주세요.",
        }

    db = config["configurable"]["db"]

    video_repository = VideoRepository(db)
    period_validator = VideoPeriodValidator(video_repository)

    result = period_validator.validate(
        region_code=region_code,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date),
    )

    if result.status == VideoPeriodValidationStatus.INVALID_RANGE:
        return {
            "start_date": None,
            "end_date": None,
            "validation_status": "invalid",
            "response": (
                "시작일은 종료일보다 늦을 수 없습니다. 검색할 기간을 다시 알려주세요."
            ),
        }

    if result.status == VideoPeriodValidationStatus.VIDEO_NOT_FOUND:
        return {
            "start_date": None,
            "end_date": None,
            "validation_status": "invalid",
            "response": (
                "해당 지역에는 입력한 기간의 CCTV 영상이 없습니다. "
                "다른 기간을 입력해 주세요."
            ),
        }

    return {
        "validation_status": "valid",
        "response": None,
    }


def validate_appearance_node(state):
    """
    인상착의가 입력되었는지 확인한다.
    """

    appearance = (state.get("appearance") or "").strip()

    if not appearance:
        return {
            "validation_status": "invalid",
            "response": (
                "인상착의를 알려주세요. 예: 검은 후드티, 회색 바지, 검은 백팩"
            ),
        }

    return {
        "appearance": appearance,
        "validation_status": "valid",
        "response": None,
    }


def route_validation(state):
    """
    검증 성공 여부에 따라 다음 노드 진행 여부를 결정한다.
    """

    if state.get("validation_status") == "valid":
        return "next"

    return "end"
