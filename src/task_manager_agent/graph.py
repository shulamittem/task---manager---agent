"""LangGraph graph: classify_node -> (conditional) -> extract_node -> END."""

from langgraph.graph import END, StateGraph

from task_manager_agent.llm import classify_and_extract
from task_manager_agent.models import MessageState


def classify_node(state: MessageState) -> dict:
    """Call the LLM once to classify + extract. Never raises."""
    if not state.raw_text or not state.raw_text.strip():
        return {
            "is_task": False,
            "needs_review": True,
            "error": "empty or non-text message payload",
        }

    try:
        result = classify_and_extract(state.raw_text)
    except Exception as e:
        return {"needs_review": True, "error": str(e)}

    return {
        "is_task": result.is_task,
        "title": result.title,
        "due_date": result.due_date,
        "assignee": result.assignee,
        "priority": result.priority,
    }


def extract_node(state: MessageState) -> dict:
    """Pure normalization of fields classify_node already returned. No I/O."""
    updates: dict = {}

    if state.title is not None:
        stripped = state.title.strip()
        if stripped != state.title:
            updates["title"] = stripped

    return updates


def _route_after_classify(state: MessageState) -> str:
    if state.error is not None or state.is_task is not True:
        return END
    return "extract_node"


def build_graph():
    """Assemble and compile the classify -> extract graph."""
    builder = StateGraph(MessageState)

    builder.add_node("classify_node", classify_node)
    builder.add_node("extract_node", extract_node)

    builder.set_entry_point("classify_node")
    builder.add_conditional_edges(
        "classify_node",
        _route_after_classify,
        {END: END, "extract_node": "extract_node"},
    )
    builder.add_edge("extract_node", END)

    return builder.compile()
