from langgraph.graph import END, StateGraph

from backend.core.chatbot.nodes import (
    create_search_node,
    extract_slots_node,
    validate_appearance_node,
    validate_period_node,
    validate_region_node,
)
from backend.core.chatbot.state import ChatState


def route_validation(state: ChatState) -> str:
    """
    검증 결과에 따라 다음 노드로 진행할지,
    현재 그래프 실행을 종료할지 결정한다.
    """

    if state.get("validation_status") == "valid":
        return "next"

    return "end"


def build_chatbot_graph():
    graph = StateGraph(ChatState)

    graph.add_node("extract_slots", extract_slots_node)
    graph.add_node("validate_region", validate_region_node)
    graph.add_node("validate_period", validate_period_node)
    graph.add_node("validate_appearance", validate_appearance_node)
    graph.add_node("create_search", create_search_node)

    graph.set_entry_point("extract_slots")

    graph.add_edge(
        "extract_slots",
        "validate_region",
    )

    graph.add_conditional_edges(
        "validate_region",
        route_validation,
        {
            "next": "validate_period",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "validate_period",
        route_validation,
        {
            "next": "validate_appearance",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "validate_appearance",
        route_validation,
        {
            "next": "create_search",
            "end": END,
        },
    )

    graph.add_edge(
        "create_search",
        END,
    )

    return graph.compile()
