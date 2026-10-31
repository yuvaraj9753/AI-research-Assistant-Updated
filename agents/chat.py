from services.groq_service import get_llm
from prompts.chat_prompt import CHAT_PROMPT


def follow_up_chat(
    query: str,
    research: dict,
    final: dict,
    question: str
):
    """
    Answer follow-up questions using the completed research report.
    """

    llm = get_llm()

    prompt = CHAT_PROMPT.format(
        query=query,
        summary=research.get("summary", ""),
        introduction=final.get("introduction", ""),
        key_points="\n".join(final.get("key_points", [])),
        conclusion=final.get("conclusion", ""),
        sources="\n".join(final.get("citations", [])),
        question=question
    )

    try:
        response = llm.invoke(prompt)

        return {
            "answer": response.content
        }

    except Exception as e:

        return {
            "error": "Follow-up chat failed",
            "details": str(e)
        }