import { useEffect, useState } from "react";
import { api } from "./api/client";
import type { GatewayHealth } from "./api/types";
import { Starfield } from "./components/Starfield";
import { AnomalyView } from "./views/AnomalyView";
import { ChatDock } from "./views/ChatDock";
import { InferenceView } from "./views/InferenceView";
import { LearnView } from "./views/LearnView";
import { PlaygroundView } from "./views/PlaygroundView";
import { SkyMapView } from "./views/SkyMapView";
import { SpectrumView } from "./views/SpectrumView";

const TABS = [
  { id: "spectrum", label: "Spectrum", hint: "Measure the power spectrum" },
  { id: "skymap", label: "Sky Map", hint: "Every projection and angular scale" },
  { id: "inference", label: "Inference", hint: "Fit ΛCDM parameters (G5)" },
  { id: "anomalies", label: "Anomalies", hint: "Isotropy tests (G6)" },
  { id: "playground", label: "Playground", hint: "Break things, learn why" },
  { id: "learn", label: "Learn", hint: "Derivations and audio explainers" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function App() {
  const [tab, setTab] = useState<TabId>(() => {
    const hash = window.location.hash.replace("#", "");
    return TABS.some((t) => t.id === hash) ? (hash as TabId) : "spectrum";
  });
  const [health, setHealth] = useState<GatewayHealth | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const check = () => api.health().then(setHealth).catch(() => setHealth(null));
    check();
    const timer = setInterval(check, 30000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (window.location.hash.replace("#", "") !== tab) {
      window.location.hash = tab;
    }
    setMenuOpen(false);
  }, [tab]);

  // Keep browser back/forward and pasted deep links working, not just the initial load.
  useEffect(() => {
    const onHashChange = () => {
      const hash = window.location.hash.replace("#", "");
      if (TABS.some((t) => t.id === hash)) setTab(hash as TabId);
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const down = health?.upstreams.filter((u) => u.status !== "ok") ?? [];

  return (
    <>
      <Starfield />

      <div className="app">
        <header className="masthead">
          <div className="masthead__brand">
            <h1>
              cmb<span className="accent">·</span>lab
            </h1>
            <p className="tagline">
              An independent reproduction of the cosmic microwave background, from raw NASA
              archive data
            </p>
          </div>

          <button
            className="masthead__menu"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label="Toggle navigation"
          >
            ☰
          </button>

          <div className="masthead__status">
            {health ? (
              down.length === 0 ? (
                <span className="status status--ok">
                  {health.upstreams.length} services online
                </span>
              ) : (
                <span className="status status--warn">
                  {down.length} service{down.length > 1 ? "s" : ""} down
                </span>
              )
            ) : (
              <span className="status status--bad">gateway unreachable</span>
            )}
          </div>
        </header>

        <nav className={`tabs ${menuOpen ? "tabs--open" : ""}`}>
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`tab ${tab === t.id ? "tab--active" : ""}`}
              onClick={() => setTab(t.id)}
              title={t.hint}
            >
              <span className="tab__label">{t.label}</span>
              <span className="tab__hint">{t.hint}</span>
            </button>
          ))}
        </nav>

        <main>
          {tab === "spectrum" && <SpectrumView />}
          {tab === "skymap" && <SkyMapView />}
          {tab === "inference" && <InferenceView />}
          {tab === "anomalies" && <AnomalyView />}
          {tab === "playground" && <PlaygroundView />}
          {tab === "learn" && <LearnView />}
        </main>

        <footer className="footer">
          <p>
            Data: NASA LAMBDA (WMAP 9-year DR5) and ESA Planck Legacy Archive (PR3). Theory:
            CAMB. No API key required for any CMB data.
          </p>
        </footer>
      </div>

      <ChatDock />
    </>
  );
}
