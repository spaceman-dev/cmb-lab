import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { ChatCapabilities, ChatReply, ChatTopic } from "../api/types";
import { RichText } from "../components/Math";

interface Turn {
  role: "user" | "assistant";
  text: string;
  reply?: ChatReply;
}

/**
 * Physics assistant.
 *
 * Works in three states, and degrades between them without ever leaving the user stuck:
 *
 *  1. No API key      — curated answers plus a browsable question bank. Fully useful.
 *  2. Key configured  — open-ended questions go to the model, grounded in retrieval.
 *  3. Key but failing — the stage-1 answer is shown anyway, with a quiet notice.
 */
export function ChatDock() {
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [caps, setCaps] = useState<ChatCapabilities | null>(null);
  const [openTopic, setOpenTopic] = useState<string | null>(null);
  const [showSetup, setShowSetup] = useState(false);
  const [browsing, setBrowsing] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.chatCapabilities().then(setCaps).catch(() => setCaps(null));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns, busy]);

  const send = async (message: string) => {
    const text = message.trim();
    if (!text || busy) return;

    setBrowsing(false);
    setTurns((prev) => [...prev, { role: "user", text }]);
    setDraft("");
    setBusy(true);

    try {
      const reply = await api.chat(text, sessionId);
      setSessionId(reply.session_id);
      setTurns((prev) => [...prev, { role: "assistant", text: reply.text, reply }]);
    } catch {
      setTurns((prev) => [
        ...prev,
        {
          role: "assistant",
          text:
            "I could not reach the chat service. Check it is running with " +
            "`./scripts/dev.sh status`.",
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const lastReply = turns.length ? turns[turns.length - 1].reply : undefined;
  const suggestions = lastReply?.suggestions ?? caps?.suggestions ?? [];
  const setup = caps?.llm.setup;
  const stage = caps?.stage ?? 1;

  const renderTopics = (topics: ChatTopic[]) => (
    <div className="topics">
      {topics.map((topic) => (
        <div key={topic.id} className="topic">
          <button
            className={`topic__head ${openTopic === topic.id ? "topic__head--open" : ""}`}
            onClick={() => setOpenTopic(openTopic === topic.id ? null : topic.id)}
          >
            <span className="topic__icon">{topic.icon}</span>
            <span className="topic__body">
              <span className="topic__label">{topic.label}</span>
              <span className="topic__blurb">{topic.blurb}</span>
            </span>
            <span className="topic__chevron">{openTopic === topic.id ? "▾" : "▸"}</span>
          </button>

          {openTopic === topic.id && (
            <ul className="topic__questions">
              {topic.questions.map((question) => (
                <li key={question}>
                  <button className="topic__question" onClick={() => void send(question)}>
                    {question}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );

  return (
    <>
      <button
        className={`chat-fab ${open ? "chat-fab--open" : ""}`}
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close assistant" : "Open physics assistant"}
      >
        {open ? "✕" : "✦"}
      </button>

      <aside className={`chat-dock ${open ? "chat-dock--open" : ""}`}>
        <header className="chat-dock__head">
          <div>
            <h3>Physics assistant</h3>
            <span className="chat-dock__stage">
              {stage === 2 ? (
                <>
                  <span className="ok">AI mode</span> · {caps?.llm.model ?? "gemini"}
                </>
              ) : (
                <>
                  {caps?.retrieval.n_questions ?? 0} curated answers · no API key needed
                </>
              )}
            </span>
          </div>
          <div className="chat-dock__actions">
            {turns.length > 0 && (
              <button
                className="chat-dock__icon"
                title="Browse questions"
                onClick={() => setBrowsing((v) => !v)}
              >
                ☰
              </button>
            )}
            <button className="chat-dock__icon" onClick={() => setOpen(false)}>
              ✕
            </button>
          </div>
        </header>

        {/* Stage-1 notice: small, dismissible, and tells you exactly where to put the key. */}
        {stage === 1 && setup && (
          <div className="llm-hint">
            <button className="llm-hint__toggle" onClick={() => setShowSetup((v) => !v)}>
              <span className="llm-hint__dot" />
              Answering from a curated knowledge base. Enable AI mode
              <span className="llm-hint__chevron">{showSetup ? "▾" : "▸"}</span>
            </button>

            {showSetup && (
              <div className="llm-hint__body">
                <ol>
                  <li>
                    Get a free key at{" "}
                    <a href={setup.get_key_url} target="_blank" rel="noreferrer">
                      aistudio.google.com/apikey
                    </a>
                  </li>
                  <li>
                    Add it to <code>{setup.file}</code>:
                    <pre>{setup.env_var}=your_key_here</pre>
                  </li>
                  <li>
                    Restart: <code>{setup.restart_command}</code>
                  </li>
                </ol>
                <p className="hint">
                  Everything below keeps working without it — the key only adds open-ended
                  questions.
                </p>
              </div>
            )}
          </div>
        )}

        <div className="chat-dock__body" ref={scrollRef}>
          {turns.length === 0 && (
            <div className="chat-intro">
              <p>
                Ask about the physics, any derivation, or what this pipeline actually
                measured. I only quote numbers that came out of the analysis.
              </p>
            </div>
          )}

          {(browsing || turns.length === 0) && caps?.topics && renderTopics(caps.topics)}

          {turns.map((turn, i) => (
            <div key={i} className={`bubble bubble--${turn.role}`}>
              {turn.role === "assistant" ? (
                <RichText text={turn.text} className="bubble__body" />
              ) : (
                <div className="bubble__body">{turn.text}</div>
              )}

              {turn.reply?.citations && turn.reply.citations.length > 0 && (
                <div className="bubble__cites">
                  {turn.reply.citations.map((c, j) => (
                    <span key={j} className={`cite cite--${c.kind}`}>
                      {c.label}
                    </span>
                  ))}
                </div>
              )}

              {/* Stage 2 was attempted and failed: say so, but the answer above still stands. */}
              {turn.reply?.llm_fallback && (
                <div className="bubble__fallback">
                  AI mode unavailable right now — answered from the curated knowledge base
                  instead.
                  {turn.reply.llm_error && (
                    <span className="bubble__fallback-detail">{turn.reply.llm_error}</span>
                  )}
                </div>
              )}

              {turn.reply?.stage === 2 && (
                <div className="bubble__badge">AI · grounded in pipeline data</div>
              )}
            </div>
          ))}

          {busy && (
            <div className="bubble bubble--assistant">
              <div className="bubble__body typing">
                <span />
                <span />
                <span />
              </div>
            </div>
          )}
        </div>

        {suggestions.length > 0 && !busy && turns.length > 0 && (
          <div className="chat-dock__suggestions">
            {suggestions.slice(0, 3).map((s) => (
              <button key={s} className="chip" onClick={() => void send(s)}>
                {s}
              </button>
            ))}
          </div>
        )}

        <form
          className="chat-dock__input"
          onSubmit={(e) => {
            e.preventDefault();
            void send(draft);
          }}
        >
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={stage === 2 ? "Ask anything about the CMB…" : "Ask about the CMB…"}
            disabled={busy}
          />
          <button type="submit" className="primary" disabled={busy || !draft.trim()}>
            Send
          </button>
        </form>
      </aside>
    </>
  );
}
