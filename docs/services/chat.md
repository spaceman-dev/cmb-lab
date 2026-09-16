# chat

**Path:** `services/chat/` · **Port:** 8009

A physics assistant that answers questions about the CMB and about this project's own
results. It is useful with no API key, better with one, and never breaks when the key stops
working.

## Three operating states

| State | Condition | Behaviour |
| --- | --- | --- |
| **1 — Curated** | No API key | Retrieval only: glossary, lessons, live measurements, and a browsable bank of 29 questions |
| **2 — Grounded AI** | Key configured and working | Open-ended questions go to Gemini, with retrieval results injected as authoritative context |
| **3 — Fallback** | Key configured but the call failed | The stage-1 answer is returned anyway, flagged with `llm_fallback` so the UI can say why |

State 3 is the one that is easy to get wrong and it carries the most tests. A model being
retired, rate-limited, overloaded, or truncated must never cost the user an answer.

## The grounding rule

**The model is never the source of a number.** Retrieval runs first and produces facts —
glossary entries, lesson excerpts, live pipeline measurements — and those are handed to the
model with an explicit instruction not to invent anything outside them. The system prompt
says: *if the CONTEXT contradicts your training, the CONTEXT wins — it is measured from real
data.*

## Modules

### `assistant.py` — stage 1

Routes a question to the best retrieval responder, in priority order:

1. Greeting / thanks / empty
2. `SUMMARY` — "what did we measure?" returns the full headline results table
3. `MEASUREMENT_PATTERNS` — a concrete live number beats a definition when both match
4. `_glossary_answer` — term definitions
5. `_lesson_answer` — relevant lesson excerpts
6. `HOW_TO` — how to drive the site
7. Fallback, with `needs_llm = True`

`Answer.needs_llm` is what decides whether stage 2 is worth attempting in `auto` mode.

### `topics.py` — the question bank

Six topics, 29 questions, all answerable without a key. A test asserts that every single one
resolves through stage 1 with `needs_llm == False`, so the browsable UI can never offer a
question it cannot answer.

| Topic | Questions |
| --- | --- |
| Start here | 4 |
| The physics | 7 |
| How we measured it | 6 |
| Cosmological parameters | 4 |
| The anomalies | 3 |
| Using this site | 5 |

### `llm.py` — stage 2

`build_context()` assembles glossary hits, live measurements, and a fixed block of pipeline
facts, then `ask_gemini()` sends it.

Resilience built in after hitting each of these for real:

- **Retired models.** Google retires pinned versions, so the default is the unversioned
  alias `gemini-flash-latest`. If a pinned name 404s, `_discover_model()` queries
  `ListModels` and picks a live replacement.
- **Overload.** A 503 triggers failover across up to three alternative models.
- **Thinking tokens.** Gemini 3.x spends reasoning tokens from the same budget as output. A
  1200-token cap left nothing for the answer and truncated it mid-sentence; the budget is
  now 4096 with `thinkingLevel: low`. Older models that reject `thinkingConfig` get a
  retry without it.
- **Truncation.** A response that hits `MAX_TOKENS` with under 400 characters is treated as
  a failure, because half a sentence is worse than a curated answer.
- **Thought parts.** Parts flagged `thought` are filtered out so internal reasoning never
  reaches the user.

## Configuration

```bash
# .env
GEMINI_API_KEY=your_key_here          # from https://aistudio.google.com/apikey
GEMINI_MODEL=gemini-flash-latest      # optional
```

Then `./scripts/dev.sh restart` — `get_settings()` is cached, so a key added after start-up
needs a restart. `/capabilities` returns this setup information so the UI can render exact
instructions instead of a generic error.

The key is optional. Without it the service is fully functional in state 1.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/capabilities` | Current stage, model, setup instructions, topics, question count |
| GET | `/topics` | The browsable question bank |
| POST | `/chat` | Ask a question. `mode` is `auto` (default), `always`, or `never` |
| GET | `/sessions/{session_id}` | Conversation history |
| POST | `/sessions/{session_id}/reset` | Clear history |

## Running

```bash
make dev-chat
.venv/bin/python -m pytest services/chat/tests -q     # 12 tests, no network
```
