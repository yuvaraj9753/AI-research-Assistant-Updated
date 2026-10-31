import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq


load_dotenv()

_llm = None


def get_llm():
    """
    Return a singleton Groq LLM instance.
    """

    global _llm

    if _llm is None:

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY not found in .env file."
            )

        _llm = ChatGroq(
            model="openai/gpt-oss-20b",
            api_key=api_key,
            temperature=0.3
        )

    return _llm