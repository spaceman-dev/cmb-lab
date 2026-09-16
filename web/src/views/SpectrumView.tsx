import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { CrossSpectrumRequest, ReferenceSpectrum, SpectrumResult } from "../api/types";
import { AnalysisDetails } from "../components/AnalysisDetails";
import { GatePanel } from "../components/GatePanel";
import { SpectrumChart } from "../components/SpectrumChart";

const DETECTORS = ["da-v1", "da-v2", "da-w1", "da-w2"];

type Params = Required<
  Pick<
    CrossSpectrumRequest,
    "product_a" | "product_b" | "lmax" | "binning" | "subtract_point_sources"
  >
>;

export function SpectrumView() {
  const [result, setResult] = useState<SpectrumResult | null>(null);
  const [references, setReferences] = useState<ReferenceSpectrum[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [logX, setLogX] = useState(false);

  const [params, setParams] = useState<Params>({
    product_a: "da-v1",
    product_b: "da-v2",
    lmax: 800,
    binning: "linear:30",
    subtract_point_sources: true,
  });

  useEffect(() => {
    Promise.allSettled([
      api.reference("planck18-TT-binned"),
      api.reference("wmap9-TT-binned"),
    ]).then((settled) => {
      setReferences(
        settled
          .filter((s): s is PromiseFulfilledResult<ReferenceSpectrum> => s.status === "fulfilled")
          .map((s) => s.value),
      );
    });
  }, []);

  const compute = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setResult(await api.crossSpectrum(params));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `${err.code ?? "error"}: ${err.message}`
          : "Could not reach the gateway. Run ./scripts/dev.sh up",
      );
    } finally {
      setLoading(false);
    }
  }, [params]);

  useEffect(() => {
    void compute();
    // Initial load only; later runs come from the Recompute button.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="view">
      <header className="view__head">
        <div>
          <h2>Power spectrum</h2>
          <p className="muted">
            A noise-unbiased cross-spectrum between two WMAP detectors, with the archive's
            measured beams deconvolved and unresolved point sources removed.
          </p>
        </div>
        {result && (
          <div className="headline">
            <span className="headline__label">first acoustic peak</span>
            <span className="headline__value">ℓ = {result.gates.G3.measured.ell}</span>
            <span className="headline__sub">
              𝒟ℓ = {result.gates.G3.measured.dl_uk2.toLocaleString()} µK²
            </span>
          </div>
        )}
      </header>

      <section className="panel">
        <div className="controls">
          <label className="field">
            <span>Detector A</span>
            <select
              value={params.product_a}
              onChange={(e) => setParams({ ...params, product_a: e.target.value })}
            >
              {DETECTORS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Detector B</span>
            <select
              value={params.product_b}
              onChange={(e) => setParams({ ...params, product_b: e.target.value })}
            >
              {DETECTORS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>ℓ max</span>
            <input
              type="number"
              min={100}
              max={1500}
              step={50}
              value={params.lmax}
              onChange={(e) => setParams({ ...params, lmax: Number(e.target.value) })}
            />
          </label>

          <label className="field">
            <span>Binning</span>
            <select
              value={params.binning}
              onChange={(e) => setParams({ ...params, binning: e.target.value })}
            >
              <option value="linear:15">linear Δℓ=15</option>
              <option value="linear:30">linear Δℓ=30</option>
              <option value="linear:50">linear Δℓ=50</option>
              <option value="log:20">logarithmic</option>
              <option value="planck">Planck-like</option>
            </select>
          </label>

          <label className="checkbox">
            <input
              type="checkbox"
              checked={params.subtract_point_sources}
              onChange={(e) =>
                setParams({ ...params, subtract_point_sources: e.target.checked })
              }
            />
            <span>subtract point sources</span>
          </label>

          <label className="checkbox">
            <input type="checkbox" checked={logX} onChange={(e) => setLogX(e.target.checked)} />
            <span>log ℓ axis</span>
          </label>

          <button className="primary" onClick={() => void compute()} disabled={loading}>
            {loading ? "computing…" : "Recompute"}
          </button>
        </div>
      </section>

      {error && <div className="error">{error}</div>}

      <div className="layout">
        <div className="layout__main">
          <section className="panel panel--chart">
            <SpectrumChart result={result} references={references} logX={logX} />
            {result?.cached && <p className="muted cache-note">served from gateway cache</p>}
          </section>
        </div>

        <aside className="layout__side">
          {result && <GatePanel result={result} />}
          {result && <AnalysisDetails result={result} />}
        </aside>
      </div>
    </div>
  );
}
