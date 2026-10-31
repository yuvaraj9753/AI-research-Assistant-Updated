from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class ResearchState(TypedDict, total=False):

    # -------------------------
    # User Input
    # -------------------------

    query: str
    research_type: str
    research_depth: str

    # -------------------------
    # Planning
    # -------------------------

    research_plan: dict
    human_feedback: str
    plan_approved: bool

    # -------------------------
    # Research
    # -------------------------

    search_queries: list[str]
    search_results: list[dict]
    sources: list[str]

    # -------------------------
    # Analysis
    # -------------------------

    insights: list[str]
    analysis: dict

    # -------------------------
    # Evaluation
    # -------------------------

    enough_information: bool
    evaluation_reason: str
    research_iterations: int

    # -------------------------
    # Final Report
    # -------------------------

    final_report: dict

    # -------------------------
    # Statistics
    # -------------------------

    start_time: float
    statistics: dict

    # -------------------------
    # Error
    # -------------------------

    error: str

    # -------------------------
    # Optional message state
    # -------------------------

    messages: Annotated[list, add_messages]