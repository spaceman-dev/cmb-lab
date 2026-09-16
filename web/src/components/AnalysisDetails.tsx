import type { SpectrumResult } from "../api/types";

/** Estimator provenance: exactly what was done to produce the plotted numbers. */
export function AnalysisDetails({ result }: { result: SpectrumResult }) {
  const ps = result.point_source;

  return (
    <section className="panel">
      <h2>Analysis provenance</h2>

      <dl className="kv">
        <div>
          <dt>input</dt>
          <dd>{result.map_label}</dd>
        </div>
        <div>
          <dt>estimator</dt>
          <dd>
            {result.estimator === "cross"
              ? "cross-spectrum (noise-unbiased)"
              : "auto-spectrum (noise-biased at high ℓ)"}
          </dd>
        </div>
        <div>
          <dt>sky fraction</dt>
          <dd>{(result.f_sky * 100).toFixed(1)}%</dd>
        </div>
        <div>
          <dt>ℓ range</dt>
          <dd>
            2 – {result.reliable_lmax}
            {result.reliable_lmax < result.lmax && (
              <span className="muted"> (capped from {result.lmax})</span>
            )}
          </dd>
        </div>
        {result.snr_lmax != null && result.beam_lmax != null && (
          <div>
            <dt>cutoff reason</dt>
            <dd>
              {result.snr_lmax <= result.beam_lmax
                ? `signal/noise collapses past ℓ ≈ ${result.snr_lmax}`
                : `beam transfer function closes at ℓ ≈ ${result.beam_lmax}`}
            </dd>
          </div>
        )}
        <div>
          <dt>beam</dt>
          <dd>{result.beams.length ? result.beams.join(", ") : "not deconvolved"}</dd>
        </div>
        <div>
          <dt>pixel window</dt>
          <dd>{result.pixwin_corrected ? "deconvolved" : "not applied"}</dd>
        </div>
      </dl>

      {ps && (
        <div className="note">
          <strong>Unresolved point sources removed.</strong>
          <p>
            A<sub>ps</sub> = {ps.amplitude_uk2_sr.toExponential(3)} µK²·sr, fitted via{" "}
            {ps.method}. Cross-spectra cancel detector noise but not real sky signal, so the
            Poisson background of faint galaxies survives as a flat C<sub>ℓ</sub> — which
            grows as ℓ² in 𝒟<sub>ℓ</sub> and dominates the residual above ℓ ≈ 350.
          </p>
          {ps.circular && (
            <p className="muted">
              Note: this fit assumes the reference ΛCDM curve is correct. The non-circular
              alternative separates sources by their frequency dependence.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
