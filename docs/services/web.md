# web

**Path:** `web/` · **Dev port:** 5174 · **React 18 + TypeScript + Vite**

The frontend. Six tabs, a night-sky theme, and a physics assistant docked in the corner.

> Vite runs on **5174**, not the usual 5173, because 5173 was occupied on the development
> machine. The gateway's CORS config allows both.

## Structure

```
src/
  App.tsx              tab routing, starfield, health polling, chat dock
  api/
    client.ts          every backend call, one function each
    types.ts           TypeScript mirrors of the pydantic models
  components/
    Math.tsx           KaTeX rendering: <Math> and <RichText>
    Starfield.tsx      animated canvas background
    AudioPlayer.tsx    server audio with SpeechSynthesis fallback
    Plot.tsx           Plotly wrapper
    GatePanel.tsx      pass/fail display for validation gates
    AnalysisDetails.tsx
    SpectrumChart.tsx
  views/
    SpectrumView.tsx   run the pipeline, see the peak
    SkyMapView.tsx     projections, filters, presets
    InferenceView.tsx  MCMC, corner plots, parameter table
    AnomalyView.tsx    the four anomalies with calibrated p-values
    PlaygroundView.tsx knobs and guided experiments
    LearnView.tsx      the curriculum, with reading-depth control
    ChatDock.tsx       the assistant
  styles.css           theme, layout, components
```

## Tabs

| Tab | What you do there |
| --- | --- |
| **Spectrum** | Choose detector maps, run the pipeline, see ℓ = 220 emerge with gates G3/G4 |
| **Sky Map** | Explore the CMB in four projections, filter by multipole band |
| **Inference** | Run MCMC, watch the posterior, compare to Planck 2018 |
| **Anomalies** | Measure the four anomalies, calibrate against simulations |
| **Playground** | Turn knobs, break the pipeline deliberately, see what each choice does |
| **Learn** | Six lessons at three reading depths, with audio |

## Notable components

### `Math.tsx`

`<Math tex={...} />` renders KaTeX. `<RichText text={...} />` handles prose containing
`$inline$` and `$$display$$` by extracting math into slots, rendering the text as markdown,
then substituting rendered KaTeX back in. This is what lets lesson narratives and chat
answers mix prose and equations freely.

### `Starfield.tsx`

Canvas background with real stellar colour temperatures. Respects
`prefers-reduced-motion` — if set, the stars render once and do not animate.

### `AudioPlayer.tsx`

Plays server-generated narration. If the tutor service cannot produce audio (non-macOS
host), it falls back to the browser's `SpeechSynthesis` API with the section's `narration`
text. The feature degrades instead of disappearing.

### `LearnView.tsx`

Hosts the reading-depth control (`plain` / `physics` / `full`), persisted to
`localStorage`. At `physics` and above, every equation gets a collapsible "What each symbol
means" list and a "Why it looks like this" panel.

### `ChatDock.tsx`

Handles the three chat states: browsable topic accordion when there is no key, a small
dismissible hint showing exactly where to add one, and a quiet "answered from the knowledge
base" badge when an AI call fails.

## Theme

Night-sky palette driven by CSS custom properties — `--star-blue`, `--star-cyan`,
`--star-white`, `--star-gold`, `--star-amber`, `--star-red` — chosen from real stellar
colours. Responsive breakpoints at 1200 px and 860 px.

## Commands

```bash
make web            # dev server
npm --prefix web run typecheck
npm --prefix web run build
npm --prefix web run preview
```

## API access

Everything goes through `src/api/client.ts`, which targets the gateway at
`http://localhost:8080/api/v1`. No view calls `fetch` directly, so changing the base URL or
adding auth is a one-file change.
