from langchain_core.messages import HumanMessage
from app.agents.graph import _build_llm

TITLE_PROMPT = (
    "Summarize the topic of this message in 3-5 words for a chat title. "
    "No quotes, no punctuation at the end, no explanation, just the title.\n\n"
    "Message: {message}"
)


def _fallback_title(message: str) -> str:
    """
    Used if every key fails (e.g. all of them rate-limited). Still gives a
    real, useful title instead of a generic placeholder -- just the first
    handful of words from what the user actually typed.
    """
    words = message.strip().split()
    short = " ".join(words[:6])
    if not short:
        return "New Chat"
    return short[:57] + "..." if len(short) > 57 else short


def generate_title(first_message: str) -> str:
    fallback = _fallback_title(first_message)
    try:
        prompt = TITLE_PROMPT.format(message=first_message[:300])
        response =  _build_llm().invoke([HumanMessage(content=prompt)])
        title = response.content.strip().strip('"').strip("'")
        return title[:60] if title else fallback
    except Exception as e:
        print(f"[title_agent] LLM title generation failed on all keys, using fallback title. Error: {e}")
        return fallback
