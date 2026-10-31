from services.groq_service import get_llm
from prompts.summary_prompt import SUMMARY_PROMPT
from utils.helpers import safe_json_parse


def summarize(query: str, research: dict):
    llm = get_llm()
    prompt = SUMMARY_PROMPT.format(
        query=query,
        insights=research.get("insights", []),
        sources="\n".join(research.get("citations", [])),
    )
    try:
        data = safe_json_parse(llm.invoke(prompt).content)
        if "error" in data:
            return data
        data["citations"] = research.get("citations", [])
        data.setdefault("related_topics", [])
        return data
    except Exception as e:
        return {"error": "Summarization failed", "details": str(e)}