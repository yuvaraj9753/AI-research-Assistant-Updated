import time
import uuid
import streamlit as st
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agents.chat import follow_up_chat
from graph.research_graph import research_graph
from utils.pdf_export import create_research_pdf


st.set_page_config(page_title="AI Research Assistant", page_icon="🔬", layout="wide")
st.title("🔬 AI Research Assistant")
st.caption(
    "Agentic AI research assistant with LangGraph, web search, human approval, "
    "source citations, iterative research, PDF export and follow-up Q&A."
)
st.markdown("Research Planning → Human Approval → Web Search → Analysis → Evaluation → Report")


DEFAULTS = {
    "query": "",
    "research_type": "General",
    "research_depth": "Standard",
    "research_plan": None,
    "research": None,
    "final": None,
    "statistics": None,
    "thread_id": None,
    "waiting_for_approval": False,
    "research_running": False,
    "graph_error": None,
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def current_config():
    return {"configurable": {"thread_id": st.session_state.thread_id}}


def pending_plan(snapshot):
    """Return the interrupt payload only when a graph task is actually interrupted."""
    for task in getattr(snapshot, "tasks", ()):
        for item in getattr(task, "interrupts", ()):
            value = getattr(item, "value", None)
            if isinstance(value, dict) and value.get("type") == "research_plan_approval":
                return value.get("plan", {})
    return None


def sync_graph_state():
    if not st.session_state.thread_id:
        return
    snapshot = research_graph.get_state(current_config())
    plan = pending_plan(snapshot)
    if plan is not None:
        st.session_state.research_plan = plan
        st.session_state.waiting_for_approval = True
        st.session_state.research_running = False
        return

    values = snapshot.values or {}
    if values.get("error"):
        st.session_state.graph_error = values["error"]
        st.session_state.research_running = False
        st.session_state.waiting_for_approval = False
        return

    if values.get("final_report"):
        st.session_state.final = values["final_report"]
        st.session_state.statistics = values.get("statistics", {})
        analysis = values.get("analysis", {})
        st.session_state.research = {
            "summary": analysis.get("summary", ""),
            "insights": analysis.get("insights", values.get("insights", [])),
            "citations": values.get("sources", []),
        }
        st.session_state.research_running = False
        st.session_state.waiting_for_approval = False


# Sidebar settings
st.sidebar.header("⚙️ Research Settings")
research_type = st.sidebar.selectbox(
    "Research Type", ["General", "Technical", "Academic", "Market"],
    index=["General", "Technical", "Academic", "Market"].index(st.session_state.research_type),
)
research_depth = st.sidebar.radio(
    "Research Depth", ["Quick", "Standard", "Deep"],
    index=["Quick", "Standard", "Deep"].index(st.session_state.research_depth),
)

query = st.text_input("🔎 Enter your research topic", value=st.session_state.query)

if st.button("🚀 Start Research", type="primary"):
    if not query.strip():
        st.warning("Please enter a research topic.")
        st.stop()

    st.session_state.query = query.strip()
    st.session_state.research_type = research_type
    st.session_state.research_depth = research_depth
    st.session_state.research = None
    st.session_state.final = None
    st.session_state.statistics = None
    st.session_state.research_plan = None
    st.session_state.graph_error = None
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.waiting_for_approval = False
    st.session_state.research_running = True

    initial_state = {
        "query": st.session_state.query,
        "research_type": research_type,
        "research_depth": research_depth,
        "research_iterations": 0,
        "start_time": time.time(),
        "messages": [HumanMessage(content=st.session_state.query)],
    }
    try:
        with st.spinner("🧠 Creating research plan..."):
            research_graph.invoke(initial_state, config=current_config())
        sync_graph_state()
        st.rerun()
    except Exception as e:
        st.session_state.research_running = False
        st.session_state.graph_error = str(e)
        st.rerun()


# Human approval UI
if st.session_state.waiting_for_approval:
    st.divider()
    st.header("👤 Human-in-the-Loop: Review Research Plan")
    plan = st.session_state.research_plan or {}

    st.subheader("🎯 Research Objective")
    st.write(plan.get("objective", "No objective generated."))

    st.subheader("❓ Sub Questions")
    questions = plan.get("sub_questions", [])
    if questions:
        for i, item in enumerate(questions, 1):
            st.write(f"{i}. {item}")
    else:
        st.write("No sub-questions provided.")

    st.subheader("🔎 Search Queries")
    for i, item in enumerate(plan.get("search_queries", []), 1):
        st.write(f"{i}. {item}")

    st.subheader("🎯 Focus Areas")
    for item in plan.get("focus_areas", []):
        st.write(f"• {item}")

    feedback = st.text_area(
        "✏️ Optional feedback / modification",
        key=f"plan_feedback_{st.session_state.thread_id}_{hash(str(plan))}",
        placeholder="Example: Add more focus on limitations and real-world applications.",
    )
    approve_col, modify_col = st.columns(2)

    with approve_col:
        if st.button("✅ Approve & Continue", type="primary", key="approve_plan"):
            try:
                st.session_state.waiting_for_approval = False
                st.session_state.research_running = True
                with st.spinner("🔍 Researching and preparing report..."):
                    research_graph.invoke(
                        Command(resume={"approved": True, "feedback": feedback}),
                        config=current_config(),
                    )
                sync_graph_state()
                st.rerun()
            except Exception as e:
                st.session_state.research_running = False
                st.session_state.graph_error = str(e)
                st.rerun()

    with modify_col:
        if st.button("✏️ Modify & Review Again", key="modify_plan"):
            if not feedback.strip():
                st.warning("Please provide feedback describing what should change.")
            else:
                try:
                    # Resume as NOT approved. Graph revises plan, then interrupts again.
                    st.session_state.waiting_for_approval = False
                    with st.spinner("🔄 Revising plan for your review..."):
                        research_graph.invoke(
                            Command(resume={"approved": False, "feedback": feedback}),
                            config=current_config(),
                        )
                    sync_graph_state()
                    st.rerun()
                except Exception as e:
                    st.session_state.graph_error = str(e)
                    st.session_state.waiting_for_approval = False
                    st.rerun()


if st.session_state.graph_error:
    st.error(f"Research workflow error: {st.session_state.graph_error}")

# Refresh completed state after a rerun if research is still marked running.
if st.session_state.research_running and not st.session_state.waiting_for_approval:
    sync_graph_state()

# Sidebar statistics
if st.session_state.statistics:
    stats = st.session_state.statistics
    st.sidebar.divider()
    st.sidebar.header("📊 Research Statistics")
    st.sidebar.metric("Sources Used", stats.get("sources_used", 0))
    st.sidebar.metric("Research Type", stats.get("research_type", "-"))
    st.sidebar.metric("Research Depth", stats.get("research_depth", "-"))
    st.sidebar.metric("Iterations", stats.get("research_iterations", 0))
    st.sidebar.metric("Time Taken", f"{stats.get('time_taken', 0)} sec")
    st.sidebar.metric("LLM", stats.get("llm_model", "-"))

# Report
if st.session_state.final is not None and st.session_state.research is not None:
    research = st.session_state.research
    final = st.session_state.final
    st.divider()
    st.header("📄 Research Report")

    with st.expander("📊 Insights", expanded=True):
        for item in research.get("insights", []):
            st.write(f"✔️ {item}")

    with st.expander("🧾 Research Summary"):
        st.write(research.get("summary", ""))

    with st.expander("📖 Introduction"):
        st.write(final.get("introduction", ""))

    with st.expander("🔑 Key Points"):
        for item in final.get("key_points", []):
            st.write(f"👉 {item}")

    with st.expander("✅ Conclusion"):
        st.write(final.get("conclusion", ""))

    with st.expander("🧭 Related Topics"):
        topics = final.get("related_topics", [])
        if topics:
            for item in topics:
                st.write(f"🔹 {item}")
        else:
            st.write("No related topics found.")

    with st.expander("🔗 Sources"):
        citations = final.get("citations", [])

        if not citations:
            citations = research.get("sources", [])

    # Handle a single URL as well as a list of URLs.
        if isinstance(citations, str):
            citations = [citations]

        if citations:
            for i, link in enumerate(citations, start=1):
                if isinstance(link, str) and link.startswith(
                ("https://", "http://")
            ):
                    st.markdown(f"{i}. [{link}]({link})")
        else:
            st.info("No sources were returned by the web search.")
        

    pdf_file = create_research_pdf(
        query=st.session_state.query,
        research=research,
        final=final,
    )
    st.download_button(
        label="📥 Download Research PDF",
        data=pdf_file,
        file_name="research_report.pdf",
        mime="application/pdf",
    )

st.divider()
st.subheader("💬 Follow-up Chat")
question = st.text_input("Ask a follow-up question", key="follow_up_question")

if st.button("Ask", key="ask_follow_up"):
    if st.session_state.final is None:
        st.warning("⚠️ Please perform research first.")
        st.stop()
    if not question.strip():
        st.warning("⚠️ Please enter a question.")
        st.stop()
    with st.spinner("🤔 Thinking..."):
        response = follow_up_chat(
            st.session_state.query,
            st.session_state.research,
            st.session_state.final,
            question,
        )
    if "error" in response:
        st.error(response.get("details", response["error"]))
    else:
        st.success("Answer")
        st.write(response["answer"])