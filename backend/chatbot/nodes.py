from backend.chatbot.schemas import ExtractedSearchSlots
from backend.schemas.search_schema import SearchCreate
from backend.services.search_service import SearchService


def extract_slots_node(state, config):
    llm = config["configurable"]["llm"]

    extractor = llm.with_structured_output(ExtractedSearchSlots)
    slots = extractor.invoke(state["messages"])

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
        missing_time=state.get("start_time"),
        search_type="C",
    )

    search = service.create_search(search_data)

    return {
        "search_id": search.id,
        "response": f"검색 조건을 저장했습니다. 검색 ID는 {search.id}입니다.",
    }
