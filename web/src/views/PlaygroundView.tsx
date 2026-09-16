import { useEffect, useMemo, useState } from "react";
import type { PlotData } from "plotly.js-dist-min";
import { api } from "../api/client";
import type { ExperimentRun, ExperimentSummary, Knob, PlaygroundTheory } from "../api/types";
import { Plot } from "../components/Plot";

const DIFFICULTY_ORDER = ["essential", "intermediate", "advanced"];

export function PlaygroundView() {
  const [experiments, setExperiments] = useState<ExperimentSummary[]>([]);
  const [knobs, setKnobs] = useState<{ spectrum: Knob[]; theory: Knob[] } | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [run, setRun] = useState<ExperimentRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(false);

  const [params, setParams] = useState<Record<string, number>>({
    H0: 67.36,
    ombh2: 0.02237,
    omch2: 0.12,
    ns: 0.9649,
    tau: 0.0544,
  });
  const [liveTheory, setLiveTheory] = useState<PlaygroundTheory | null>(null);
  const [baseTheory, setBaseTheory] = useState<PlaygroundTheory | null>(null);

  useEffect(() => {
    api.experiments().then((d) => setExperiments(d.experiments)).catch(() => setExperiments([]));
    api.knobs().then(setKnobs).catch(() => setKnobs(null));
    api
      .sandboxTheory({ H0: 67.36, ombh2: 0.02237, omch2: 0.12, ns: 0.9649, tau: 0.0544 })
      .then(setBaseTheory)
      .catch(() => setBaseTheory(null));
  }, []);

  // Debounced: each change is a CAMB call, fast but not free.
  useEffect(() => {
    const timer = setTimeout(() => {
      api.sandboxTheory(params).then(setLiveTheory).catch(() => setLiveTheory(null));
    }, 250);
    return () => clearTimeout(timer);
  }, [params]);

  const execute = async (id: string) => {
    setSelected(id);
    setRevealed(false);
    setRun(null);
    setError(null);
    setBusy(true);
    try {
      setRun(await api.runExperiment(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not run the experiment");
    } finally {
      setBusy(false);
    }
  };

  const comparisonTraces = useMemo<PlotData[]>(() => {
    if (!run) return [];

    if (run.kind === "theory") {
      return [
        {
          x: run.baseline.ell,
          y: run.baseline.dl_tt,
          type: "scatter",
          mode: "lines",
          name: "baseline",
          line: { color: "#94a3b8", width: 2 },
        },
        {
          x: run.variant.ell,
          y: run.variant.dl_tt,
          type: "scatter",
          mode: "lines",
          name: "variant",
          line: { color: "#f59e0b", width: 2.5 },
        },
      ];
    }

    const asPoints = (
      rows: { ell: number; dl: number; err: number | null }[],
      colour: string,
      name: string,
      symbol: string,
    ): PlotData => ({
      x: rows.map((b) => b.ell),
      y: rows.map((b) => b.dl),
      error_y: {
        type: "data",
        array: rows.map((b) => b.err ?? 0),
        color: colour,
        thickness: 1.2,
      },
      type: "scatter",
      mode: "markers",
      name,
      marker: { color: colour, size: 8, symbol },
    });

    return [
      asPoints(run.baseline.bandpowers ?? [], "#38bdf8", "baseline", "square"),
      asPoints(run.variant.bandpowers ?? [], "#f59e0b", "variant", "diamond"),
    ];
  }, [run]);

  const sliderTraces = useMemo<PlotData[]>(() => {
    const out: PlotData[] = [];
    if (baseTheory) {
      out.push({
        x: baseTheory.ell,
        y: baseTheory.dl_tt,
        type: "scatter",
        mode: "lines",
        name: "Planck 2018 best fit",
        line: { color: "#475569", width: 2, dash: "dot" },
      });
    }
    if (liveTheory) {
      out.push({
        x: liveTheory.ell,
        y: liveTheory.dl_tt,
        type: "scatter",
        mode: "lines",
        name: "your parameters",
        line: { color: "#38bdf8", width: 2.5 },
      });
    }
    return out;
  }, [baseTheory, liveTheory]);

  const grouped = DIFFICULTY_ORDER.map((level) => ({
    level,
    items: experiments.filter((e) => e.difficulty === level),
  })).filter((g) => g.items.length);

  return (
    <div className="view">
      <header className="view__head">
        <div>
          <h2>Playground</h2>
          <p className="muted">
            Change one thing, see what happens, understand why. The most instructive
            experiments are the ones that break the result.
          </p>
        </div>
      </header>

      <div className="playground-layout">
        <aside className="panel">
          <h3>Guided experiments</h3>
          {grouped.map((group) => (
            <div key={group.level} className="experiment-group">
              <div className="experiment-group__label">{group.level}</div>
              {group.items.map((e) => (
                <button
                  key={e.id}
                  className={`experiment ${selected === e.id ? "experiment--active" : ""}`}
                  onClick={() => void execute(e.id)}
                  disabled={busy}
                >
                  <span className="experiment__title">{e.title}</span>
                  <span className="experiment__question">{e.question}</span>
                </button>
              ))}
            </div>
          ))}
        </aside>

        <div className="playground-main">
          {busy && <div className="panel placeholder">running both arms…</div>}
          {error && <div className="error">{error}</div>}

          {run && !busy && (
            <>
              <section className="panel">
                <h3>{run.experiment.title}</h3>
                <p className="muted">{run.experiment.question}</p>

                <Plot
                  data={comparisonTraces}
                  layout={{
                    autosize: true,
                    height: 400,
                    paper_bgcolor: "rgba(0,0,0,0)",
                    plot_bgcolor: "rgba(0,0,0,0)",
                    font: { color: "#94a3b8", size: 11 },
                    margin: { l: 65, r: 20, t: 20, b: 50 },
                    xaxis: { title: { text: "multipole ℓ" }, gridcolor: "#1e293b" },
                    yaxis: {
                      title: { text: "𝒟ℓ  [µK²]" },
                      gridcolor: "#1e293b",
                      rangemode: "tozero",
                    },
                    legend: { orientation: "h", y: -0.2 },
                  }}
                  config={{ displaylogo: false, responsive: true }}
                  className="chart"
                />

                <div className="delta-row">
                  {Object.entries(run.delta).map(([key, value]) => (
                    <div key={key} className="delta">
                      <span className="delta__label">Δ {key}</span>
                      <span className="delta__value">
                        {value === null ? "—" : value > 0 ? `+${value}` : value}
                      </span>
                    </div>
                  ))}
                </div>

                {!revealed ? (
                  <button className="ghost" onClick={() => setRevealed(true)}>
                    Predict first, then reveal the explanation
                  </button>
                ) : (
                  <div className="note">
                    <strong>What happened</strong>
                    <p>{run.experiment.expect}</p>
                  </div>
                )}
              </section>
            </>
          )}

          <section className="panel">
            <h3>Free-form: build your own universe</h3>
            <p className="muted">
              Drag the sliders and watch the acoustic peaks respond in real time. The dotted
              grey curve is the Planck 2018 best fit for reference.
            </p>

            <div className="slider-grid">
              {knobs?.theory.map((knob) => (
                <label key={knob.id} className="field">
                  <span>
                    {knob.label}: <strong className="mono">{params[knob.id]?.toFixed(5)}</strong>
                  </span>
                  <input
                    type="range"
                    min={knob.min ?? 0}
                    max={knob.max ?? 1}
                    step={knob.step ?? 0.001}
                    value={params[knob.id] ?? 0}
                    onChange={(e) =>
                      setParams((prev) => ({ ...prev, [knob.id]: Number(e.target.value) }))
                    }
                  />
                  <span className="hint">{knob.watch_for}</span>
                </label>
              ))}
            </div>

            <Plot
              data={sliderTraces}
              layout={{
                autosize: true,
                height: 380,
                paper_bgcolor: "rgba(0,0,0,0)",
                plot_bgcolor: "rgba(0,0,0,0)",
                font: { color: "#94a3b8", size: 11 },
                margin: { l: 65, r: 20, t: 20, b: 50 },
                xaxis: { title: { text: "multipole ℓ" }, gridcolor: "#1e293b", range: [0, 1200] },
                yaxis: { title: { text: "𝒟ℓ  [µK²]" }, gridcolor: "#1e293b", rangemode: "tozero" },
                legend: { orientation: "h", y: -0.2 },
              }}
              config={{ displayModeBar: false, responsive: true }}
              className="chart"
            />

            {liveTheory && (
              <div className="delta-row">
                <div className="delta">
                  <span className="delta__label">first peak</span>
                  <span className="delta__value">ℓ = {liveTheory.peak1_ell}</span>
                </div>
                <div className="delta">
                  <span className="delta__label">Ω_m</span>
                  <span className="delta__value">
                    {liveTheory.derived.omega_m?.toFixed(4) ?? "—"}
                  </span>
                </div>
                <div className="delta">
                  <span className="delta__label">σ₈</span>
                  <span className="delta__value">
                    {liveTheory.derived.sigma8?.toFixed(4) ?? "—"}
                  </span>
                </div>
                <div className="delta">
                  <span className="delta__label">age</span>
                  <span className="delta__value">
                    {liveTheory.derived.age_gyr?.toFixed(2) ?? "—"} Gyr
                  </span>
                </div>
              </div>
            )}

            <button
              className="ghost"
              onClick={() =>
                setParams({ H0: 67.36, ombh2: 0.02237, omch2: 0.12, ns: 0.9649, tau: 0.0544 })
              }
            >
              Reset to Planck 2018
            </button>
          </section>
        </div>
      </div>
    </div>
  );
}
