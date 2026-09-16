"""Tests for the assistant's graceful-degradation behaviour.

The assistant has three operating states and must stay useful in all of them:

  1. no API key        -> curated retrieval answers only
  2. key, model works  -> grounded generation
  3. key, model fails  -> curated answer is returned anyway, with a flag explaining why

State 3 is the one that is easy to get wrong, so it carries the most tests here. None of
these tests touch the network.
"""

from __future__ import annotations

import pytest
from cmblab_chat import llm, topics
from cmblab_chat.assistant import answer
from cmblab_chat.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── the question bank ───────────────────────────────────────────────────────────────────


def test_every_curated_question_is_answerable_without_a_key():
    """The whole point of the browsable topics is that they need no API key."""
    for topic in topics.TOPICS:
        for question in topic.questions:
            result = answer(question)
            assert result.text.strip(), f"{question!r} produced an empty answer"
            assert not result.needs_llm, f"{question!r} would have fallen through to the LLM"


def test_curated_questions_still_work_before_the_pipeline_has_run(monkeypatch):
    """A fresh deployment has no results yet, and must still answer sensibly.

    Measurement answers normally splice in live pipeline values. On a brand new instance
    those are all None, and an earlier version fell through to "I'm not certain what you
    are asking" — which is wrong, because the question was understood perfectly. CI caught
    this because CI has no data directory.
    """
    import cmblab_chat.assistant as assistant

    def no_results(keys):
        return {k: {"label": k.replace("_", " "), "value": None, "display": ""} for k in keys}

    monkeypatch.setattr(assistant, "resolve", no_results)

    for topic in topics.TOPICS:
        for question in topic.questions:
            result = answer(question)
            assert result.text.strip(), f"{question!r} produced an empty answer with no data"
            assert not result.needs_llm, f"{question!r} fell through to the LLM with no data"


def test_missing_measurement_says_what_to_run(monkeypatch):
    import cmblab_chat.assistant as assistant

    monkeypatch.setattr(
        assistant,
        "resolve",
        lambda keys: {k: {"label": "First acoustic peak", "value": None} for k in keys},
    )

    result = answer("what is the first acoustic peak?")
    assert result.intent == "not_measured"
    assert not result.needs_llm
    # It must point somewhere actionable rather than just apologising.
    assert "Spectrum" in result.text
    assert "make spectrum" in result.text


def test_topics_are_well_formed():
    ids = [t.id for t in topics.TOPICS]
    assert len(ids) == len(set(ids)), "topic ids must be unique"
    assert topics.question_count() == sum(len(t.questions) for t in topics.TOPICS)
    for topic in topics.TOPICS:
        assert topic.label and topic.blurb and topic.icon
        assert topic.questions


def test_topics_endpoint(client: TestClient):
    body = client.get("/topics").json()
    assert body["n_questions"] == topics.question_count()
    assert len(body["topics"]) == len(topics.TOPICS)


# ── stage reporting and setup guidance ──────────────────────────────────────────────────


def test_capabilities_reports_stage_1_and_tells_you_how_to_upgrade(client, monkeypatch):
    monkeypatch.setattr(llm, "llm_available", lambda: False)
    monkeypatch.setattr("cmblab_chat.main.llm_available", lambda: False)

    body = client.get("/capabilities").json()
    assert body["stage"] == 1
    assert body["llm"]["available"] is False
    # The UI renders these verbatim, so they must be present.
    setup = body["llm"]["setup"]
    assert setup["env_var"] == "GEMINI_API_KEY"
    assert setup["file"] == ".env"
    assert setup["get_key_url"].startswith("https://")
    assert setup["restart_command"]
    # Stage 1 must still advertise a full question bank.
    assert body["retrieval"]["n_questions"] > 0
    assert body["topics"]


# ── state 3: the model is configured but fails ──────────────────────────────────────────


def _force_llm(monkeypatch, *, side_effect):
    monkeypatch.setattr("cmblab_chat.main.llm_available", lambda: True)
    monkeypatch.setattr("cmblab_chat.main.ask_gemini", side_effect)


@pytest.mark.parametrize(
    "exc",
    [
        llm.LLMUnavailable("Gemini rate limit reached."),
        llm.LLMUnavailable("Gemini is overloaded right now."),
        llm.LLMUnavailable("Gemini's answer was cut off before it finished"),
        RuntimeError("something entirely unexpected"),
    ],
)
def test_llm_failure_still_returns_a_useful_answer(client, monkeypatch, exc):
    def boom(*args, **kwargs):
        raise exc

    _force_llm(monkeypatch, side_effect=boom)

    body = client.post(
        "/chat", json={"message": "What is the sound horizon?", "mode": "always"}
    ).json()

    assert body["stage"] == 1, "a failed upgrade must fall back, not error out"
    assert body["llm_fallback"] is True
    assert body["llm_error"]
    # The substantive requirement: the user still got a real answer.
    assert "sound horizon" in body["text"].lower()
    assert body["citations"]


def test_llm_success_is_marked_as_stage_2(client, monkeypatch):
    def ok(*args, **kwargs):
        return llm.LLMResult(
            text="A grounded explanation.",
            model="gemini-flash-latest",
            provider="gemini",
            grounded_on=["glossary:sound_horizon"],
        )

    _force_llm(monkeypatch, side_effect=ok)

    body = client.post(
        "/chat", json={"message": "Explain the damping tail", "mode": "always"}
    ).json()
    assert body["stage"] == 2
    assert body["text"] == "A grounded explanation."
    assert "llm_fallback" not in body


def test_missing_key_raises_unavailable_rather_than_crashing(monkeypatch):
    monkeypatch.setattr(llm, "gemini_api_key", lambda: "")
    with pytest.raises(llm.LLMUnavailable, match="GEMINI_API_KEY"):
        llm.ask_gemini("anything")


# ── model selection ─────────────────────────────────────────────────────────────────────


def test_default_model_is_an_unversioned_alias():
    """Pinned versions get retired by Google; aliases do not."""
    assert "latest" in llm.DEFAULT_MODEL


def test_fallback_models_exclude_the_failed_one(monkeypatch):
    monkeypatch.setattr(
        llm, "_cached_ranked_models", lambda: ("gemini-flash-latest", "gemini-2.5-flash")
    )
    assert "gemini-flash-latest" not in llm._fallback_models(exclude="gemini-flash-latest")
