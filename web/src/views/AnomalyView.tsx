import { useEffect, useMemo, useState } from "react";
import type { PlotData } from "plotly.js-dist-min";
import { api, pollJob } from "../api/client";
import type { AnomalyReport, AnomalyStat, JobStatus } from "../api/types";
import { Plot } from "../components/Plot";

export function AnomalyView() {
  const [nSims, setNSims] = useState(500);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [report, setReport] = useState<AnomalyReport | null>(null);
  const [quick, setQuick] = useState<Record<string, { name: string; unit: string; values: Record<string, number> }> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [focus, setFocus] = useState<string | null>(null);

  useEffect(() => {
    api
      .measureAnomalies({})
      .then((d) => setQuick(d.results))
      .catch(() => setQuick(null));
  }, []);

  const run = async () => {
    setError(null);
    setReport(null);
    try {
      const { job_id } = await api.startAnomalyJob({ n_sims: nSims });
      const finished = await pollJob(`/anomaly/jobs/${job_id}`, setJob);
      if (finished.state === "succeeded") {
        const result = finished.result as AnomalyReport;
        setReport(result);
        setFocus(Object.keys(result.statistics)[0] ?? null);
      } else {
        setError(finished.error ?? "The analysis failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reach the anomaly service");
    }
  };

  const running = job?.state === "running" || job?.state === "pending";
  const active: AnomalyStat | null = report && focus ? report.statistics[focus] : null;

  const nullTraces = useMemo<PlotData[]>(() => {
    if (!active) return [];
    return [
      {
        x: active.null.histogram.centres,
        y: active.null.histogram.counts,
        type: "bar",
        name: "isotropic simulations",
        marker: { color: "#475569" },
        hovertemplate: "%{y} sims<extra></extra>",
      },
      {
        x: [active.observed, active.observed],
        y: [0, Math.max(...active.null.histogram.counts)],
        type: "scatter",
        mode: "lines",
        name: "observed sky",
        line: { color: "#38bdf8", width: 3 },
      },
    ];
  }, [active]);

  return (
    <div className="view">
      <header className="view__head">
        <div>
          <h2>Large-angle anomalies</h2>
          <p className="muted">
            Four features of the CMB that have resisted explanation for twenty years. The
            measurement is easy; the significance is not. Gate G6 checks that the p-value
            machinery is calibrated before any claim is made.
          </p>
        </div>
      </header>

      {quick && (
        <section className="panel">
          <h3>Measured on the real sky</h3>
          <p className="muted">
            These are just numbers — no significance yet. That requires simulations.
          </p>
          <div className="stat-grid">
            {Object.entries(quick).map(([key, entry]) => {
              const primary = Object.entries(entry.values)[0];
              return (
                <div key={key} className="stat-card">
                  <div className="stat-card__name">{entry.name}</div>
                  <div className="stat-card__value">
                    {typeof primary?.[1] === "number" ? primary[1].toFixed(2) : "—"}
                    <span className="stat-card__unit"> {entry.unit}</span>
                  </div>
                  <div className="stat-card__detail">
                    {Object.entries(entry.values)
                      .slice(1, 4)
                      .map(([k, v]) => `${k}: ${typeof v === "number" ? v.toFixed(1) : v}`)
                      .join(" · ")}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      <section className="panel">
        <div className="controls">
          <label className="field">
            <span>Monte Carlo realisations</span>
            <input
              type="number"
              min={100}
              max={5000}
              step={100}
              value={nSims}
              onChange={(e) => setNSims(Number(e.target.value))}
            />
          </label>
          <button className="primary" onClick={() => void run()} disabled={running}>
            {running ? "simulating…" : "Run full analysis"}
          </button>
        </div>
        <p className="hint">
          Each realisation is an isotropic ΛCDM sky put through the identical analysis,
          including the same search over axes. Four statistics × {nSims} simulations, run in
          parallel across your cores.
        </p>

        {running && job && (
          <div className="progress">
            <div className="progress__bar">
              <div className="progress__fill" style={{ width: `${job.progress * 100}%` }} />
            </div>
            <div className="progress__label">
              {job.message} · {(job.progress * 100).toFixed(0)}% · {job.elapsed_s.toFixed(0)}s
            </div>
          </div>
        )}

        {error && <div className="error">{error}</div>}
      </section>

      {report && (
        <>
          <section
            className={`panel gate ${report.gates.G6.passed ? "gate--pass" : "gate--fail"}`}
          >
            <div className="gate__head">
              <span className="gate__id">G6</span>
              <span className="gate__name">{report.gates.G6.name}</span>
              <span className="gate__badge">{report.gates.G6.passed ? "PASS" : "FAIL"}</span>
            </div>
            <p className="muted">{report.gates.G6.detail}</p>
            <p className="hint">
              This gate does <strong>not</strong> claim the anomalies are real. It verifies
              that skies which are isotropic by construction produce uniform p-values — if
              they did not, every result below would be meaningless.
            </p>
          </section>

          <section className="panel">
            <h3>Significance</h3>
            <div className="chips">
              {Object.entries(report.statistics).map(([key, stat]) => (
                <button
                  key={key}
                  className={`chip ${focus === key ? "chip--active" : ""}`}
                  onClick={() => setFocus(key)}
                >
                  {stat.human_name}
                </button>
              ))}
            </div>

            <table className="table">
              <thead>
                <tr>
                  <th>Statistic</th>
                  <th>Observed</th>
                  <th>Isotropic mean</th>
                  <th>p (raw)</th>
                  <th>p (corrected)</th>
                  <th>σ</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(report.statistics).map(([key, stat]) => (
                  <tr key={key} className={focus === key ? "row--active" : ""}>
                    <td>{stat.human_name}</td>
                    <td className="mono">
                      {stat.observed.toFixed(2)} {stat.unit}
                    </td>
                    <td className="mono muted">
                      {stat.null.mean.toFixed(2)} ± {stat.null.std.toFixed(2)}
                    </td>
                    <td className="mono">{stat.p_value.toFixed(4)}</td>
                    <td className={`mono ${stat.p_value_corrected < 0.05 ? "bad" : ""}`}>
                      {stat.p_value_corrected.toFixed(4)}
                    </td>
                    <td className="mono">{stat.sigma_equivalent.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <p className="hint">
              Read the <strong>corrected</strong> column. Four statistics were tested, so the
              raw p-value overstates the case by roughly a factor of four (Šidák).
            </p>
          </section>

          {active && (
            <section className="panel">
              <h3>{active.human_name} — null distribution</h3>
              <p className="muted">
                Grey is what {active.n_sims.toLocaleString()} isotropic universes produce.
                Blue is our sky. The p-value is simply the fraction of the grey distribution
                at least as extreme as the blue line.
              </p>
              <Plot
                data={nullTraces}
                layout={{
                  autosize: true,
                  height: 320,
                  paper_bgcolor: "rgba(0,0,0,0)",
                  plot_bgcolor: "rgba(0,0,0,0)",
                  font: { color: "#94a3b8", size: 11 },
                  margin: { l: 55, r: 20, t: 15, b: 45 },
                  xaxis: {
                    title: { text: `${active.human_name} [${active.unit}]` },
                    gridcolor: "#1e293b",
                  },
                  yaxis: { title: { text: "simulations" }, gridcolor: "#1e293b" },
                  legend: { orientation: "h", y: 1.15 },
                  bargap: 0.03,
                }}
                config={{ displayModeBar: false, responsive: true }}
                className="chart"
              />
              <dl className="kv kv--tight">
                <div>
                  <dt>more extreme sims</dt>
                  <dd>
                    {active.n_more_extreme} / {active.n_sims}
                  </dd>
                </div>
                <div>
                  <dt>tail tested</dt>
                  <dd>{active.lower_tail ? "lower" : "upper"}</dd>
                </div>
                <div>
                  <dt>trials corrected</dt>
                  <dd>{active.n_trials_corrected}</dd>
                </div>
              </dl>
            </section>
          )}
        </>
      )}
    </div>
  );
}
