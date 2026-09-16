/** Thin fetch wrapper for the gateway API. */

import type {
  ChatCapabilities,
  ChatReply,
  ChatTopic,
  Curriculum,
  CrossSpectrumRequest,
  ExperimentRun,
  ExperimentSummary,
  GatewayHealth,
  H0Measurement,
  JobStatus,
  Knob,
  Lesson,
  MapEntry,
  ParameterMeta,
  PlaygroundSpectrum,
  PlaygroundTheory,
  ProjectionsResponse,
  ReferenceSpectrum,
  SkyStats,
  SpectrumResult,
  SphereData,
  TheoryResult,
} from "./types";

const BASE = "/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    let detail = response.statusText;
    let code: string | undefined;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
      code = body.error;
    } catch {
      // Non-JSON error body; keep the status text.
    }
    throw new ApiError(detail, response.status, code);
  }

  return response.json() as Promise<T>;
}

const post = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });

/** Poll a job until it reaches a terminal state. */
export async function pollJob(
  path: string,
  onProgress: (job: JobStatus) => void,
  { intervalMs = 900, timeoutMs = 20 * 60 * 1000 } = {},
): Promise<JobStatus> {
  const started = Date.now();

  for (;;) {
    const job = await request<JobStatus>(path);
    onProgress(job);

    if (["succeeded", "failed", "cancelled"].includes(job.state)) return job;
    if (Date.now() - started > timeoutMs) {
      throw new ApiError("Job timed out", 504, "timeout");
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}

export const api = {
  // ── system ────────────────────────────────────────────────
  health: () => request<GatewayHealth>("/health"),

  // ── spectrum ──────────────────────────────────────────────
  maps: () => request<{ maps: MapEntry[] }>("/maps"),
  crossSpectrum: (body: CrossSpectrumRequest) =>
    post<SpectrumResult>("/spectra/cross", body),
  reference: (slug: string, ellMax = 1200) =>
    request<ReferenceSpectrum>(`/references/${slug}?ell_max=${ellMax}`),

  // ── cosmology (G5) ────────────────────────────────────────
  parameterMeta: () => request<ParameterMeta>("/parameters"),
  theory: (body: Record<string, number | boolean>) =>
    post<TheoryResult>("/theory", body),
  startInference: (body: Record<string, unknown>) =>
    post<{ job_id: string; estimated_seconds: number }>("/inference/jobs", body),
  inferenceJob: (id: string) => request<JobStatus>(`/inference/jobs/${id}`),
  hubbleTension: () =>
    request<{ measurements: H0Measurement[] }>("/tension/H0"),

  // ── anomaly (G6) ──────────────────────────────────────────
  anomalyStatistics: () =>
    request<{ statistics: { id: string; name: string; unit: string }[] }>(
      "/anomaly/statistics",
    ),
  measureAnomalies: (body: Record<string, unknown>) =>
    post<{ map: string; results: Record<string, { name: string; unit: string; values: Record<string, number> }> }>(
      "/anomaly/measure",
      body,
    ),
  startAnomalyJob: (body: Record<string, unknown>) =>
    post<{ job_id: string; estimated_seconds: number }>("/anomaly/jobs", body),
  anomalyJob: (id: string) => request<JobStatus>(`/anomaly/jobs/${id}`),

  // ── skymap ────────────────────────────────────────────────
  projections: () => request<ProjectionsResponse>("/skymap/projections"),
  renderUrl: (
    dataset: string,
    product: string,
    params: Record<string, string | number | boolean>,
  ) => {
    const query = new URLSearchParams(
      Object.entries(params).map(([k, v]) => [k, String(v)]),
    );
    return `${BASE}/skymap/render/${dataset}/${product}.png?${query}`;
  },
  presetUrl: (dataset: string, product: string, preset: string, projection = "mollweide") =>
    `${BASE}/skymap/preset/${dataset}/${product}/${preset}.png?projection=${projection}`,
  sphere: (dataset: string, product: string, ellMin = 2, ellMax = 767) =>
    request<SphereData>(
      `/skymap/sphere/${dataset}/${product}?ell_min=${ellMin}&ell_max=${ellMax}&n_lon=240&n_lat=120`,
    ),
  skyStats: (dataset: string, product: string, ellMin = 2, ellMax = 767) =>
    request<SkyStats>(
      `/skymap/stats/${dataset}/${product}?ell_min=${ellMin}&ell_max=${ellMax}`,
    ),

  // ── tutor ─────────────────────────────────────────────────
  curriculum: () => request<Curriculum>("/tutor/curriculum"),
  lesson: (id: string) => request<Lesson>(`/tutor/lessons/${id}`),
  audioUrl: (lessonId: string, sectionId: string) =>
    `${BASE}/tutor/audio/${lessonId}/${sectionId}.m4a`,

  // ── chat ──────────────────────────────────────────────────
  chatCapabilities: () => request<ChatCapabilities>("/chat/capabilities"),
  chatTopics: () =>
    request<{ topics: ChatTopic[]; n_questions: number }>("/chat/topics"),
  chat: (message: string, sessionId?: string, mode: "auto" | "always" | "never" = "auto") =>
    post<ChatReply>("/chat/chat", { message, session_id: sessionId, mode }),

  // ── playground ────────────────────────────────────────────
  knobs: () => request<{ spectrum: Knob[]; theory: Knob[] }>("/playground/knobs"),
  experiments: () =>
    request<{ experiments: ExperimentSummary[] }>("/playground/experiments"),
  runExperiment: (id: string) =>
    post<ExperimentRun>(`/playground/experiments/${id}/run`, {}),
  sandboxSpectrum: (config: Record<string, unknown>) =>
    post<PlaygroundSpectrum>("/playground/spectrum", config),
  sandboxTheory: (config: Record<string, unknown>) =>
    post<PlaygroundTheory>("/playground/theory", config),
};
