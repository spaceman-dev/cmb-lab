"""HTTP API for the anomaly service."""

from __future__ import annotations

from typing import Any

from cmblab_core.jobs import JobManager
from cmblab_core.service import create_app
from fastapi import Query
from pydantic import BaseModel, Field

from .pipeline import (
    ANOMALY_NSIDE,
    HUMAN_NAMES,
    N_TRIALS,
    UNITS,
    analyse_statistic,
    calibrate,
    load_anomaly_map,
    measure,
    run_full_analysis,
)
from .statistics import STATISTICS

app = create_app(
    service_name="anomaly",
    description="Large-angle isotropy statistics with Monte Carlo significance.",
)

jobs = JobManager(max_workers=1)


class AnalysisRequest(BaseModel):
    dataset: str = "wmap9"
    product: str = "ilc-map"
    mask_product: str | None = "mask-kq75"
    statistic: str | None = Field(default=None, description="None runs all four")
    n_sims: int = Field(default=1000, ge=50, le=20000)
    nside: int = Field(default=ANOMALY_NSIDE, ge=16, le=128)


@app.get("/statistics", tags=["meta"])
async def list_statistics() -> dict[str, Any]:
    return {
        "n_trials_corrected": N_TRIALS,
        "statistics": [
            {
                "id": name,
                "name": HUMAN_NAMES.get(name, name),
                "unit": UNITS.get(name, ""),
                "key": key,
                "anomalous_when": "low" if lower else "high",
            }
            for name, (_, key, lower) in STATISTICS.items()
        ],
        "note": (
            "p-values are reported both raw and Šidák-corrected for the four tests. "
            "Read the corrected value."
        ),
    }


@app.post("/measure", tags=["analysis"])
async def measure_only(request: AnalysisRequest) -> dict[str, Any]:
    """Measure the statistics on the real sky without running simulations. Fast."""
    sky, mask, label = load_anomaly_map(
        request.dataset,
        request.product,
        nside=request.nside,
        mask_product=request.mask_product,
    )

    names = [request.statistic] if request.statistic else list(STATISTICS)
    results = {}
    for name in names:
        if name not in STATISTICS:
            raise KeyError(f"Unknown statistic {name!r}")
        results[name] = {
            "name": HUMAN_NAMES.get(name, name),
            "unit": UNITS.get(name, ""),
            "values": measure(sky, name, mask),
        }

    return {
        "map": label,
        "nside": request.nside,
        "results": results,
        "note": "No significance yet — run /jobs to build the Monte Carlo null distribution.",
    }


@app.post("/jobs", tags=["analysis"])
async def start_analysis(request: AnalysisRequest) -> dict[str, Any]:
    """Launch the full Monte Carlo analysis as a background job."""

    def task(progress):
        if request.statistic:
            result = analyse_statistic(
                request.statistic,
                dataset=request.dataset,
                product=request.product,
                mask_product=request.mask_product,
                n_sims=request.n_sims,
                nside=request.nside,
                progress=progress,
            )
            return {
                "statistics": {
                    request.statistic: {
                        **result.public(),
                        "human_name": HUMAN_NAMES.get(request.statistic, request.statistic),
                        "unit": UNITS.get(request.statistic, ""),
                    }
                }
            }

        report = run_full_analysis(
            dataset=request.dataset,
            product=request.product,
            mask_product=request.mask_product,
            n_sims=request.n_sims,
            nside=request.nside,
            progress=progress,
        )
        return report.public()

    job_id = jobs.submit("anomaly", task, params=request.model_dump())
    n_statistics = 1 if request.statistic else len(STATISTICS)
    return {
        "job_id": job_id,
        "state": "pending",
        "estimated_seconds": round(request.n_sims * n_statistics * 0.02),
        "poll": f"/jobs/{job_id}",
    }


@app.get("/jobs/{job_id}", tags=["analysis"])
async def job_status(job_id: str) -> dict[str, Any]:
    record = jobs.get(job_id)
    payload = record.public()
    if record.state == "succeeded":
        payload["result"] = record.result
    return payload


@app.get("/jobs", tags=["analysis"])
async def list_jobs(limit: int = 20) -> dict[str, Any]:
    return {"jobs": [r.public() for r in jobs.list(limit=limit)]}


@app.post("/calibrate", tags=["validation"])
async def start_calibration(
    statistic: str = Query(default="low_quadrupole"),
    n_checks: int = Query(default=24, ge=8, le=200),
    n_sims: int = Query(default=300, ge=100, le=5000),
) -> dict[str, Any]:
    """Gate G6: verify p-values come out uniform on skies that really are isotropic."""
    if statistic not in STATISTICS:
        raise KeyError(f"Unknown statistic {statistic!r}")

    def task(progress):
        return calibrate(statistic, n_checks=n_checks, n_sims=n_sims, progress=progress)

    job_id = jobs.submit(
        "calibration",
        task,
        params={"statistic": statistic, "n_checks": n_checks, "n_sims": n_sims},
    )
    return {"job_id": job_id, "state": "pending", "poll": f"/jobs/{job_id}"}
