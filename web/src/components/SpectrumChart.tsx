import { useMemo } from "react";
import type { PlotData, PlotLayout } from "plotly.js-dist-min";
import { Plot } from "./Plot";
import type { ReferenceSpectrum, SpectrumResult } from "../api/types";

interface Props {
  result: SpectrumResult | null;
  references: ReferenceSpectrum[];
  logX: boolean;
}

const PALETTE = {
  ours: "#38bdf8",
  theory: "#f8fafc",
  wmap: "#fb923c",
  planck: "#a78bfa",
};

function referenceColour(slug: string): string {
  if (slug.startsWith("wmap")) return PALETTE.wmap;
  if (slug.startsWith("planck")) return PALETTE.planck;
  return "#94a3b8";
}

export function SpectrumChart({ result, references, logX }: Props) {
  const traces = useMemo<PlotData[]>(() => {
    const out: PlotData[] = [];

    // Best-fit LCDM curve, drawn first so measurements sit on top of it.
    const withTheory = references.find((r) => r.best_fit_dl_uk2);
    if (withTheory?.best_fit_dl_uk2) {
      out.push({
        x: withTheory.ell,
        y: withTheory.best_fit_dl_uk2,
        type: "scatter",
        mode: "lines",
        name: "ΛCDM best fit",
        line: { color: PALETTE.theory, width: 2, dash: "solid" },
        hovertemplate: "ℓ=%{x:.0f}<br>𝒟ℓ=%{y:.0f} µK²<extra>ΛCDM</extra>",
      });
    }

    for (const reference of references) {
      out.push({
        x: reference.ell,
        y: reference.dl_uk2,
        type: "scatter",
        mode: "markers",
        name: `${reference.mission} published`,
        marker: { color: referenceColour(reference.slug), size: 5, symbol: "circle-open" },
        error_y: {
          type: "data",
          symmetric: false,
          array: reference.err_hi,
          arrayminus: reference.err_lo,
          color: referenceColour(reference.slug),
          thickness: 1,
          width: 0,
        },
        hovertemplate: `ℓ=%{x:.0f}<br>𝒟ℓ=%{y:.0f} µK²<extra>${reference.mission}</extra>`,
      });
    }

    if (result) {
      out.push({
        x: result.bandpowers.map((b) => b.ell_eff),
        y: result.bandpowers.map((b) => b.dl_uk2),
        type: "scatter",
        mode: "markers",
        name: "our measurement",
        marker: { color: PALETTE.ours, size: 9, symbol: "square" },
        error_y: {
          type: "data",
          array: result.bandpowers.map((b) => b.dl_err_uk2 ?? 0),
          color: PALETTE.ours,
          thickness: 1.6,
          width: 3,
        },
        error_x: {
          type: "data",
          symmetric: false,
          array: result.bandpowers.map((b) => b.ell_max - b.ell_eff),
          arrayminus: result.bandpowers.map((b) => b.ell_eff - b.ell_min),
          color: PALETTE.ours,
          thickness: 1,
          width: 0,
        },
        hovertemplate: "ℓ=%{x:.0f}<br>𝒟ℓ=%{y:.0f} µK²<extra>cmb-lab</extra>",
      });
    }

    return out;
  }, [result, references]);

  const layout = useMemo<PlotLayout>(
    () => ({
      autosize: true,
      height: 520,
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { color: "#cbd5e1", family: "ui-monospace, SFMono-Regular, monospace", size: 12 },
      margin: { l: 70, r: 20, t: 40, b: 60 },
      title: {
        text: "CMB temperature angular power spectrum",
        font: { size: 15, color: "#e2e8f0" },
      },
      xaxis: {
        title: { text: "multipole moment  ℓ" },
        type: logX ? "log" : "linear",
        gridcolor: "#1e293b",
        zerolinecolor: "#334155",
        range: logX ? [Math.log10(2), Math.log10(1200)] : [0, 1000],
      },
      yaxis: {
        title: { text: "𝒟ℓ = ℓ(ℓ+1)Cℓ / 2π   [µK²]" },
        gridcolor: "#1e293b",
        zerolinecolor: "#334155",
        rangemode: "tozero",
      },
      legend: {
        orientation: "h",
        y: -0.18,
        bgcolor: "rgba(0,0,0,0)",
      },
      hovermode: "closest",
      shapes: result
        ? [
            {
              type: "line",
              x0: result.gates.G3.measured.ell,
              x1: result.gates.G3.measured.ell,
              y0: 0,
              y1: 1,
              yref: "paper",
              line: { color: PALETTE.ours, width: 1, dash: "dot" },
            },
          ]
        : [],
      annotations: result
        ? [
            {
              x: logX ? Math.log10(result.gates.G3.measured.ell) : result.gates.G3.measured.ell,
              y: 1,
              yref: "paper",
              text: `1st peak  ℓ=${result.gates.G3.measured.ell}`,
              showarrow: false,
              yanchor: "bottom",
              font: { color: PALETTE.ours, size: 11 },
            },
          ]
        : [],
    }),
    [logX, result],
  );

  return (
    <Plot
      data={traces}
      layout={layout}
      config={{ displayModeBar: true, displaylogo: false, responsive: true }}
      className="chart"
    />
  );
}
