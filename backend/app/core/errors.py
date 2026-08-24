def is_quota_error(e: Exception) -> bool:
    message = str(e).lower()
    return "resource_exhausted" in message or "429" in message or "quota" in message


def classify_ai_error(e: Exception) -> tuple[int, str]:
    """
    Turns a raw exception from Gemini (or any AI call) into an HTTP status
    code and a message that's actually useful to show a user, instead of
    a stack trace or a generic "something went wrong."

    The full raw error should still be printed to the server terminal by
    the caller -- this is only for what the PERSON sees.
    """
    message = str(e).lower()

    if is_quota_error(e):
        return 429, (
            "The AI service has hit its usage limit for now (this is common on "
            "free-tier API keys). Please wait a minute and try again."
        )

    if "api key" in message or "permission" in message or "401" in message or "403" in message:
        return 401, "There's a problem with the AI service's API key or permissions. Please check the server configuration."

    if "not_found" in message or "404" in message:
        return 502, "The AI model being used isn't available right now. Please try again shortly."

    if "timeout" in message or "timed out" in message:
        return 504, "The AI service took too long to respond. Please try again."

    return 500, "Something went wrong on the server while processing your request. Please try again."
