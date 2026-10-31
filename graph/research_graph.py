from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from graph.state import ResearchState

from graph.nodes import (
    planner_node,
    human_approval_node,
    revise_plan_node,
    route_after_approval,
    search_agent_node,
    route_after_search_agent,
    search_tool_node,
    analyze_node,
    evaluation_node,
    prepare_next_search_node,
    summary_node,
    statistics_node,
    route_after_evaluation,
)


# =========================================================
# CHECKPOINTER
# =========================================================

checkpointer = InMemorySaver()


# =========================================================
# ROUTING HELPERS
# =========================================================

def route_after_planner(state):
    if state.get("error"):
        return "end"

    return "human_approval"


def route_after_revision(state):
    if state.get("error"):
        return "end"

    return "human_approval"


# =========================================================
# GRAPH BUILDER
# =========================================================

def build_research_graph():
    builder = StateGraph(ResearchState)

    # -------------------------
    # Nodes
    # -------------------------

    builder.add_node("planner", planner_node)
    builder.add_node("human_approval", human_approval_node)
    builder.add_node("revise_plan", revise_plan_node)

    builder.add_node("search_agent", search_agent_node)
    builder.add_node("search_tools", search_tool_node)

    builder.add_node("analyze", analyze_node)
    builder.add_node("evaluate", evaluation_node)
    builder.add_node("prepare_next_search", prepare_next_search_node)

    builder.add_node("summary", summary_node)
    builder.add_node("statistics", statistics_node)

    # -------------------------
    # Initial planning
    # -------------------------

    builder.add_edge(START, "planner")

    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "human_approval": "human_approval",
            "end": END,
        },
    )

    # -------------------------
    # Human approval routing
    # -------------------------

    builder.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {
            "search_agent": "search_agent",
            "revise_plan": "revise_plan",
            "end": END,
        },
    )

    # -------------------------
    # Revised plan must be approved again
    # -------------------------

    builder.add_conditional_edges(
        "revise_plan",
        route_after_revision,
        {
            "human_approval": "human_approval",
            "end": END,
        },
    )

    # -------------------------
    # Search and tool calling
    # -------------------------

    builder.add_conditional_edges(
        "search_agent",
        route_after_search_agent,
        {
            "search_tools": "search_tools",
            "analyze": "analyze",
            "end": END,
        },
    )

    builder.add_edge("search_tools", "analyze")
    builder.add_edge("analyze", "evaluate")

    # -------------------------
    # Evaluation loop
    # -------------------------

    builder.add_conditional_edges(
        "evaluate",
        route_after_evaluation,
        {
            "summary": "summary",
            "search_again": "prepare_next_search",
            "end": END,
        },
    )

    builder.add_edge("prepare_next_search", "search_agent")

    # -------------------------
    # Final report
    # -------------------------

    builder.add_edge("summary", "statistics")
    builder.add_edge("statistics", END)

    return builder.compile(checkpointer=checkpointer)


research_graph = build_research_graph()