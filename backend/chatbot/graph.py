from langgraph.graph import StateGraph, END
from backend.chatbot.state import ChatState
from backend.chatbot.nodes import (
    extract_slots_node,
    validate_slots_node,
    ask_missing_node,
    create_search_node,
)


def route_after_validation(state):
    if state["missing_slots"]:
        return "ask_missing"

    return "create_search"


def build_chatbot_graph():
    graph = StateGraph(ChatState)

    graph.add_node("extract_slots", extract_slots_node)
    graph.add_node("validate_slots", validate_slots_node)
    graph.add_node("ask_missing", ask_missing_node)
    graph.add_node("create_search", create_search_node)

    graph.set_entry_point("extract_slots")

    graph.add_edge("extract_slots", "validate_slots")

    graph.add_conditional_edges(
        "validate_slots",
        route_after_validation,
        {
            "ask_missing": "ask_missing",
            "create_search": "create_search",
        },
    )

    graph.add_edge("ask_missing", END)
    graph.add_edge("create_search", END)

    return graph.compile()
