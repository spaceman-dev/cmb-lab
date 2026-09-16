import { useEffect, useMemo, useState } from "react";
import type { PlotData } from "plotly.js-dist-min";
import { api, pollJob } from "../api/client";
import type { H0Measurement, InferenceResult, JobStatus } from "../api/types";
import { Plot } from "../components/Plot";

const PARAM_CHOICES = ["H0", "ombh2", "omch2", "ns"];

export function InferenceView() {
  const [free, setFree] = useState<string[]>(["H0", "ombh2", "omch2"]);
  const [walkers, setWalkers] = useState(20);
  const [steps, setSteps] = useState(400);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [result, setResult] = useState<InferenceResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tension, setTension] = useState<H0Measurement[]>([]);

  useEffect(() => {
    api.hubbleTension().then((d) => setTension(d.measurements)).catch(() => setTension([]));
  }, []);

  const run = async () => {
    setError(null);
    setResult(null);
    try {
      const { job_id } = await api.startInference({
        free_params: free,
        n_walkers: walkers,
        n_steps: steps,
      });
      const finished = await pollJob(`/inference/jobs/${job_id}`, setJob);
      if (finished.state === "succeeded") {
        setResult(finished.result as InferenceResult);
      } else {
        setError(finished.error ?? "The fit failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reach the cosmology service");
    }
  };

  const running = job?.state === "running" || job?.state === "pending";

  const tensionTraces = useMemo<PlotData[]>(() => {
    if (!tension.length) return [];
    const early = tension.filter((m) => m.probe === "early universe");
    const late = tension.filter((m) => m.probe !== "early universe");

    const build = (rows: H0Measurement[], colour: string, name: string): PlotData => ({
      x: rows.map((r) => r.value),
      y: rows.map((r) => r.key.replace(/_/g, " ")),
      error_x: { type: "data", array: rows.map((r) => r.err), color: colour, thickness: 2 },
      type: "scatter",
      mode: "markers",
      name,
      marker: { color: colour, size: 11, symbol: "diamond" },
      hovertemplate: "%{x:.2f} ± %{error_x.array:.2f}<extra>%{y}</extra>",
    });

    const ours: PlotData[] = result?.derived
      ? []
      : [];
    if (result?.posterior?.H0) {
      ours.push({
        x: [result.posterior.H0.mean],
        y: ["cmb-lab (yours)"],
        error_x: {
          type: "data",
          array: [result.posterior.H0.std],
          color: "#38bdf8",
          thickness: 3,
        },
        type: "scatter",
        mode: "markers",
        name: "your measurement",
        marker: { color: "#38bdf8", size: 15, symbol: "star" },
      });
    }

    return [
      build(early, "#a78bfa", "early universe"),
      build(late, "#fb923c", "late universe"),
      ...ours,
    ];
  }, [tension, result]);

  return (
    <div className="view">
      <header className="view__head">
        <div>
          <h2>Cosmological inference</h2>
          <p className="muted">
            Fit ΛCDM to the bandpowers we measured, using CAMB for theory and an
            affine-invariant ensemble sampler for the posterior. Gate G5 asks whether the
            result agrees with Planck 2018.
          </p>
        </div>
      </header>

      <section className="panel">
        <div className="controls">
          <div className="field">
            <span>Free parameters</span>
            <div className="chips">
              {PARAM_CHOICES.map((p) => (
                <button
                  key={p}
                  className={`chip ${free.includes(p) ? "chip--active" : ""}`}
                  onClick={() =>
                    setFree((prev) =>
                      prev.includes(p)
                        ? prev.filter((x) => x !== p)
                        : [...prev, p],
                    )
                  }
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          <label className="field">
            <span>Walkers</span>
            <input
              type="number"
              min={8}
              max={64}
              step={4}
              value={walkers}
              onChange={(e) => setWalkers(Number(e.target.value))}
            />
          </label>

          <label className="field">
            <span>Steps</span>
            <input
              type="number"
              min={100}
              max={3000}
              step={100}
              value={steps}
              onChange={(e) => setSteps(Number(e.target.value))}
            />
          </label>

          <button className="primary" onClick={() => void run()} disabled={running || !free.length}>
            {running ? "sampling…" : "Run MCMC"}
          </button>
        </div>

        <p className="hint">
          {walkers * steps} likelihood evaluations ≈ {Math.round((walkers * steps * 0.06) / 8)}s
          on this machine. τ is fixed to the published value: temperature data alone cannot
          separate it from the primordial amplitude.
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

      {result && (
        <>
          <section className={`panel gate ${result.gates.G5.passed ? "gate--pass" : "gate--fail"}`}>
            <div className="gate__head">
              <span className="gate__id">G5</span>
              <span className="gate__name">{result.gates.G5.name}</span>
              <span className="gate__badge">{result.gates.G5.passed ? "PASS" : "FAIL"}</span>
            </div>
            <p className="muted">{result.gates.G5.detail}</p>

            <table className="table">
              <thead>
                <tr>
                  <th>Parameter</th>
                  <th>Our measurement</th>
                  <th>Planck 2018</th>
                  <th>Tension</th>
                </tr>
              </thead>
              <tbody>
                {Object.values(result.gates.G5.comparisons).map((c) => (
                  <tr key={c.name}>
                    <td>{c.label}</td>
                    <td className="mono">
                      {c.ours.toFixed(4)} ± {c.ours_err.toFixed(4)}
                    </td>
                    <td className="mono muted">
                      {c.published.toFixed(4)} ± {c.published_err.toFixed(4)}
                    </td>
                    <td className={c.consistent ? "ok" : "bad"}>
                      {c.tension_sigma.toFixed(2)}σ
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <dl className="kv kv--tight">
              <div>
                <dt>χ²/dof</dt>
                <dd>{result.chi2_per_dof.toFixed(3)}</dd>
              </div>
              <div>
                <dt>acceptance</dt>
                <dd>{result.acceptance_fraction.toFixed(3)}</dd>
              </div>
              <div>
                <dt>autocorr τ</dt>
                <dd>{result.autocorr_time?.toFixed(1) ?? "—"}</dd>
              </div>
              <div>
                <dt>samples</dt>
                <dd>{result.n_samples.toLocaleString()}</dd>
              </div>
            </dl>
            <p className="hint">
              A healthy chain has acceptance around 0.2–0.7 and total length of at least ~50
              autocorrelation times.
            </p>
          </section>
        </>
      )}

      <section className="panel">
        <h3>The Hubble tension</h3>
        <p className="muted">
          Early-universe probes consistently give a lower expansion rate than late-universe
          distance ladders. Run the fit above and your own measurement joins the plot.
        </p>
        <Plot
          data={tensionTraces}
          layout={{
            autosize: true,
            height: 320,
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            font: { color: "#cbd5e1", size: 11 },
            margin: { l: 150, r: 20, t: 20, b: 45 },
            xaxis: { title: { text: "H₀  [km/s/Mpc]" }, gridcolor: "#1e293b" },
            yaxis: { gridcolor: "#1e293b", automargin: true },
            legend: { orientation: "h", y: -0.25 },
          }}
          config={{ displayModeBar: false, responsive: true }}
          className="chart"
        />
      </section>
    </div>
  );
}
