/** Wire types for the cmb-lab API, mirroring the gateway's JSON contract. */

// ─────────────────────────────────────────────────────────── spectrum

export interface Bandpower {
  ell_min: number;
  ell_max: number;
  ell_eff: number;
  dl_uk2: number;
  dl_err_uk2: number | null;
}

export interface GateG3 {
  name: string;
  passed: boolean;
  detail: string;
  measured: { ell: number; dl_uk2: number };
  expected: { ell: number; dl_uk2: number };
}

export interface Comparison {
  chi2: number;
  dof: number;
  chi2_per_dof: number;
  n_compared: number;
  passed: boolean;
}

export interface PointSource {
  amplitude_uk2_sr: number;
  amplitude_err: number;
  method: string;
  circular: boolean;
  summary: string;
}

export interface SpectrumResult {
  id: string;
  cached: boolean;
  map_label: string;
  estimator: "cross" | "auto";
  f_sky: number;
  lmax: number;
  reliable_lmax: number;
  beam_lmax: number;
  snr_lmax: number | null;
  beam_corrected: boolean;
  pixwin_corrected: boolean;
  beams: string[];
  point_source: PointSource | null;
  gates: {
    G3: GateG3;
    G4: { name: string; comparisons: Record<string, Comparison> };
  };
  bandpowers: Bandpower[];
}

export interface ReferenceSpectrum {
  slug: string;
  mission: string;
  reference: string;
  ell: number[];
  dl_uk2: number[];
  err_lo: number[];
  err_hi: number[];
  best_fit_dl_uk2?: number[];
}

export interface MapEntry {
  dataset: string;
  product: string;
  nside: number;
  npix: number;
  unit: string;
  rms: number | null;
  has_preview: boolean;
}

export interface GatewayHealth {
  status: string;
  service: string;
  upstreams: { service: string; status: string; url: string }[];
  cache: { hits: number; misses: number; size: number };
}

export interface CrossSpectrumRequest {
  product_a?: string;
  product_b?: string;
  mask_dataset?: string | null;
  mask_product?: string | null;
  lmax?: number;
  binning?: string;
  subtract_point_sources?: boolean;
}

// ─────────────────────────────────────────────────────────── cosmology

export interface ParamSummary {
  name: string;
  label: string;
  mean: number;
  std: number;
  median: number;
  q16: number;
  q84: number;
}

export interface ParamComparison {
  name: string;
  label: string;
  ours: number;
  ours_err: number;
  published: number;
  published_err: number;
  tension_sigma: number;
  consistent: boolean;
  source: string;
}

export interface InferenceResult {
  spectrum: string;
  free_params: string[];
  n_walkers: number;
  n_steps: number;
  n_samples: number;
  acceptance_fraction: number;
  autocorr_time: number | null;
  best_fit: Record<string, number>;
  best_chi2: number;
  dof: number;
  chi2_per_dof: number;
  posterior: Record<string, ParamSummary>;
  derived: Record<string, ParamSummary>;
  gates: {
    G5: {
      name: string;
      passed: boolean;
      detail: string;
      comparisons: Record<string, ParamComparison>;
    };
  };
}

export interface JobStatus {
  id: string;
  kind: string;
  state: "pending" | "running" | "succeeded" | "failed" | "cancelled";
  progress: number;
  message: string;
  error: string | null;
  elapsed_s: number;
  result?: unknown;
}

export interface TheoryResult {
  params: Record<string, number>;
  derived: Record<string, number | null>;
  first_peak: { ell: number; dl_uk2: number };
  ell: number[];
  dl_tt: number[];
  dl_ee: number[];
  dl_te: number[];
}

export interface H0Measurement {
  key: string;
  value: number;
  err: number;
  source: string;
  probe: string;
  tension_vs_planck_sigma: number;
}

export interface ParameterMeta {
  bounds: Record<string, { min: number; max: number }>;
  labels: Record<string, string>;
  planck2018: Record<string, { value: number; err: number; source: string }>;
}

// ─────────────────────────────────────────────────────────── anomaly

export interface AnomalyStat {
  statistic: string;
  human_name: string;
  unit: string;
  observed: number;
  details: Record<string, number>;
  p_value: number;
  p_value_corrected: number;
  sigma_equivalent: number;
  n_more_extreme: number;
  n_sims: number;
  lower_tail: boolean;
  n_trials_corrected: number;
  null: {
    mean: number;
    std: number;
    percentiles: Record<string, number>;
    histogram: { centres: number[]; counts: number[] };
    failures: number;
  };
}

export interface AnomalyReport {
  map: string;
  nside: number;
  n_sims: number;
  n_trials_corrected: number;
  statistics: Record<string, AnomalyStat>;
  gates: {
    G6: {
      name: string;
      passed: boolean;
      detail: string;
      calibration: {
        statistic: string;
        n_checks: number;
        mean_p_value: number;
        fraction_below_0p05: number;
        p_values: number[];
        passed: boolean;
        detail: string;
      };
    };
  };
}

// ─────────────────────────────────────────────────────────── skymap

export interface Projection {
  id: string;
  label: string;
  description: string;
  supports_direction: boolean;
}

export interface Preset {
  id: string;
  label: string;
  ell_min: number;
  ell_max: number;
  explain: string;
}

export interface ProjectionsResponse {
  projections: Projection[];
  colormaps: string[];
  presets: Preset[];
}

export interface SphereData {
  x: number[][];
  y: number[][];
  z: number[][];
  values: (number | null)[][];
  vmin: number;
  vmax: number;
}

export interface SkyStats {
  mean_uk: number;
  rms_uk: number;
  skewness: number;
  kurtosis: number;
  n_pixels: number;
  histogram: { centres: number[]; density: number[]; gaussian: number[] };
}

// ─────────────────────────────────────────────────────────── tutor

export interface Variable {
  symbol: string;
  meaning: string;
  units: string;
}

export interface Equation {
  latex: string;
  label: string;
  explain: string;
  variables: Variable[];
  intuition: string;
}

export interface DerivationStep {
  n: number;
  latex: string;
  reason: string;
}

export interface LiveValue {
  label: string;
  value: number | string | string[] | null;
  display: string;
  context?: string;
  source?: string;
}

export interface LessonSection {
  id: string;
  title: string;
  narrative: string;
  narration: string;
  plain: string;
  equations: Equation[];
  derivation: DerivationStep[];
  live: string[];
  live_values: Record<string, LiveValue>;
  audio: { available: boolean; estimated_seconds: number; url: string };
}

export interface Lesson {
  id: string;
  title: string;
  subtitle: string;
  duration_min: number;
  prerequisites: string[];
  sections: LessonSection[];
  navigation: {
    previous: string | null;
    next: string | null;
    position: number;
    total: number;
  };
}

export interface LessonSummary {
  id: string;
  title: string;
  subtitle: string;
  duration_min: number;
  prerequisites: string[];
  n_sections: number;
  sections: { id: string; title: string }[];
}

export interface Curriculum {
  order: string[];
  total_minutes: number;
  lessons: LessonSummary[];
  audio: {
    available: boolean;
    voices: string[];
    default_voice: string;
    fallback: string;
  };
}

// ─────────────────────────────────────────────────────────── chat

export interface ChatCitation {
  kind: string;
  label: string;
  ref: string;
  detail: string;
}

export interface ChatReply {
  text: string;
  intent: string;
  confidence: number;
  citations: ChatCitation[];
  suggestions: string[];
  data: Record<string, unknown>;
  stage: 1 | 2;
  session_id: string;
  llm_configured: boolean;
  model?: string;
  llm_error?: string;
  llm_fallback?: boolean;
}

export interface ChatTopic {
  id: string;
  label: string;
  blurb: string;
  icon: string;
  questions: string[];
}

export interface LlmSetup {
  env_var: string;
  file: string;
  get_key_url: string;
  restart_command: string;
}

export interface ChatCapabilities {
  stage: 1 | 2;
  llm: {
    available: boolean;
    provider: string | null;
    model: string | null;
    note: string;
    setup: LlmSetup;
  };
  retrieval: { available: boolean; sources: string[]; n_questions: number };
  topics: ChatTopic[];
  suggestions: string[];
}

// ─────────────────────────────────────────────────────────── playground

export interface Knob {
  id: string;
  label: string;
  kind: "select" | "number" | "boolean";
  default: unknown;
  options: unknown[];
  min: number | null;
  max: number | null;
  step: number | null;
  physics: string;
  watch_for: string;
}

export interface ExperimentSummary {
  id: string;
  title: string;
  question: string;
  difficulty: string;
  kind: string;
  lesson: string | null;
}

export interface PlaygroundSpectrum {
  label: string;
  is_auto_spectrum: boolean;
  f_sky: number;
  usable_lmax: number;
  peak1_ell: number;
  peak1_dl: number;
  gate_g3_passed: boolean;
  chi2_per_dof: number | null;
  gate_g4_passed: boolean | null;
  bandpowers: { ell: number; dl: number; err: number | null }[];
}

export interface PlaygroundTheory {
  peak1_ell: number;
  peak1_dl: number;
  ell: number[];
  dl_tt: number[];
  derived: Record<string, number | null>;
}

export interface ExperimentRun {
  experiment: {
    id: string;
    title: string;
    question: string;
    expect: string;
    difficulty: string;
    lesson?: string;
  };
  kind: "spectrum" | "theory";
  baseline: PlaygroundSpectrum & PlaygroundTheory & { label?: string };
  variant: PlaygroundSpectrum & PlaygroundTheory & { label?: string };
  delta: Record<string, number | null>;
}
