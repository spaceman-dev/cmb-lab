# catalog

**Path:** `services/catalog/` · **Port:** 8001

Answers "what data do I actually have on disk?" Everything else assumes data exists;
catalog is the service that knows.

## Responsibility

Scans `data/raw/` and `data/clean/`, reports what is present, and serves basic statistics
and preview images for each map. It is read-only — it never downloads or modifies anything.
That belongs to [ingest](ingest.md).

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/datasets` | All known datasets and how much of each is downloaded |
| GET | `/datasets/{dataset_slug}/products` | Products in one dataset, with local availability |
| GET | `/datasets/{dataset_slug}/products/{product_slug}` | Detail for one product, including FITS header info |
| GET | `/maps` | Every cleaned map available for analysis |
| GET | `/maps/{dataset}/{product}/stats` | N_side, pixel count, mean, RMS, min/max, fraction masked |
| GET | `/maps/{dataset}/{product}/preview.png` | Small Mollweide thumbnail |

Via the gateway these are under `/api/v1/catalog/`.

## How the frontend uses it

`/maps` populates every map selector in the app — the Spectrum, Sky Map, and Playground
tabs all ask catalog which maps exist rather than hard-coding names. Adding a new product
to the archive therefore makes it appear in the UI without any frontend change.

## Notes

- Availability is computed from the filesystem on each request. There is no database and no
  cache to invalidate, which means a file dropped into `data/clean/` shows up immediately.
- `stats` reads the map, so it is slower than the other endpoints. The gateway caches it.
- If a product is registered but not downloaded, it is still listed, with
  `available: false`. The UI uses this to prompt `make data-bootstrap`.
