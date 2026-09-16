import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Curriculum, Lesson } from "../api/types";
import { AudioPlayer } from "../components/AudioPlayer";
import { Math, RichText } from "../components/Math";

/**
 * How much detail to show. The default is deliberately the gentlest one: a reader meeting
 * this material for the first time should not be handed six lessons of dense derivation
 * before they know what the subject is about.
 */
type Depth = "plain" | "physics" | "full";

const DEPTHS: { id: Depth; label: string; hint: string }[] = [
  { id: "plain", label: "Plain English", hint: "No symbols. The ideas only." },
  { id: "physics", label: "With equations", hint: "Every symbol explained, plus intuition." },
  { id: "full", label: "Full derivations", hint: "Step-by-step algebra as well." },
];

export function LearnView() {
  const [curriculum, setCurriculum] = useState<Curriculum | null>(null);
  const [lessonId, setLessonId] = useState("origin");
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [loading, setLoading] = useState(false);
  const [openDerivations, setOpenDerivations] = useState<Record<string, boolean>>({});
  const [depth, setDepth] = useState<Depth>(
    () => (localStorage.getItem("cmblab.depth") as Depth) || "plain",
  );
  const [openVars, setOpenVars] = useState<Record<string, boolean>>({});

  const chooseDepth = (next: Depth) => {
    setDepth(next);
    localStorage.setItem("cmblab.depth", next);
  };

  useEffect(() => {
    api.curriculum().then(setCurriculum).catch(() => setCurriculum(null));
  }, []);

  useEffect(() => {
    setLoading(true);
    api
      .lesson(lessonId)
      .then((data) => {
        setLesson(data);
        window.scrollTo({ top: 0, behavior: "smooth" });
      })
      .catch(() => setLesson(null))
      .finally(() => setLoading(false));
  }, [lessonId]);

  return (
    <div className="view">
      <header className="view__head">
        <div>
          <h2>Learn the physics</h2>
          <p className="muted">
            Every derivation this project relies on, built from scratch. Each section has an
            audio explainer and splices in the numbers your own pipeline measured.
          </p>
        </div>
        {curriculum && (
          <div className="pill">
            {curriculum.lessons.length} lessons · {curriculum.total_minutes} min
          </div>
        )}
      </header>

      <div className="panel depth-bar">
        <div className="depth-bar__intro">
          <strong>Reading depth</strong>
          <span className="muted">Start plain. Go deeper whenever you want.</span>
        </div>
        <div className="depth-bar__options">
          {DEPTHS.map((option) => (
            <button
              key={option.id}
              className={`depth-opt ${depth === option.id ? "depth-opt--on" : ""}`}
              onClick={() => chooseDepth(option.id)}
              title={option.hint}
            >
              <span className="depth-opt__label">{option.label}</span>
              <span className="depth-opt__hint">{option.hint}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="learn-layout">
        <aside className="panel learn-nav">
          <h3>Curriculum</h3>
          <ol className="lesson-list">
            {curriculum?.lessons.map((item, index) => (
              <li key={item.id}>
                <button
                  className={`lesson-item ${lessonId === item.id ? "lesson-item--active" : ""}`}
                  onClick={() => setLessonId(item.id)}
                >
                  <span className="lesson-item__n">{index + 1}</span>
                  <span className="lesson-item__body">
                    <span className="lesson-item__title">{item.title}</span>
                    <span className="lesson-item__sub">
                      {item.n_sections} sections · {item.duration_min} min
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ol>

          {lesson && (
            <>
              <h3>In this lesson</h3>
              <ul className="section-list">
                {lesson.sections.map((s) => (
                  <li key={s.id}>
                    <a href={`#${s.id}`}>{s.title}</a>
                  </li>
                ))}
              </ul>
            </>
          )}
        </aside>

        <main className="learn-main">
          {loading && <div className="panel placeholder">loading lesson…</div>}

          {lesson && !loading && (
            <>
              <div className="panel lesson-header">
                <span className="lesson-header__position">
                  Lesson {lesson.navigation.position} of {lesson.navigation.total}
                </span>
                <h1>{lesson.title}</h1>
                <p className="lesson-header__sub">{lesson.subtitle}</p>
                {lesson.prerequisites.length > 0 && (
                  <p className="hint">
                    Builds on:{" "}
                    {lesson.prerequisites.map((p) => (
                      <button key={p} className="link" onClick={() => setLessonId(p)}>
                        {p}
                      </button>
                    ))}
                  </p>
                )}
              </div>

              {lesson.sections.map((section) => (
                <article key={section.id} id={section.id} className="panel lesson-section">
                  <h2>{section.title}</h2>

                  <AudioPlayer
                    src={api.audioUrl(lesson.id, section.id)}
                    fallbackText={section.narration}
                    estimatedSeconds={section.audio.estimated_seconds}
                    available={section.audio.available}
                    label="Listen to this section"
                  />

                  {section.plain && (
                    <div className="plain-box">
                      <div className="plain-box__tag">In plain English</div>
                      <p>{section.plain}</p>
                    </div>
                  )}

                  {depth !== "plain" && (
                    <RichText text={section.narrative} className="prose" />
                  )}

                  {Object.keys(section.live_values).length > 0 && (
                    <div className="live-grid">
                      {Object.entries(section.live_values).map(([key, value]) => (
                        <div key={key} className="live-card">
                          <div className="live-card__label">{value.label}</div>
                          <div className="live-card__value">{value.display}</div>
                          {value.context && (
                            <div className="live-card__context">{value.context}</div>
                          )}
                          {value.source && (
                            <div className="live-card__source">{value.source}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {depth !== "plain" && section.equations.length > 0 && (
                    <div className="equations">
                      {section.equations.map((equation, i) => {
                        const key = `${section.id}-${i}`;
                        const open = openVars[key];
                        return (
                          <figure key={i} className="equation">
                            {equation.label && (
                              <figcaption className="equation__label">
                                {equation.label}
                              </figcaption>
                            )}
                            <Math tex={equation.latex} display />

                            {equation.intuition && (
                              <div className="equation__intuition">
                                <span className="equation__intuition-tag">Why it looks
                                  like this</span>
                                <p>{equation.intuition}</p>
                              </div>
                            )}

                            {equation.variables.length > 0 && (
                              <>
                                <button
                                  className="equation__vars-toggle"
                                  onClick={() =>
                                    setOpenVars((prev) => ({ ...prev, [key]: !prev[key] }))
                                  }
                                >
                                  {open ? "▾" : "▸"} What each symbol means (
                                  {equation.variables.length})
                                </button>

                                {open && (
                                  <dl className="varlist">
                                    {equation.variables.map((v, j) => (
                                      <div key={j} className="varlist__row">
                                        <dt>
                                          <Math tex={v.symbol} />
                                        </dt>
                                        <dd>
                                          {v.meaning}
                                          {v.units && (
                                            <span className="varlist__units">[{v.units}]</span>
                                          )}
                                        </dd>
                                      </div>
                                    ))}
                                  </dl>
                                )}
                              </>
                            )}

                            {equation.explain && (
                              <p className="equation__explain">{equation.explain}</p>
                            )}
                          </figure>
                        );
                      })}
                    </div>
                  )}

                  {depth === "full" && section.derivation.length > 0 && (
                    <div className="derivation">
                      <button
                        className="derivation__toggle"
                        onClick={() =>
                          setOpenDerivations((prev) => ({
                            ...prev,
                            [section.id]: !prev[section.id],
                          }))
                        }
                      >
                        {openDerivations[section.id] ? "▾" : "▸"} Step-by-step derivation (
                        {section.derivation.length} steps)
                      </button>

                      {openDerivations[section.id] && (
                        <ol className="steps">
                          {section.derivation.map((step) => (
                            <li key={step.n} className="step">
                              <div className="step__n">{step.n}</div>
                              <div className="step__body">
                                <Math tex={step.latex} display />
                                <p className="step__reason">{step.reason}</p>
                              </div>
                            </li>
                          ))}
                        </ol>
                      )}
                    </div>
                  )}
                </article>
              ))}

              <nav className="panel lesson-nav">
                <button
                  className="ghost"
                  disabled={!lesson.navigation.previous}
                  onClick={() =>
                    lesson.navigation.previous && setLessonId(lesson.navigation.previous)
                  }
                >
                  ← Previous
                </button>
                <button
                  className="primary"
                  disabled={!lesson.navigation.next}
                  onClick={() => lesson.navigation.next && setLessonId(lesson.navigation.next)}
                >
                  Next lesson →
                </button>
              </nav>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
