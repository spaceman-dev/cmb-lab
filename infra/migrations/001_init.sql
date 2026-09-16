-- cmb-lab initial schema
-- Schema-per-service. No cross-schema foreign keys: services talk over HTTP, not SQL.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE SCHEMA IF NOT EXISTS catalog;
CREATE SCHEMA IF NOT EXISTS spectrum;
CREATE SCHEMA IF NOT EXISTS cosmology;
CREATE SCHEMA IF NOT EXISTS anomaly;
CREATE SCHEMA IF NOT EXISTS literature;

-- ============================================================
-- catalog: what data exists and where it came from
-- ============================================================

CREATE TABLE catalog.datasets (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug         TEXT NOT NULL UNIQUE,          -- 'wmap9', 'planck-pr3'
    name         TEXT NOT NULL,
    mission      TEXT NOT NULL,                 -- 'WMAP', 'Planck', 'ACT'
    release      TEXT NOT NULL,                 -- '9-year', 'PR3-2018'
    archive      TEXT NOT NULL,                 -- 'LAMBDA', 'PLA', 'IRSA'
    reference    TEXT,                          -- primary paper bibcode
    description  TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A downloadable file from an archive.
CREATE TABLE catalog.products (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id        UUID NOT NULL REFERENCES catalog.datasets(id) ON DELETE CASCADE,
    slug              TEXT NOT NULL,
    kind              TEXT NOT NULL,            -- map | mask | beam | spectrum | likelihood
    url               TEXT NOT NULL,
    filename          TEXT NOT NULL,
    -- Physical descriptors (nullable: a mask has no frequency)
    frequency_ghz     REAL,
    nside             INTEGER,
    component_method  TEXT,                     -- COMMANDER | NILC | SEVEM | SMICA
    field_names       TEXT[],                   -- e.g. {I_STOKES, Q_STOKES, U_STOKES}
    unit              TEXT,                     -- K_CMB | mK | uK
    coord_system      TEXT DEFAULT 'G',         -- Galactic
    -- Integrity
    size_bytes        BIGINT,
    checksum          TEXT,
    checksum_algo     TEXT DEFAULT 'md5',
    -- Local state
    storage_uri       TEXT,                     -- s3://cmblab/raw/...
    downloaded_at     TIMESTAMPTZ,
    notes             TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (dataset_id, slug)
);

CREATE INDEX idx_products_dataset ON catalog.products(dataset_id);
CREATE INDEX idx_products_kind    ON catalog.products(kind);

-- A cleaned / derived HEALPix map.
CREATE TABLE catalog.map_artifacts (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_product_id  UUID NOT NULL REFERENCES catalog.products(id) ON DELETE CASCADE,
    label              TEXT NOT NULL,
    nside              INTEGER NOT NULL,
    npix               BIGINT NOT NULL,
    unit               TEXT NOT NULL DEFAULT 'uK',
    coord_system       TEXT NOT NULL DEFAULT 'G',
    ops_applied        JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- Validation gate G2 values
    monopole_uk        DOUBLE PRECISION,
    dipole_amp_uk      DOUBLE PRECISION,
    dipole_lon_deg     DOUBLE PRECISION,
    dipole_lat_deg     DOUBLE PRECISION,
    masked_fraction    DOUBLE PRECISION,
    stats              JSONB NOT NULL DEFAULT '{}'::jsonb,
    storage_uri        TEXT NOT NULL,
    preview_uri        TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_artifacts_source ON catalog.map_artifacts(source_product_id);

-- Generic provenance graph: any artifact -> its inputs.
CREATE TABLE catalog.provenance_edges (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_kind   TEXT NOT NULL,    -- map_artifact | spectrum_result | inference_run | anomaly_result
    child_id     UUID NOT NULL,
    parent_kind  TEXT NOT NULL,
    parent_id    UUID NOT NULL,
    relation     TEXT NOT NULL,    -- derived_from | masked_by | beam_corrected_by
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_prov_child  ON catalog.provenance_edges(child_kind, child_id);
CREATE INDEX idx_prov_parent ON catalog.provenance_edges(parent_kind, parent_id);

-- Job lifecycle for every service.
CREATE TABLE catalog.jobs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service       TEXT NOT NULL,        -- ingest | spectrum | cosmology | anomaly
    kind          TEXT NOT NULL,        -- download_product | estimate_spectrum | ...
    state         TEXT NOT NULL DEFAULT 'pending',  -- pending|running|succeeded|failed|cancelled
    progress      REAL NOT NULL DEFAULT 0.0,
    message       TEXT,
    params        JSONB NOT NULL DEFAULT '{}'::jsonb,
    result        JSONB,
    error         TEXT,
    celery_id     TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at    TIMESTAMPTZ,
    finished_at   TIMESTAMPTZ
);

CREATE INDEX idx_jobs_state   ON catalog.jobs(state);
CREATE INDEX idx_jobs_service ON catalog.jobs(service);
CREATE INDEX idx_jobs_created ON catalog.jobs(created_at DESC);

-- ============================================================
-- spectrum: angular power spectrum estimation
-- ============================================================

CREATE TABLE spectrum.spectrum_results (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    map_artifact_id   UUID NOT NULL,
    mask_product_id   UUID,
    beam_product_id   UUID,
    method            TEXT NOT NULL,      -- anafast_fsky | master
    lmax              INTEGER NOT NULL,
    binning           TEXT NOT NULL,      -- linear:30 | log | planck
    f_sky             DOUBLE PRECISION,
    beam_corrected    BOOLEAN NOT NULL DEFAULT false,
    pixwin_corrected  BOOLEAN NOT NULL DEFAULT false,
    -- Validation gate G3
    peak1_ell         INTEGER,
    peak1_dl_uk2      DOUBLE PRECISION,
    -- Gate G4
    chi2_vs_published DOUBLE PRECISION,
    dof               INTEGER,
    storage_uri       TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_spec_map ON spectrum.spectrum_results(map_artifact_id);

-- Binned bandpowers. D_l = l(l+1)C_l / 2pi in uK^2.
CREATE TABLE spectrum.bandpowers (
    id           BIGSERIAL PRIMARY KEY,
    result_id    UUID NOT NULL REFERENCES spectrum.spectrum_results(id) ON DELETE CASCADE,
    ell_min      INTEGER NOT NULL,
    ell_max      INTEGER NOT NULL,
    ell_eff      DOUBLE PRECISION NOT NULL,
    dl_uk2       DOUBLE PRECISION NOT NULL,
    dl_err_uk2   DOUBLE PRECISION
);

CREATE INDEX idx_bandpowers_result ON spectrum.bandpowers(result_id, ell_eff);

-- Published reference spectra, for comparison.
CREATE TABLE spectrum.reference_spectra (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        TEXT NOT NULL UNIQUE,   -- 'planck-2018-TT', 'wmap9-TT'
    mission     TEXT NOT NULL,
    spectrum    TEXT NOT NULL DEFAULT 'TT',
    reference   TEXT,
    storage_uri TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- cosmology: theory + parameter inference
-- ============================================================

CREATE TABLE cosmology.theory_runs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    params      JSONB NOT NULL,         -- {H0, ombh2, omch2, ns, As, tau}
    lmax        INTEGER NOT NULL,
    derived     JSONB,                  -- {omega_m, sigma8, age_gyr, z_star, theta_star}
    storage_uri TEXT,
    cache_key   TEXT UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cosmology.inference_runs (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spectrum_result_id UUID,
    likelihood         TEXT NOT NULL,     -- plik_lite | gaussian_bandpower
    sampler            TEXT NOT NULL DEFAULT 'emcee',
    free_params        TEXT[] NOT NULL,
    n_walkers          INTEGER NOT NULL,
    n_steps            INTEGER NOT NULL,
    burn_in            INTEGER,
    acceptance_frac    DOUBLE PRECISION,
    autocorr_time      DOUBLE PRECISION,
    max_log_like       DOUBLE PRECISION,
    chain_uri          TEXT,
    state              TEXT NOT NULL DEFAULT 'pending',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cosmology.posterior_summaries (
    id           BIGSERIAL PRIMARY KEY,
    run_id       UUID NOT NULL REFERENCES cosmology.inference_runs(id) ON DELETE CASCADE,
    param        TEXT NOT NULL,
    mean         DOUBLE PRECISION NOT NULL,
    std          DOUBLE PRECISION NOT NULL,
    median       DOUBLE PRECISION,
    q16          DOUBLE PRECISION,
    q84          DOUBLE PRECISION,
    UNIQUE (run_id, param)
);

-- ============================================================
-- anomaly: large-angle isotropy statistics
-- ============================================================

CREATE TABLE anomaly.simulation_batches (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    n_sims       INTEGER NOT NULL,
    nside        INTEGER NOT NULL,
    lmax         INTEGER NOT NULL,
    theory_cl_id UUID,
    seed         BIGINT NOT NULL,
    mask_slug    TEXT,
    storage_uri  TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE anomaly.anomaly_results (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    map_artifact_id  UUID NOT NULL,
    batch_id         UUID REFERENCES anomaly.simulation_batches(id) ON DELETE SET NULL,
    statistic        TEXT NOT NULL,   -- quad_oct_alignment | hemispherical_asymmetry
                                      -- cold_spot | low_quadrupole
    observed_value   DOUBLE PRECISION NOT NULL,
    sim_mean         DOUBLE PRECISION,
    sim_std          DOUBLE PRECISION,
    p_value          DOUBLE PRECISION,
    p_value_corrected DOUBLE PRECISION,
    n_sims           INTEGER,
    details          JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_anom_map ON anomaly.anomaly_results(map_artifact_id, statistic);

-- ============================================================
-- literature: published values for the tension dashboard
-- ============================================================

CREATE TABLE literature.papers (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bibcode       TEXT UNIQUE,
    arxiv_id      TEXT,
    doi           TEXT,
    title         TEXT NOT NULL,
    authors       TEXT[],
    year          INTEGER,
    publication   TEXT,
    citation_count INTEGER,
    abstract      TEXT,
    url           TEXT,
    fetched_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE literature.published_values (
    id          BIGSERIAL PRIMARY KEY,
    paper_id    UUID REFERENCES literature.papers(id) ON DELETE CASCADE,
    param       TEXT NOT NULL,        -- H0 | omega_m | sigma8 | ns | tau
    value       DOUBLE PRECISION NOT NULL,
    err_lo      DOUBLE PRECISION,
    err_hi      DOUBLE PRECISION,
    probe       TEXT,                 -- CMB | SNe | BAO | lensing | Cepheid
    dataset_tag TEXT,                 -- 'Planck 2018 TT,TE,EE+lowE+lensing'
    is_primary  BOOLEAN DEFAULT false,
    source      TEXT,                 -- ads | manual | arxiv
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_pubvals_param ON literature.published_values(param);
