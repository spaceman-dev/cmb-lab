"""Tests for the tutor content, audio pipeline, and chat assistant."""

from __future__ import annotations

import pytest
from cmblab_chat.assistant import answer
from cmblab_tutor.audio import estimate_duration_s, speakable
from cmblab_tutor.content import CURRICULUM_ORDER, LESSONS, get_lesson, get_section
from cmblab_tutor.glossary import GLOSSARY, search_glossary

# ─────────────────────────────────────────────────────── curriculum


def test_every_lesson_in_the_order_exists():
    for lesson_id in CURRICULUM_ORDER:
        assert lesson_id in LESSONS


def test_prerequisites_come_earlier_in_the_curriculum():
    """A lesson must never depend on one the student has not reached yet."""
    for index, lesson_id in enumerate(CURRICULUM_ORDER):
        lesson = LESSONS[lesson_id]
        for prerequisite in lesson.prerequisites:
            assert prerequisite in CURRICULUM_ORDER, prerequisite
            assert CURRICULUM_ORDER.index(prerequisite) < index, (
                f"{lesson_id} requires {prerequisite}, which comes later"
            )


def test_every_section_has_narrative_and_narration():
    """The narration drives the audio explainer, so it can never be missing."""
    for lesson in LESSONS.values():
        for section in lesson.sections:
            assert len(section.narrative.strip()) > 200, f"{lesson.id}/{section.id}"
            assert len(section.narration.strip()) > 200, f"{lesson.id}/{section.id}"


def test_narration_contains_no_latex():
    """Narration is read aloud; raw LaTeX would be spelled out character by character."""
    for lesson in LESSONS.values():
        for section in lesson.sections:
            assert "$" not in section.narration, f"{lesson.id}/{section.id}"
            assert "\\frac" not in section.narration, f"{lesson.id}/{section.id}"


def test_every_equation_has_an_explanation():
    for lesson in LESSONS.values():
        for section in lesson.sections:
            for equation in section.equations:
                assert equation.latex.strip()
                assert equation.explain.strip(), f"{lesson.id}/{section.id}"


def test_derivation_steps_are_numbered_consecutively():
    for lesson in LESSONS.values():
        for section in lesson.sections:
            if not section.derivation:
                continue
            numbers = [step.n for step in section.derivation]
            assert numbers == list(range(1, len(numbers) + 1)), f"{lesson.id}/{section.id}"
            for step in section.derivation:
                assert step.reason.strip(), "every step must say why it follows"


def test_live_keys_all_resolve_to_a_resolver():
    from cmblab_tutor.live import RESOLVERS

    for lesson in LESSONS.values():
        for section in lesson.sections:
            for key in section.live:
                assert key in RESOLVERS, f"{lesson.id}/{section.id} wants unknown key {key}"


def test_unknown_lesson_raises():
    with pytest.raises(KeyError, match="Unknown lesson"):
        get_lesson("not-a-lesson")


def test_unknown_section_raises():
    with pytest.raises(KeyError, match="Unknown section"):
        get_section("origin", "not-a-section")


# ─────────────────────────────────────────────────────── audio


def test_speakable_strips_display_math():
    assert "$" not in speakable(r"Text $$\frac{a}{b}$$ more text")


def test_speakable_expands_symbols():
    spoken = speakable("The value of ℓ and µK")
    assert "ell" in spoken
    assert "microkelvin" in spoken


def test_speakable_removes_markdown():
    spoken = speakable("**bold** and `code` and _italics_")
    assert "*" not in spoken
    assert "`" not in spoken


def test_duration_estimate_scales_with_length():
    short = estimate_duration_s("one two three")
    long = estimate_duration_s(" ".join(["word"] * 300))
    assert long > short
    assert long == pytest.approx(300 * 60 / 165, rel=0.05)


# ─────────────────────────────────────────────────────── glossary


def test_glossary_entries_are_complete():
    for key, term in GLOSSARY.items():
        assert term.key == key
        assert term.short.strip()
        assert len(term.long.strip()) > 60


def test_glossary_search_finds_aliases():
    hits = search_glossary("what is c_l")
    assert any(h["key"] == "power_spectrum" for h in hits)


def test_glossary_search_handles_nonsense():
    assert search_glossary("zzzz") == []


# ─────────────────────────────────────────────────────── assistant


def test_greeting_is_recognised():
    assert answer("hello").intent == "greeting"


def test_definition_question_hits_the_glossary():
    result = answer("what is cosmic variance?")
    assert result.intent == "definition"
    assert "2ℓ+1" in result.text or "2l+1" in result.text.replace("ℓ", "l")


def test_howto_question_is_routed():
    result = answer("how do I run an MCMC inference?")
    assert result.intent == "howto"


def test_unknown_question_asks_for_the_llm():
    result = answer("what is the airspeed velocity of an unladen swallow")
    assert result.needs_llm


def test_empty_question_is_handled():
    assert answer("   ").intent == "empty"


def test_answers_always_carry_suggestions():
    for question in ("hello", "what is a multipole?", "how do I download data?"):
        assert answer(question).suggestions


@pytest.mark.slow
def test_measurement_question_returns_a_live_number():
    """Requires the pipeline data; skipped implicitly if the resolver cannot run."""
    result = answer("what is the first acoustic peak?")
    assert result.intent in {"measurement", "explanation", "definition"}


# ── the plain-English layer ─────────────────────────────────────────────────────────────
#
# The curriculum is correct but dense, and a first-time reader was getting overwhelmed.
# Three affordances fix that, and these tests keep them from rotting: a jargon-free summary
# on every section, a gloss for every symbol, and an intuition paragraph per equation.


def _all_lessons():
    import cmblab_tutor.content as content

    return [v for k, v in vars(content).items() if k.startswith("LESSON_")]


def _all_equations():
    return [eq for lesson in _all_lessons() for s in lesson.sections for eq in s.equations]


def test_every_section_has_a_plain_english_summary():
    for lesson in _all_lessons():
        for section in lesson.sections:
            assert section.plain.strip(), f"{lesson.id}/{section.id} has no plain summary"
            # A summary that needs LaTeX to be understood is not a plain summary.
            assert "$" not in section.plain, f"{lesson.id}/{section.id} plain text has math"
            assert "\\" not in section.plain, f"{lesson.id}/{section.id} plain text has LaTeX"


def test_every_equation_explains_its_symbols_and_its_shape():
    for equation in _all_equations():
        assert equation.variables, f"{equation.label!r} has no variable glosses"
        assert equation.intuition.strip(), f"{equation.label!r} has no intuition"
        for var in equation.variables:
            assert var.symbol.strip(), f"{equation.label!r} has a nameless symbol"
            assert len(var.meaning) > 15, f"{equation.label!r}/{var.symbol} gloss is too thin"


def test_intuition_avoids_undefined_jargon():
    """The intuition paragraph is the on-ramp, so it must not need the lesson to parse."""
    for equation in _all_equations():
        assert "$" not in equation.intuition, f"{equation.label!r} intuition contains math"


def test_plain_summary_is_short_enough_to_actually_read():
    for lesson in _all_lessons():
        for section in lesson.sections:
            words = len(section.plain.split())
            assert 25 <= words <= 140, f"{lesson.id}/{section.id} plain summary is {words} words"


def test_lesson_payload_exposes_the_new_fields():
    """The browser renders these, so they must survive serialisation."""
    payload = _all_lessons()[0].public()
    section = payload["sections"][0]
    assert "plain" in section
    assert "variables" in section["equations"][0]
    assert "intuition" in section["equations"][0]


# ── glossary ranking ────────────────────────────────────────────────────────────────────
#
# Substring matching used to rank "Cosmic variance" first for "cosmic microwave
# background", and "CMB Cold Spot" for "what is cmb" — the term merely contained the
# query as a substring. Both are answers to a different question than the one asked, which
# is worse than no answer in a teaching tool.


def test_every_term_finds_itself_first():
    from cmblab_tutor.glossary import GLOSSARY, search_glossary

    for entry in GLOSSARY.values():
        hits = search_glossary(entry.term, limit=1)
        assert hits, f"{entry.term!r} returned nothing"
        assert hits[0]["key"] == entry.key, (
            f"{entry.term!r} ranked {hits[0]['term']!r} above itself"
        )


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("what is cmb?", "cmb"),
        ("What is the CMB?", "cmb"),
        ("what is this cosmic microwave background radiation about?", "cmb"),
        ("cosmic microwave background", "cmb"),
        ("what is recombination", "recombination"),
        ("when did the universe become transparent", "recombination"),
        ("what is the cold spot", "cold_spot"),
        ("explain cosmic variance", "cosmic_variance"),
        ("what is a cross-spectrum", "cross_spectrum"),
        ("what is a multipole", "multipole"),
        ("axis of evil", "axis_of_evil"),
        ("what is the look-elsewhere effect", "look_elsewhere"),
        ("what is lambda cdm", "lcdm"),
        ("what is the sound horizon", "sound_horizon"),
        ("what is the hubble tension", "hubble_tension"),
    ],
)
def test_glossary_returns_the_term_actually_asked_about(query, expected):
    from cmblab_tutor.glossary import search_glossary

    hits = search_glossary(query, limit=1)
    assert hits, f"{query!r} returned nothing"
    assert hits[0]["key"] == expected, f"{query!r} returned {hits[0]['term']!r}"


def test_cmb_outranks_terms_that_merely_contain_the_word():
    """The regression that started this: 'cmb' must not land on 'CMB Cold Spot'."""
    from cmblab_tutor.glossary import search_glossary

    hits = search_glossary("what is the cmb", limit=3)
    assert hits[0]["key"] == "cmb"
    assert hits[0]["score"] > 3 * hits[1]["score"], "margin over the runner-up is too thin"
