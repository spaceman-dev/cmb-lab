"""HTTP API for the chat assistant.

Two stages, one endpoint. Stage 1 (retrieval) always runs and always answers. Stage 2 (a
grounded language model) is used when a key is configured and either the caller asks for it
or stage 1 was not confident. If stage 2 fails for any reason, the stage-1 answer is
returned instead — the assistant never goes dark.
"""

from __future__ import annotations

import uuid
from typing import Any

from cmblab_core.service import create_app
from pydantic import BaseModel, Field

from .assistant import DEFAULT_SUGGESTIONS, answer
from .llm import LLMUnavailable, ask_gemini, gemini_model, llm_available
from .topics import all_topics, question_count

app = create_app(
    service_name="chat",
    description="Physics assistant: retrieval-grounded, optionally LLM-backed.",
)

#: Conversation history, kept in memory. Bounded so a long session cannot grow without end.
_SESSIONS: dict[str, list[dict[str, str]]] = {}
MAX_TURNS = 40


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None
    #: "auto" uses the LLM only when retrieval is unsure; "always" forces it; "never" is stage 1.
    mode: str = Field(default="auto", pattern="^(auto|always|never)$")


@app.get("/capabilities", tags=["meta"])
async def capabilities() -> dict[str, Any]:
    enabled = llm_available()
    return {
        "stage": 2 if enabled else 1,
        "llm": {
            "available": enabled,
            "provider": "gemini" if enabled else None,
            "model": gemini_model() if enabled else None,
            "note": (
                "Grounded generation enabled."
                if enabled
                else "Running on curated answers. Add a key for open-ended questions."
            ),
            # Everything the UI needs to tell the user how to switch stage 2 on.
            "setup": {
                "env_var": "GEMINI_API_KEY",
                "file": ".env",
                "get_key_url": "https://aistudio.google.com/apikey",
                "restart_command": "./scripts/dev.sh restart",
            },
        },
        "retrieval": {
            "available": True,
            "sources": ["glossary", "lessons", "live pipeline measurements"],
            "n_questions": question_count(),
        },
        "topics": all_topics(),
        "suggestions": DEFAULT_SUGGESTIONS,
    }


@app.get("/topics", tags=["meta"])
async def topics() -> dict[str, Any]:
    """Curated question bank. Every entry works without an API key."""
    return {"topics": all_topics(), "n_questions": question_count()}


@app.post("/chat", tags=["chat"])
async def chat(request: ChatRequest) -> dict[str, Any]:
    session_id = request.session_id or uuid.uuid4().hex[:12]
    history = _SESSIONS.setdefault(session_id, [])

    grounded = answer(request.message)

    use_llm = llm_available() and (
        request.mode == "always" or (request.mode == "auto" and grounded.needs_llm)
    )

    reply = grounded.public()
    reply["stage"] = 1
    reply["session_id"] = session_id
    reply["llm_configured"] = llm_available()

    if use_llm:
        try:
            result = ask_gemini(request.message, history=history)
            reply["text"] = result.text
            reply["stage"] = 2
            reply["intent"] = "llm"
            reply["confidence"] = 0.8
            reply["model"] = result.model
            reply["grounded_on"] = result.grounded_on
            # Keep whatever retrieval found so the UI can still show citations.
            reply["retrieval"] = grounded.public()
        except LLMUnavailable as exc:
            # Stage 2 failing must never cost the user an answer: the stage-1 reply is
            # already in `reply`, so we only annotate why the upgrade did not happen.
            reply["llm_error"] = str(exc)
            reply["llm_fallback"] = True
        except Exception as exc:  # noqa: BLE001 - an unexpected provider error is still a fallback
            reply["llm_error"] = f"Unexpected error from the model provider: {exc}"
            reply["llm_fallback"] = True

    history.append({"role": "user", "content": request.message})
    history.append({"role": "assistant", "content": reply["text"]})
    del history[:-MAX_TURNS]

    return reply


@app.get("/sessions/{session_id}", tags=["chat"])
async def session(session_id: str) -> dict[str, Any]:
    if session_id not in _SESSIONS:
        raise KeyError(f"No session {session_id}")
    return {"session_id": session_id, "turns": _SESSIONS[session_id]}


@app.post("/sessions/{session_id}/reset", tags=["chat"])
async def reset(session_id: str) -> dict[str, Any]:
    _SESSIONS.pop(session_id, None)
    return {"session_id": session_id, "reset": True}
