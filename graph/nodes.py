import json
import time

from langgraph.types import interrupt
from langgraph.prebuilt import ToolNode

from services.groq_service import get_llm
from services.search_service import web_search
from utils.helpers import safe_json_parse

from prompts.planner_prompt import PLANNER_PROMPT
from prompts.analysis_prompt import ANALYSIS_PROMPT
from prompts.evaluation_prompt import EVALUATION_PROMPT
from prompts.summary_prompt import SUMMARY_PROMPT

search_tool_node = ToolNode([web_search])


def planner_node(state):
    try:
        prompt = PLANNER_PROMPT.format(
            query=state["query"],
            research_type=state["research_type"],
            research_depth=state["research_depth"],
        )
        response = get_llm().invoke(prompt)
        plan = safe_json_parse(response.content)

        if not isinstance(plan, dict) or plan.get("error"):
            return {"error": "Planner could not produce valid JSON."}

        for key in (
            "objective",
            "sub_questions",
            "search_queries",
            "focus_areas",
        ):
            if key not in plan:
                plan[key] = [] if key != "objective" else ""

        if not plan["objective"]:
            return {
                "error": "Planner returned a plan without an objective."
            }

        return {
            "research_plan": plan,
            "search_queries": plan["search_queries"],
            "plan_approved": False,
            "research_iterations": 0,
            "sources": [],
            "error": "",
        }

    except Exception as e:
        return {"error": f"Planner failed: {e}"}


def human_approval_node(state):
    # LangGraph pauses here. Resume value is the user's decision.
    decision = interrupt({
        "type": "research_plan_approval",
        "message": "Review the research plan before research begins.",
        "plan": state.get("research_plan", {}),
    })

    if not isinstance(decision, dict):
        decision = {}

    return {
        "plan_approved": decision.get("approved") is True,
        "human_feedback": str(
            decision.get("feedback", "")
        ).strip(),
    }


def route_after_approval(state):
    if state.get("error"):
        return "end"

    return (
        "search_agent"
        if state.get("plan_approved") is True
        else "revise_plan"
    )


def revise_plan_node(state):
    try:
        current_plan = state.get("research_plan", {})
        feedback = state.get("human_feedback", "")

        prompt = f"""
You are an expert AI Research Planner. Revise the plan based on feedback.
Do not conduct research and do not write a report.

Topic: {state.get('query', '')}
Research type: {state.get('research_type', 'General')}
Research depth: {state.get('research_depth', 'Standard')}

Current plan:
{json.dumps(current_plan, ensure_ascii=False)}

User feedback:
{feedback}

Return ONLY valid JSON:
{{
  "objective": "clear objective",
  "sub_questions": ["question"],
  "search_queries": ["specific search query"],
  "focus_areas": ["focus area"]
}}
"""

        response = get_llm().invoke(prompt)
        plan = safe_json_parse(response.content)

        if (
            not isinstance(plan, dict)
            or plan.get("error")
            or not plan.get("objective")
        ):
            return {
                "error": "Could not generate a valid revised plan."
            }

        for key in (
            "sub_questions",
            "search_queries",
            "focus_areas",
        ):
            if not isinstance(plan.get(key), list):
                plan[key] = []

        # Deliberately do NOT approve: return to human approval.
        return {
            "research_plan": plan,
            "search_queries": plan["search_queries"],
            "plan_approved": False,
            "error": "",
        }

    except Exception as e:
        return {"error": f"Plan revision failed: {e}"}


def route_after_revision(state):
    return "end" if state.get("error") else "human_approval"


def search_agent_node(state):
    try:
        queries = state.get("search_queries") or [state["query"]]

        # Limit tool calls to control latency and token usage.
        queries = [str(q) for q in queries[:3]]

        llm = get_llm().bind_tools([web_search])

        prompt = f"""
You are a web research tool-calling agent.

Topic: {state['query']}
Research type: {state.get('research_type', 'General')}
Research depth: {state.get('research_depth', 'Standard')}

Approved plan:
{json.dumps(state.get('research_plan', {}), ensure_ascii=False)[:1800]}

Search queries:
{json.dumps(queries, ensure_ascii=False)}

Call the web_search tool for up to three of the listed queries.
Do not answer the research question directly; use the tool.
"""

        response = llm.invoke(prompt)
        return {"messages": [response]}

    except Exception as e:
        return {"error": f"Search agent failed: {e}"}


def route_after_search_agent(state):
    if state.get("error"):
        return "end"

    messages = state.get("messages", [])

    if messages and getattr(messages[-1], "tool_calls", []):
        return "search_tools"

    return "analyze"


def analyze_node(state):
    try:
        messages = state.get("messages", [])

        results = []
        sources = list(state.get("sources", []))

        # Extract search results from LangChain tool messages.
        for message in messages:
            if getattr(message, "type", None) != "tool":
                continue

            content = message.content

            try:
                if isinstance(content, str):
                    parsed = json.loads(content)
                elif isinstance(content, dict):
                    parsed = content
                else:
                    continue

                if not isinstance(parsed, dict):
                    continue

                if parsed.get("error"):
                    continue

                # Collect source URLs returned by Tavily.
                raw_sources = parsed.get("sources", [])

                if isinstance(raw_sources, str):
                    raw_sources = [raw_sources]

                if isinstance(raw_sources, list):
                    for url in raw_sources:
                        if (
                            isinstance(url, str)
                            and url.strip().startswith(
                                ("https://", "http://")
                            )
                        ):
                            sources.append(url.strip())

                # Also collect URLs directly from search results.
                items = parsed.get("results", [])

                if not isinstance(items, list):
                    items = []

                compact_results = []

                for item in items:
                    if not isinstance(item, dict):
                        continue

                    url = item.get("url", "")

                    if (
                        isinstance(url, str)
                        and url.strip().startswith(
                            ("https://", "http://")
                        )
                    ):
                        sources.append(url.strip())

                    compact_results.append({
                        "title": str(item.get("title", ""))[:200],
                        "url": str(url)[:500],
                        "content": str(
                            item.get("content", "")
                        )[:900],
                    })

                results.append({
                    "query": parsed.get("query", ""),
                    "results": compact_results,
                    "sources": raw_sources,
                })

            except (json.JSONDecodeError, TypeError, ValueError):
                continue

        # Remove duplicates and invalid URLs.
        sources = list(dict.fromkeys(
            url.strip()
            for url in sources
            if (
                isinstance(url, str)
                and url.strip().startswith(
                    ("https://", "http://")
                )
            )
        ))

        if not results:
            return {
                "error": (
                    "No valid web search tool results found. "
                    "Check the messages returned by the search tool."
                ),
                "sources": sources,
            }

        prompt = ANALYSIS_PROMPT.format(
            query=state["query"],
            research_type=state.get(
                "research_type", "General"
            ),
            research_plan=json.dumps(
                state.get("research_plan", {}),
                ensure_ascii=False,
            )[:1500],
            search_results=json.dumps(
                results,
                ensure_ascii=False,
            )[:6500],
        )

        response = get_llm().invoke(prompt)
        analysis = safe_json_parse(response.content)

        if not isinstance(analysis, dict) or analysis.get("error"):
            return {
                "error": "Research analysis failed: invalid model response.",
                "sources": sources,
            }

        return {
            "analysis": analysis,
            "insights": analysis.get("insights", []),
            "sources": sources,
            "error": "",
        }

    except Exception as e:
        return {
            "error": f"Analysis failed: {e}"
        }

def evaluation_node(state):
    iteration = state.get("research_iterations", 0)

    try:
        prompt = EVALUATION_PROMPT.format(
            query=state["query"],
            research_type=state.get(
                "research_type", "General"
            ),
            research_plan=json.dumps(
                state.get("research_plan", {}),
                ensure_ascii=False,
            )[:1200],
            analysis=json.dumps(
                state.get("analysis", {}),
                ensure_ascii=False,
            )[:2500],
            sources="\n".join(
                state.get("sources", [])[:12]
            ),
            iteration=iteration,
        )

        evaluation = safe_json_parse(
            get_llm().invoke(prompt).content
        )

        if (
            not isinstance(evaluation, dict)
            or evaluation.get("error")
        ):
            return {
                "enough_information": True,
                "evaluation_reason": (
                    "Evaluation response was invalid; "
                    "using available research."
                ),
                "research_iterations": iteration + 1,
            }

        enough = bool(
            evaluation.get("enough_information", False)
        )

        # Initial pass plus at most two additional research rounds.
        if iteration >= 2:
            enough = True

        return {
            "enough_information": enough,
            "evaluation_reason": evaluation.get("reason", ""),
            "research_iterations": iteration + 1,
        }

    except Exception as e:
        return {
            "enough_information": True,
            "evaluation_reason": (
                "Evaluation failed; continuing with available "
                f"research: {e}"
            ),
            "research_iterations": iteration + 1,
        }


def prepare_next_search_node(state):
    unanswered = state.get(
        "analysis", {}
    ).get("unanswered_questions", [])

    if not unanswered:
        unanswered = [state["query"]]

    return {
        "search_queries": [
            str(q) for q in unanswered[:3]
        ]
    }


def summary_node(state):
    try:
        raw_sources = state.get("sources", [])

        if isinstance(raw_sources, str):
            raw_sources = [raw_sources]
        elif not isinstance(raw_sources, list):
            raw_sources = []

        # Keep only valid web URLs and remove duplicates.
        sources = list(dict.fromkeys(
            url.strip()
            for url in raw_sources
            if (
                isinstance(url, str)
                and url.strip().startswith(
                    ("https://", "http://")
                )
            )
        ))

        prompt = SUMMARY_PROMPT.format(
            query=state["query"],
            insights=json.dumps(
                state.get(
                    "analysis", {}
                ).get("insights", []),
                ensure_ascii=False,
            )[:3000],
            sources="\n".join(sources[:20]),
        )

        report = safe_json_parse(
            get_llm().invoke(prompt).content
        )

        if not isinstance(report, dict) or report.get("error"):
            return {
                "error": (
                    "Final report generation failed: "
                    "invalid model response."
                )
            }

        # Attach the collected URLs to the final report.
        report["citations"] = sources

        return {
            "final_report": report,
            "sources": sources,
            "error": "",
        }

    except Exception as e:
        return {"error": f"Summary generation failed: {e}"}


def statistics_node(state):
    elapsed = round(
        time.time() - state.get("start_time", time.time()),
        2,
    )

    return {
        "statistics": {
            "research_type": state.get(
                "research_type", "-"
            ),
            "research_depth": state.get(
                "research_depth", "-"
            ),
            "sources_used": len(
                state.get("sources", [])
            ),
            "research_iterations": state.get(
                "research_iterations", 0
            ),
            "time_taken": elapsed,
            "llm_model": "openai/gpt-oss-20b",
        }
    }


def route_after_evaluation(state):
    if state.get("error"):
        return "end"

    return (
        "summary"
        if state.get("enough_information", False)
        else "search_again"
    )