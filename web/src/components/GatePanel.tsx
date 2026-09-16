import type { SpectrumResult } from "../api/types";

/**
 * Validation gate readout.
 *
 * The gates are the scientific contract of the project: each one asserts a published
 * value, so a green panel means the pipeline reproduced real physics rather than merely
 * running without crashing.
 */
export function GatePanel({ result }: { result: SpectrumResult }) {
  const g3 = result.gates.G3;
  const comparisons = Object.entries(result.gates.G4.comparisons);

  return (
    <section className="panel">
      <h2>Validation gates</h2>

      <div className={`gate ${g3.passed ? "gate--pass" : "gate--fail"}`}>
        <div className="gate__head">
          <span className="gate__id">G3</span>
          <span className="gate__name">First acoustic peak</span>
          <span className="gate__badge">{g3.passed ? "PASS" : "FAIL"}</span>
        </div>
        <dl className="gate__grid">
          <div>
            <dt>measured ℓ</dt>
            <dd>{g3.measured.ell}</dd>
          </div>
          <div>
            <dt>expected ℓ</dt>
            <dd>{g3.expected.ell}</dd>
          </div>
          <div>
            <dt>measured 𝒟ℓ</dt>
            <dd>{g3.measured.dl_uk2.toLocaleString()} µK²</dd>
          </div>
          <div>
            <dt>expected 𝒟ℓ</dt>
            <dd>{g3.expected.dl_uk2.toLocaleString()} µK²</dd>
          </div>
        </dl>
      </div>

      {comparisons.map(([slug, c]) => (
        <div key={slug} className={`gate ${c.passed ? "gate--pass" : "gate--fail"}`}>
          <div className="gate__head">
            <span className="gate__id">G4</span>
            <span className="gate__name">vs {slug}</span>
            <span className="gate__badge">{c.passed ? "PASS" : "FAIL"}</span>
          </div>
          <dl className="gate__grid">
            <div>
              <dt>χ²/dof</dt>
              <dd className="gate__hero">{c.chi2_per_dof.toFixed(2)}</dd>
            </div>
            <div>
              <dt>χ²</dt>
              <dd>{c.chi2.toFixed(1)}</dd>
            </div>
            <div>
              <dt>dof</dt>
              <dd>{c.dof}</dd>
            </div>
            <div>
              <dt>bandpowers</dt>
              <dd>{c.n_compared}</dd>
            </div>
          </dl>
        </div>
      ))}
    </section>
  );
}
