"""Thin wrapper around the google-genai SDK for the single classify+extract call."""

import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from task_manager_agent.models import ClassificationExtraction

load_dotenv()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

if not GOOGLE_API_KEY:
    raise RuntimeError(
        "GOOGLE_API_KEY is not set. Copy .env.example to .env and fill it in."
    )

# Milliseconds, per the google-genai SDK's HttpOptions contract.
REQUEST_TIMEOUT_MS = 30_000

_SYSTEM_INSTRUCTION = """\
You will receive a single message from a Hebrew WhatsApp group chat.

Decide whether the message describes or assigns a task or action item
(something someone needs to do), as opposed to small talk, a question,
a status update, or other non-actionable chatter.

If it IS a task, also extract:
- title: a short imperative Hebrew phrase describing the task.
- due_date: the due date/time exactly as mentioned in the text (verbatim), or null if none is mentioned.
- assignee: the name of the person mentioned in the text as responsible for the task (verbatim), or null if no specific person is named.
- priority: one of "low", "medium", "high", "urgent" ONLY if the text itself signals urgency (e.g. explicit words like "דחוף", "קריטי", or explicit low-urgency phrases like "אין לחץ"). Otherwise null.

If it is NOT a task, set is_task to false and leave all other fields null.
"""


def classify_and_extract(raw_text: str) -> ClassificationExtraction:
    """Call Gemini once to classify `raw_text` as a task and extract its fields.

    Raises ValueError/RuntimeError on any failure (missing/unparseable
    response). Callers are responsible for catching and marking the message
    as needing review.
    """
    try:
        client = genai.Client(
            api_key=GOOGLE_API_KEY,
            http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
        )
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=raw_text,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=ClassificationExtraction,
            ),
        )
        parsed = response.parsed
    except Exception as e:
        raise RuntimeError(f"Gemini classify_and_extract call failed: {e}") from e

    if parsed is None:
        raise ValueError(
            "Gemini response could not be parsed into ClassificationExtraction"
        )
    if not isinstance(parsed, ClassificationExtraction):
        raise ValueError(
            f"Gemini response.parsed was an unexpected type: {type(parsed)!r}"
        )

    return parsed
