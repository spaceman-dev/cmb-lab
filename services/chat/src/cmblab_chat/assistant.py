"""Stage-1 assistant: intent matching and knowledge retrieval, no LLM required.

A retrieval assistant with good source material answers physics questions more reliably
than a generative one with none — and it never invents a number. Every answer here is
either a curated explanation or a value read from the live pipeline, with its provenance
attached.

Stage 2 keeps all of this and passes it to a language model as grounding context, so the
model paraphrases facts rather than inventing them.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from cmblab_tutor.content import CURRICULUM_ORDER, LESSONS
from cmblab_tutor.glossary import GLOSSARY, search_glossary
from cmblab_tutor.live import RESOLVERS, resolve


@dataclass(slots=True)
class Citation:
    kind: str  # glossary | lesson | measurement
    label: str
    ref: str = ""
    detail: str = ""


@dataclass(slots=True)
class Answer:
    text: str
    intent: str
    confidence: float
    citations: list[Citation] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    needs_llm: bool = False

    def public(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "intent": self.intent,
            "confidence": round(self.confidence, 3),
            "citations": [asdict(c) for c in self.citations],
            "suggestions": self.suggestions,
            "data": self.data,
        }


#: Questions whose answer is a live number from the pipeline.
MEASUREMENT_PATTERNS: list[tuple[str, str]] = [
    (r"first (acoustic )?peak|peak position|where.*peak|220", "first_peak_ell"),
    (r"peak (height|amplitude)|how (high|big).*peak", "first_peak_dl"),
    (r"chi.?squared|chi2|goodness of fit|how well.*agree|agreement", "chi2_per_dof"),
    (r"f.?sky|sky fraction|how much sky|mask.*fraction", "f_sky"),
    (r"how many bandpowers|bandpower count|number of bins", "n_bandpowers"),
    (r"\brms\b|fluctuation amplitude|how big.*fluctuation|70 ?(micro)?k", "map_rms"),
    (r"resolution|nside|how many pixels", "map_nside"),
    (r"beam|jupiter", "beam_labels"),
    (r"hubble tension|h0 tension|67.*73|disagree.*hubble", "tension_H0"),
    (r"hubble constant|\bh0\b|expansion rate", "posterior_H0"),
    (r"baryon density|omega.?b|ombh2", "posterior_ombh2"),
    (r"theory.*peak|camb.*predict|predicted peak", "theory_peak_ell"),
]

HOW_TO: dict[str, tuple[str, str]] = {
    "spectrum": (
        "Run a power spectrum",
        "Open the **Spectrum** tab and press Recompute. It cross-correlates two WMAP "
        "detectors (V1 × V2 by default), deconvolves the measured beams, subtracts "
        "unresolved point sources, and checks gates G3 and G4. On the command line: "
        "`make spectrum`.",
    ),
    "inference": (
        "Fit cosmological parameters",
        "Open the **Inference** tab and start an MCMC run. It samples H₀, Ω_b h² and "
        "Ω_c h² against our measured bandpowers using CAMB, then compares the posterior "
        "to Planck 2018. On the command line: `cmblab-cosmology fit`.",
    ),
    "anomaly": (
        "Test the large-angle anomalies",
        "Open the **Anomalies** tab and launch an analysis. It measures the four classic "
        "statistics, builds a Monte Carlo null distribution from isotropic ΛCDM skies, and "
        "reports both raw and look-elsewhere corrected p-values.",
    ),
    "download": (
        "Get the data",
        "Run `make data-bootstrap`. It pulls about 170 MB from NASA LAMBDA and the ESA "
        "Planck Legacy Archive — no API key needed — then cleans and validates it.",
    ),
    "map": (
        "Explore the sky maps",
        "Open the **Sky Map** tab. You can switch projection (Mollweide, globe, gnomonic "
        "zoom, 3D sphere) and filter by multipole band. Try the quadrupole and octupole "
        "presets side by side to see the alignment anomaly directly.",
    ),
    "playground": (
        "Experiment with the data",
        "Open the **Playground** tab. Change the mask, the multipole range, the binning, "
        "or the cosmological parameters, and watch the spectrum and χ² respond live.",
    ),
}

GREETING = re.compile(r"^\s*(hi|hello|hey|yo|greetings|good (morning|afternoon|evening))\b", re.I)
THANKS = re.compile(r"\b(thanks|thank you|cheers|appreciate)\b", re.I)

DEFAULT_SUGGESTIONS = [
    "Why is the first peak at ℓ = 220?",
    "What is a cross-spectrum and why did we use one?",
    "Explain cosmic variance",
    "What did our pipeline measure?",
    "What is the look-elsewhere effect?",
]


#: What produces each live measurement, so a question asked before the pipeline has run gets
#: a useful answer instead of a shrug. Keyed by resolver name.
PRODUCED_BY: dict[str, tuple[str, str]] = {
    "first_peak_ell": ("Spectrum", "make spectrum"),
    "first_peak_dl": ("Spectrum", "make spectrum"),
    "chi2_per_dof": ("Spectrum", "make spectrum"),
    "f_sky": ("Spectrum", "make spectrum"),
    "n_bandpowers": ("Spectrum", "make spectrum"),
    "map_rms": ("Sky Map", "make data-bootstrap"),
    "map_nside": ("Sky Map", "make data-bootstrap"),
    "beam_labels": ("Spectrum", "make data-bootstrap"),
    "theory_peak_ell": ("Playground", "cmblab-cosmology theory"),
    "posterior_H0": ("Inference", "cmblab-cosmology fit"),
    "posterior_ombh2": ("Inference", "cmblab-cosmology fit"),
    "tension_H0": ("Inference", "cmblab-cosmology fit"),
    "anomaly_summary": ("Anomalies", "cmblab-anomaly run"),
    "alignment_angle": ("Anomalies", "cmblab-anomaly run"),
    "alignment_p": ("Anomalies", "cmblab-anomaly run"),
}


def _not_measured_yet(key: str, label: str) -> Answer:
    """A complete answer for a quantity this instance has not computed yet.

    Falling through to the generic "I'm not sure what you mean" would be wrong here: we
    understood the question perfectly, we simply have no number for it. Say so, and say
    what to run.
    """
    tab, command = PRODUCED_BY.get(key, ("Spectrum", "make spectrum"))
    return Answer(
        text=(
            f"**{label}** has not been measured on this instance yet.\n\n"
            f"It comes out of the **{tab}** tab — open it and start a run, or from the "
            f"command line:\n\n```\n{command}\n```\n\n"
            "I only quote numbers this pipeline actually produced, so I would rather tell "
            "you it is missing than recite a textbook value as if we had measured it."
        ),
        intent="not_measured",
        confidence=0.75,
        suggestions=[
            f"What is {label.lower()}?",
            "How do I run a power spectrum?",
            "What did our pipeline measure?",
        ],
    )


def _measurement_answer(key: str) -> Answer | None:
    values = resolve([key])
    payload = values.get(key)
    if not payload:
        return None
    if payload.get("value") is None:
        return _not_measured_yet(key, payload.get("label", key.replace("_", " ")))

    lines = [f"**{payload['label']}**", "", f"## {payload['display']}"]
    if payload.get("context"):
        lines += ["", payload["context"]]
    if payload.get("source"):
        lines += ["", f"_Source: {payload['source']}_"]

    return Answer(
        text="\n".join(lines),
        intent="measurement",
        confidence=0.9,
        citations=[
            Citation(kind="measurement", label=payload["label"], detail=payload.get("source", ""))
        ],
        data={key: payload},
        suggestions=[
            "How was that computed?",
            "Show me the derivation",
            "Is that consistent with Planck?",
        ],
    )


#: "What did we actually find?" — the headline results, assembled from live values.
SUMMARY = re.compile(
    r"what did (our|the|we|this)?\s*(pipeline|project|analysis|you|we)?\s*(measure|find|get|show)"
    r"|summar(y|ise|ize)|headline|overall result|what are the results|key findings",
    re.I,
)


def _summary_answer() -> Answer:
    """Headline results. Every number comes from the live pipeline, never hard-coded."""
    keys = ["first_peak_ell", "first_peak_dl", "chi2_per_dof", "f_sky", "posterior_H0"]
    values = resolve(keys)

    rows = [
        f"| {v['label']} | **{v['display']}** |"
        for k in keys
        if (v := values.get(k)) and v.get("value") is not None
    ]

    if not rows:
        # Nothing has been computed yet. Explain the project rather than showing a
        # table of blanks.
        return Answer(
            text=(
                "**This pipeline has not been run on this instance yet.**\n\n"
                "When it runs it measures the cosmic microwave background power spectrum "
                "from raw NASA WMAP data: it cross-correlates two independent detectors so "
                "their noise cancels, deconvolves the measured beams, masks the Galaxy, and "
                "subtracts unresolved point sources. Out of that come the position of the "
                "first acoustic peak, the cosmological parameters, and calibrated "
                "significances for the four large-angle anomalies.\n\n"
                "Start it from the **Spectrum** tab, or run:\n\n```\nmake data-bootstrap\n"
                "make spectrum\n```"
            ),
            intent="not_measured",
            confidence=0.8,
            suggestions=[
                "Why is the first peak at ℓ = 220?",
                "What is a cross-spectrum and why did we use one?",
                "How do I run a power spectrum?",
            ],
        )

    lines = [
        "**What this pipeline measured, from raw NASA archive data**",
        "",
        "We cross-correlated two independent WMAP detectors so their noise cancels, "
        "deconvolved the measured beams, masked the Galaxy, and subtracted unresolved "
        "point sources. What came out:",
        "",
    ]
    if rows:
        lines += ["| Quantity | Value |", "| --- | --- |", *rows, ""]
    lines += [
        "The first peak position is the headline: it is the angular size of the sound "
        "horizon at recombination, and it is what tells us the universe is spatially flat.",
        "",
        "Every number above is recomputed from the archive files — nothing is copied from "
        "a published table. The published values are only used afterwards, as a check.",
    ]

    return Answer(
        text="\n".join(lines),
        intent="summary",
        confidence=0.9,
        citations=[Citation(kind="measurement", label="Pipeline results", detail="live")],
        data={k: v for k, v in values.items() if v.get("value") is not None},
        suggestions=[
            "Why is the first peak at ℓ = 220?",
            "What is a cross-spectrum and why did we use one?",
            "How well does our result agree with published data?",
        ],
    )


def _glossary_answer(question: str) -> Answer | None:
    hits = search_glossary(question, limit=3)
    if not hits:
        return None

    top = hits[0]
    # Weak matches are better handled as an explanation than a definition.
    if top["score"] < 4:
        return None

    lines = [f"**{top['term']}**", "", top["long"]]
    if top.get("latex"):
        lines += ["", f"$${top['latex']}$$"]

    citations = [Citation(kind="glossary", label=top["term"], ref=top["key"])]
    if top.get("lesson"):
        lesson = LESSONS.get(top["lesson"])
        if lesson:
            lines += [
                "",
                f"This is derived in full in the lesson **{lesson.title}**.",
            ]
            citations.append(
                Citation(
                    kind="lesson",
                    label=lesson.title,
                    ref=f"{top['lesson']}#{top['section']}",
                )
            )

    related = [h["term"] for h in hits[1:]]
    return Answer(
        text="\n".join(lines),
        intent="definition",
        confidence=min(0.55 + 0.1 * top["score"], 0.95),
        citations=citations,
        suggestions=[f"What is {t}?" for t in related] or DEFAULT_SUGGESTIONS[:2],
    )


def _lesson_answer(question: str) -> Answer | None:
    """Match a question against lesson and section titles."""
    tokens = {t for t in re.findall(r"[a-z]+", question.lower()) if len(t) > 3}
    if not tokens:
        return None

    best_score = 0
    best: tuple[str, str, str, str] | None = None

    for lesson_id in CURRICULUM_ORDER:
        lesson = LESSONS[lesson_id]
        for section in lesson.sections:
            haystack = f"{lesson.title} {lesson.subtitle} {section.title}".lower()
            score = sum(2 for t in tokens if t in haystack)
            score += sum(1 for t in tokens if t in section.narrative.lower()[:900])
            if score > best_score:
                best_score = score
                best = (lesson_id, lesson.title, section.id, section.title)

    if not best or best_score < 4:
        return None

    lesson_id, lesson_title, section_id, section_title = best
    section = next(s for s in LESSONS[lesson_id].sections if s.id == section_id)

    # Lead with the first substantive paragraph rather than the whole wall of text.
    paragraphs = [p.strip() for p in section.narrative.strip().split("\n\n") if p.strip()]
    excerpt = "\n\n".join(paragraphs[:2])

    lines = [f"**{section_title}** — from the lesson _{lesson_title}_", "", excerpt]
    if section.equations:
        equation = section.equations[0]
        lines += ["", f"$${equation.latex}$$", "", f"_{equation.explain}_"]

    return Answer(
        text="\n".join(lines),
        intent="explanation",
        confidence=min(0.5 + 0.05 * best_score, 0.9),
        citations=[
            Citation(
                kind="lesson",
                label=f"{lesson_title} → {section_title}",
                ref=f"{lesson_id}#{section_id}",
            )
        ],
        suggestions=[
            "Show me the full derivation",
            "Play the audio explanation",
            "What did our data measure?",
        ],
        data={"lesson": lesson_id, "section": section_id, "has_audio": True},
    )


def _howto_answer(question: str) -> Answer | None:
    lowered = question.lower()
    if not re.search(r"\bhow (do|can|would) i\b|\bhow to\b|where do i|show me how", lowered):
        return None

    for key, (title, body) in HOW_TO.items():
        if key in lowered or any(word in lowered for word in key.split("_")):
            return Answer(
                text=f"**{title}**\n\n{body}",
                intent="howto",
                confidence=0.85,
                suggestions=list(DEFAULT_SUGGESTIONS[:3]),
            )

    options = "\n".join(f"- **{t}** — {b.split('.')[0]}." for t, b in HOW_TO.values())
    return Answer(
        text=f"Here is what you can do in cmb-lab:\n\n{options}",
        intent="howto",
        confidence=0.6,
        suggestions=list(DEFAULT_SUGGESTIONS[:3]),
    )


def answer(question: str) -> Answer:
    """Route a question to the best stage-1 responder."""
    text = question.strip()

    if not text:
        return Answer(
            text="Ask me anything about the CMB, the physics, or what this pipeline measured.",
            intent="empty",
            confidence=1.0,
            suggestions=DEFAULT_SUGGESTIONS,
        )

    if GREETING.match(text) and len(text) < 40:
        return Answer(
            text=(
                "Hello. I can explain the physics behind this project, walk through any "
                "derivation, or tell you what our pipeline actually measured from the NASA "
                "data. What would you like to know?"
            ),
            intent="greeting",
            confidence=1.0,
            suggestions=DEFAULT_SUGGESTIONS,
        )

    if THANKS.search(text) and len(text) < 40:
        return Answer(
            text="Any time. Ask away if something else comes up.",
            intent="thanks",
            confidence=1.0,
            suggestions=DEFAULT_SUGGESTIONS[:3],
        )

    lowered = text.lower()

    # "What did we find?" asks for the whole result set, not one number, so it is checked
    # before the single-measurement patterns that would otherwise match a fragment of it.
    if SUMMARY.search(lowered):
        return _summary_answer()

    # Live measurements first: a concrete number beats a definition when both could match.
    for pattern, key in MEASUREMENT_PATTERNS:
        if re.search(pattern, lowered) and key in RESOLVERS and (found := _measurement_answer(key)):
            return found

    for responder in (_howto_answer, _glossary_answer, _lesson_answer):
        if found := responder(text):
            return found

    hits = search_glossary(text, limit=4)
    if hits:
        options = "\n".join(f"- **{h['term']}** — {h['short']}" for h in hits)
        return Answer(
            text=(
                "I am not certain what you are asking, but these look related:\n\n"
                f"{options}\n\nTry rephrasing, or ask about one of them directly."
            ),
            intent="fallback_related",
            confidence=0.35,
            citations=[Citation(kind="glossary", label=h["term"], ref=h["key"]) for h in hits],
            suggestions=[f"What is {h['term']}?" for h in hits[:3]],
            needs_llm=True,
        )

    terms = ", ".join(sorted({t.term for t in list(GLOSSARY.values())[:8]}))
    return Answer(
        text=(
            "I do not have a curated answer for that yet. I can explain: "
            f"{terms}, and more. I can also report any number our pipeline measured.\n\n"
            "_Enable the AI assistant (stage 2) with a Gemini API key for open-ended "
            "questions._"
        ),
        intent="fallback",
        confidence=0.2,
        suggestions=DEFAULT_SUGGESTIONS,
        needs_llm=True,
    )
