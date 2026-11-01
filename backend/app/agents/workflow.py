from typing import Any

from app.agents.state import CreationState


def research_node(state: CreationState) -> CreationState:
    """Placeholder for retrieval and source collection."""
    return {
        **state,
        "status": "writing",
        "outline": [
            f"{state.get('topic', '未命名主题')}：背景与问题",
            "核心概念与证据",
            "结论与实践建议",
        ],
        "retrieved_sources": [],
    }


def writer_node(state: CreationState) -> CreationState:
    """Placeholder for model-backed drafting."""
    topic = state.get("topic", "未命名主题")
    outline = "\n".join(f"- {item}" for item in state.get("outline", []))
    return {
        **state,
        "status": "verifying",
        "draft": f"# {topic}\n\n## 写作大纲\n{outline}\n\n> 等待接入模型与检索服务。",
    }


def verification_node(state: CreationState) -> CreationState:
    """Placeholder for claim extraction and evidence verification."""
    return {
        **state,
        "status": "completed",
        "verification_notes": [
            {
                "level": "info",
                "message": "当前为流程骨架，尚未执行事实核查。",
            }
        ],
    }


def build_creation_graph() -> Any:
    """Build the Research -> Writer -> Verification MVP graph."""
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError(
            "LangGraph is not installed. Install the agent extra: pip install -e '.[agent]'"
        ) from exc

    graph = StateGraph(CreationState)
    graph.add_node("research", research_node)
    graph.add_node("writer", writer_node)
    graph.add_node("verification", verification_node)
    graph.add_edge(START, "research")
    graph.add_edge("research", "writer")
    graph.add_edge("writer", "verification")
    graph.add_edge("verification", END)
    return graph.compile()