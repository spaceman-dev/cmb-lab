import { useEffect, useMemo, useState } from "react";
import type { PlotData, PlotLayout } from "plotly.js-dist-min";
import { api } from "../api/client";
import type { MapEntry, Preset, ProjectionsResponse, SkyStats, SphereData } from "../api/types";
import { Plot } from "../components/Plot";

const DEFAULT_MAP = { dataset: "wmap9", product: "ilc-map" };

export function SkyMapView() {
  const [meta, setMeta] = useState<ProjectionsResponse | null>(null);
  const [maps, setMaps] = useState<MapEntry[]>([]);
  const [selected, setSelected] = useState(DEFAULT_MAP);

  const [projection, setProjection] = useState("mollweide");
  const [cmap, setCmap] = useState("planck");
  const [preset, setPreset] = useState<Preset | null>(null);
  const [lon, setLon] = useState(0);
  const [lat, setLat] = useState(0);
  const [fov, setFov] = useState(30);
  const [smooth, setSmooth] = useState(0);
  const [graticule, setGraticule] = useState(true);

  const [sphere, setSphere] = useState<SphereData | null>(null);
  const [stats, setStats] = useState<SkyStats | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.projections().then((data) => {
      setMeta(data);
      setPreset(data.presets.find((p) => p.id === "full") ?? data.presets[0]);
    });
    api.maps().then(({ maps }) => setMaps(maps.filter((m) => m.has_preview)));
  }, []);

  const ellMin = preset?.ell_min ?? 2;
  const ellMax = preset?.ell_max ?? 767;

  useEffect(() => {
    setLoading(true);
    api
      .skyStats(selected.dataset, selected.product, ellMin, ellMax)
      .then(setStats)
      .catch(() => setStats(null))
      .finally(() => setLoading(false));
  }, [selected, ellMin, ellMax]);

  useEffect(() => {
    if (projection !== "sphere3d") return;
    setLoading(true);
    api
      .sphere(selected.dataset, selected.product, ellMin, ellMax)
      .then(setSphere)
      .catch(() => setSphere(null))
      .finally(() => setLoading(false));
  }, [projection, selected, ellMin, ellMax]);

  const imageUrl = useMemo(
    () =>
      api.renderUrl(selected.dataset, selected.product, {
        projection,
        cmap,
        lon,
        lat,
        fov_deg: fov,
        ell_min: ellMin,
        ell_max: ellMax,
        smooth_deg: smooth,
        graticule,
        title: preset?.label ?? "",
      }),
    [selected, projection, cmap, lon, lat, fov, ellMin, ellMax, smooth, graticule, preset],
  );

  const sphereTraces = useMemo<PlotData[]>(() => {
    if (!sphere) return [];
    return [
      {
        type: "surface",
        x: sphere.x,
        y: sphere.y,
        z: sphere.z,
        surfacecolor: sphere.values,
        cmin: sphere.vmin,
        cmax: sphere.vmax,
        colorscale: [
          [0, "#1d4ed8"],
          [0.25, "#06b6d4"],
          [0.5, "#f8fafc"],
          [0.75, "#f59e0b"],
          [1, "#b91c1c"],
        ],
        showscale: true,
        colorbar: { title: { text: "µK" }, thickness: 12, len: 0.7 },
        lighting: { ambient: 0.95, diffuse: 0.1, specular: 0 },
        hovertemplate: "%{surfacecolor:.1f} µK<extra></extra>",
      },
    ];
  }, [sphere]);

  const sphereLayout = useMemo<PlotLayout>(
    () => ({
      autosize: true,
      height: 560,
      paper_bgcolor: "rgba(0,0,0,0)",
      font: { color: "#cbd5e1", size: 11 },
      margin: { l: 0, r: 0, t: 10, b: 0 },
      scene: {
        xaxis: { visible: false },
        yaxis: { visible: false },
        zaxis: { visible: false },
        aspectmode: "data",
        bgcolor: "rgba(0,0,0,0)",
        camera: { eye: { x: 1.5, y: 1.5, z: 0.9 } },
      },
    }),
    [],
  );

  const histogramTraces = useMemo<PlotData[]>(() => {
    if (!stats) return [];
    return [
      {
        x: stats.histogram.centres,
        y: stats.histogram.density,
        type: "bar",
        name: "measured",
        marker: { color: "#38bdf8", opacity: 0.75 },
      },
      {
        x: stats.histogram.centres,
        y: stats.histogram.gaussian,
        type: "scatter",
        mode: "lines",
        name: "Gaussian",
        line: { color: "#f59e0b", width: 2 },
      },
    ];
  }, [stats]);

  const supportsDirection = ["orthographic", "gnomonic", "cartesian"].includes(projection);

  return (
    <div className="view">
      <header className="view__head">
        <div>
          <h2>Sky map explorer</h2>
          <p className="muted">
            The same data, every way of looking at it. Filter by multipole to isolate an
            angular scale — the quadrupole and octupole presets make the alignment anomaly
            visible directly.
          </p>
        </div>
      </header>

      <div className="skymap-layout">
        <aside className="panel skymap-controls">
          <h3>Map</h3>
          <div className="chips">
            {maps.map((m) => (
              <button
                key={`${m.dataset}/${m.product}`}
                className={`chip ${selected.product === m.product ? "chip--active" : ""}`}
                onClick={() => setSelected({ dataset: m.dataset, product: m.product })}
              >
                {m.product}
              </button>
            ))}
          </div>

          <h3>Projection</h3>
          <div className="chips">
            {meta?.projections.map((p) => (
              <button
                key={p.id}
                className={`chip ${projection === p.id ? "chip--active" : ""}`}
                onClick={() => setProjection(p.id)}
                title={p.description}
              >
                {p.label}
              </button>
            ))}
          </div>
          {meta && (
            <p className="hint">
              {meta.projections.find((p) => p.id === projection)?.description}
            </p>
          )}

          <h3>Angular scale</h3>
          <div className="chips">
            {meta?.presets.map((p) => (
              <button
                key={p.id}
                className={`chip ${preset?.id === p.id ? "chip--active" : ""}`}
                onClick={() => setPreset(p)}
              >
                {p.label}
              </button>
            ))}
          </div>
          {preset && <p className="hint">{preset.explain}</p>}

          <h3>Appearance</h3>
          <label className="field">
            <span>Colour map</span>
            <select value={cmap} onChange={(e) => setCmap(e.target.value)}>
              {meta?.colormaps.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Smoothing: {smooth.toFixed(1)}°</span>
            <input
              type="range"
              min={0}
              max={5}
              step={0.25}
              value={smooth}
              onChange={(e) => setSmooth(Number(e.target.value))}
            />
          </label>

          <label className="checkbox">
            <input
              type="checkbox"
              checked={graticule}
              onChange={(e) => setGraticule(e.target.checked)}
            />
            <span>Coordinate grid</span>
          </label>

          {supportsDirection && (
            <>
              <h3>Direction</h3>
              <label className="field">
                <span>Galactic longitude: {lon.toFixed(0)}°</span>
                <input
                  type="range"
                  min={-180}
                  max={180}
                  step={5}
                  value={lon}
                  onChange={(e) => setLon(Number(e.target.value))}
                />
              </label>
              <label className="field">
                <span>Galactic latitude: {lat.toFixed(0)}°</span>
                <input
                  type="range"
                  min={-90}
                  max={90}
                  step={5}
                  value={lat}
                  onChange={(e) => setLat(Number(e.target.value))}
                />
              </label>
              {projection === "gnomonic" && (
                <label className="field">
                  <span>Field of view: {fov.toFixed(0)}°</span>
                  <input
                    type="range"
                    min={2}
                    max={90}
                    step={2}
                    value={fov}
                    onChange={(e) => setFov(Number(e.target.value))}
                  />
                </label>
              )}
              <button
                className="ghost"
                onClick={() => {
                  setLon(209);
                  setLat(-57);
                  setProjection("gnomonic");
                  setFov(30);
                }}
              >
                Jump to the Cold Spot
              </button>
            </>
          )}
        </aside>

        <div className="skymap-main">
          <section className="panel panel--chart">
            {projection === "sphere3d" ? (
              sphere ? (
                <Plot
                  data={sphereTraces}
                  layout={sphereLayout}
                  config={{ displaylogo: false, responsive: true }}
                  className="chart"
                />
              ) : (
                <div className="placeholder">{loading ? "building globe…" : "no data"}</div>
              )
            ) : (
              <img className="skymap-image" src={imageUrl} alt={`${projection} projection`} />
            )}
          </section>

          {stats && (
            <section className="panel">
              <h3>Is the field Gaussian?</h3>
              <p className="muted">
                Inflation predicts nearly Gaussian primordial fluctuations, so the pixel
                histogram should follow a bell curve. A detected departure would be a major
                discovery — so far, none has held up.
              </p>
              <Plot
                data={histogramTraces}
                layout={{
                  autosize: true,
                  height: 240,
                  paper_bgcolor: "rgba(0,0,0,0)",
                  plot_bgcolor: "rgba(0,0,0,0)",
                  font: { color: "#94a3b8", size: 11 },
                  margin: { l: 55, r: 15, t: 10, b: 40 },
                  xaxis: { title: { text: "temperature [µK]" }, gridcolor: "#1e293b" },
                  yaxis: { title: { text: "density" }, gridcolor: "#1e293b" },
                  legend: { orientation: "h", y: 1.15 },
                  bargap: 0.02,
                }}
                config={{ displayModeBar: false, responsive: true }}
                className="chart"
              />
              <dl className="kv kv--tight">
                <div>
                  <dt>RMS</dt>
                  <dd>{stats.rms_uk.toFixed(1)} µK</dd>
                </div>
                <div>
                  <dt>skewness</dt>
                  <dd>{stats.skewness.toFixed(4)}</dd>
                </div>
                <div>
                  <dt>kurtosis</dt>
                  <dd>{stats.kurtosis.toFixed(4)}</dd>
                </div>
              </dl>
              <p className="hint">
                A perfect Gaussian has skewness 0 and excess kurtosis 0.
              </p>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
