from backend.core.chatbot.schemas import ExtractedSearchSlots
from backend.core.chatbot.prompts import SLOT_EXTRACTION_PROMPT
from backend.schemas.search_schema import SearchCreate
from backend.services.search_service import SearchService


def extract_slots_node(state, config):
    llm = config["configurable"]["llm"]

    extractor = llm.with_structured_output(ExtractedSearchSlots)
    # SLOT_EXTRACTION_PROMPT를 안 붙이면 LLM이 스키마의 필드 설명만 보고
    # "알 수 없으면 null" 원칙 없이 지역·시간 등을 추측해서 채울 수 있다.
    prompt_messages = [{"role": "system", "content": SLOT_EXTRACTION_PROMPT}] + list(
        state["messages"]
    )
    slots = extractor.invoke(prompt_messages)

    return {
        "region": slots.region or state.get("region"),
        "start_time": slots.start_time or state.get("start_time"),
        "end_time": slots.end_time or state.get("end_time"),
        "appearance": slots.appearance or state.get("appearance"),
        "missing_name": slots.missing_name or state.get("missing_name"),
        "gender": slots.gender or state.get("gender"),
        "age": slots.age or state.get("age"),
    }


def validate_slots_node(state):
    missing_slots = []

    if not state.get("region"):
        missing_slots.append("region")

    if not state.get("start_time") or not state.get("end_time"):
        missing_slots.append("time")

    if not state.get("appearance"):
        missing_slots.append("appearance")

    return {"missing_slots": missing_slots}


def ask_missing_node(state):
    missing_slots = state["missing_slots"]

    if "region" in missing_slots:
        response = "검색할 지역을 알려주세요. 예: 대전 동구, 고흥읍 등암리"
    elif "time" in missing_slots:
        response = "검색할 시간대를 알려주세요. 예: 오늘 오후 2시부터 4시 사이"
    else:
        response = "인상착의를 알려주세요. 예: 검은 후드티, 회색 바지, 검은 백팩"

    return {"response": response}


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
        # missing_time은 datetime 필드인데 챗봇이 뽑는 start_time/end_time은
        # "14:00" 같은 시각뿐인 자유 텍스트라 그대로 넣으면 pydantic 검증에서
        # 터진다(날짜 정보가 없음). start_date/end_date(영상 검색 기간, date 타입)로
        # 자연어 시간을 정확히 변환하는 로직은 아직 없어서 일단 기본값(최근 7일)을
        # 쓰고, 시간대 정보는 응답 문구에만 참고로 남긴다.
        search_type="2",
    )

    # create_search_with_match_count()가 내부에서 AnalysisService.run_analysis()까지
    # 동기 실행하고 매칭 건수도 같이 돌려준다 — 여기서 AnalysisRepository를 따로
    # 알 필요가 없다(레이어를 건너뛰지 않도록).
    search, match_count = service.create_search_with_match_count(search_data)

    time_note = ""
    if state.get("start_time") and state.get("end_time"):
        time_note = f" (요청하신 시간대 {state['start_time']}~{state['end_time']}는 참고용으로만 기록했고, 실제 검색 기간 필터는 아직 최근 7일 기본값을 씁니다.)"

    if match_count > 0:
        response = (
            f"검색을 완료했습니다. 조건에 맞는 후보 {match_count}건을 찾았어요. "
            f"검색 ID는 {search.id}입니다. 상세 결과는 검색 내역에서 확인해주세요.{time_note}"
        )
    else:
        response = (
            f"검색 조건으로 후보를 찾지 못했습니다(검색 ID: {search.id}). "
            f"인상착의나 지역·기간을 조금 더 넓혀서 다시 시도해보시겠어요?{time_note}"
        )

    return {
        "search_id": search.id,
        "response": response,
        # 검색이 끝났으면 슬롯을 비워서 다음 메시지부터는 새 검색으로 취급한다.
        # 안 비우면 이후 어떤 메시지를 보내도 "슬롯이 이미 다 채워져 있음"으로
        # 판단해 매번 전체 파이프라인(LLM 추출 + FashionCLIP 임베딩 + Chroma
        # 검색)을 다시 돌리게 된다.
        "region": None,
        "start_time": None,
        "end_time": None,
        "appearance": None,
        "missing_name": None,
        "gender": None,
        "age": None,
        "missing_slots": [],
    }
