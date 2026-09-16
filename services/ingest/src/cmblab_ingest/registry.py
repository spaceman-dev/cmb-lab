"""Registry of known archive products, with URLs verified against the live archives.

This is deliberately code rather than database seed data: it is version-controlled,
reviewable in a diff, and testable. The catalog service loads it on first start.

See docs/data-sources.md for how to regenerate these URLs if an archive reorganises.
"""

from __future__ import annotations

from dataclasses import dataclass, field

LAMBDA_DR5 = "https://lambda.gsfc.nasa.gov/data/map/dr5"
PLA_MAP = "https://pla.esac.esa.int/pla/aio/product-action?MAP.MAP_ID="
PLA_COSMO = "https://pla.esac.esa.int/pla/aio/product-action?COSMOLOGY.FILE_ID="


@dataclass(frozen=True, slots=True)
class ProductSpec:
    slug: str
    kind: str  # map | mask | beam | spectrum
    url: str
    filename: str
    unit: str | None = None
    nside: int | None = None
    frequency_ghz: float | None = None
    component_method: str | None = None
    approx_mb: float | None = None
    #: True when the archive already removed monopole+dipole. Changes what gate G2 asserts.
    dipole_removed: bool = False
    #: Slug of the beam product describing this map's resolution, if one exists.
    beam_product: str | None = None
    #: Effective Gaussian beam FWHM, for maps with no tabulated transfer function.
    beam_fwhm_arcmin: float | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    slug: str
    name: str
    mission: str
    release: str
    archive: str
    reference: str
    description: str
    products: tuple[ProductSpec, ...] = field(default_factory=tuple)


# ----------------------------------------------------------------------------------
# WMAP 9-year (DR5) — NASA LAMBDA
# ----------------------------------------------------------------------------------

WMAP9 = DatasetSpec(
    slug="wmap9",
    name="WMAP Nine-Year Data Release",
    mission="WMAP",
    release="DR5 / 9-year",
    archive="LAMBDA",
    reference="2013ApJS..208...19H",
    description=(
        "Nine years of WMAP observations at Nside=512 across five frequency bands. "
        "Small enough for a fast development loop while being real flight data."
    ),
    products=(
        ProductSpec(
            slug="ilc-map",
            kind="map",
            url=f"{LAMBDA_DR5}/dfp/ilc/wmap_ilc_9yr_v5.fits",
            filename="wmap_ilc_9yr_v5.fits",
            unit="mK_CMB",
            nside=512,
            component_method="ILC",
            approx_mb=24.0,
            dipole_removed=True,
            beam_fwhm_arcmin=60.0,
            notes=(
                "Internal Linear Combination foreground-cleaned CMB map. Great for "
                "visualisation and low-l work. NOT suitable for power spectra above "
                "l~250: its auto-spectrum carries a noise bias and its effective beam is "
                "not a clean Gaussian. Use the DA maps with cross-spectra instead."
            ),
        ),
        ProductSpec(
            slug="mask-kq75",
            kind="mask",
            url=(
                f"{LAMBDA_DR5}/ancillary/masks/wmap_temperature_kq75_analysis_mask_r9_9yr_v5.fits"
            ),
            filename="wmap_temperature_kq75_analysis_mask_r9_9yr_v5.fits",
            nside=512,
            approx_mb=24.0,
            notes="Conservative temperature analysis mask, f_sky about 0.71. 1=keep, 0=reject.",
        ),
        ProductSpec(
            slug="mask-kq85",
            kind="mask",
            url=(
                f"{LAMBDA_DR5}/ancillary/masks/wmap_temperature_kq85_analysis_mask_r9_9yr_v5.fits"
            ),
            filename="wmap_temperature_kq85_analysis_mask_r9_9yr_v5.fits",
            nside=512,
            approx_mb=24.0,
            notes="Permissive mask, f_sky about 0.82. More sky, more Galactic residual.",
        ),
        ProductSpec(
            slug="tt-spectrum",
            kind="spectrum",
            url=f"{LAMBDA_DR5}/dcp/spectra/wmap_tt_spectrum_9yr_v5.txt",
            filename="wmap_tt_spectrum_9yr_v5.txt",
            approx_mb=0.086,
            notes="WMAP's own published unbinned TT spectrum. Comparison target for gate G4.",
        ),
        ProductSpec(
            slug="tt-spectrum-binned",
            kind="spectrum",
            url=f"{LAMBDA_DR5}/dcp/spectra/wmap_binned_tt_spectrum_9yr_v5.txt",
            filename="wmap_binned_tt_spectrum_9yr_v5.txt",
            approx_mb=0.004,
            notes="Binned version, as plotted in the WMAP papers.",
        ),
        *(
            ProductSpec(
                slug=f"band-{band.lower()}",
                kind="map",
                url=f"{LAMBDA_DR5}/skymaps/9yr/raw/wmap_band_imap_r9_9yr_{band}_v5.fits",
                filename=f"wmap_band_imap_r9_9yr_{band}_v5.fits",
                unit="mK_CMB",
                nside=512,
                frequency_ghz=freq,
                approx_mb=24.0,
                notes=f"Raw {band}-band temperature map at {freq} GHz.",
            )
            for band, freq in (("K", 22.8), ("Ka", 33.0), ("Q", 40.7), ("V", 60.8), ("W", 93.5))
        ),
        *(
            ProductSpec(
                slug=f"beam-{da.lower()}",
                kind="beam",
                url=f"{LAMBDA_DR5}/ancillary/beams/wmap_ampl_bl_{da}_9yr_v5p1.txt",
                filename=f"wmap_ampl_bl_{da}_9yr_v5p1.txt",
                approx_mb=0.04,
                notes=f"Beam transfer function b_l for differencing assembly {da}.",
            )
            for da in ("K1", "Ka1", "Q1", "Q2", "V1", "V2", "W1", "W2", "W3", "W4")
        ),
        # Foreground-reduced per-differencing-assembly maps. These are the right input for
        # power spectrum estimation: each DA has an independent noise realisation, so a
        # cross-spectrum between two of them is unbiased by noise, and each has an exact
        # tabulated beam transfer function rather than a Gaussian approximation.
        *(
            ProductSpec(
                slug=f"da-{da.lower()}",
                kind="map",
                url=(f"{LAMBDA_DR5}/skymaps/9yr/forered/wmap_forered_imap_r9_9yr_{da}_v5.fits"),
                filename=f"wmap_forered_imap_r9_9yr_{da}_v5.fits",
                unit="mK_CMB",
                nside=512,
                frequency_ghz=freq,
                approx_mb=24.0,
                dipole_removed=True,
                beam_product=f"beam-{da.lower()}",
                notes=f"Foreground-reduced {da} temperature map at {freq} GHz.",
            )
            for da, freq in (
                ("Q1", 40.7),
                ("Q2", 40.7),
                ("V1", 60.8),
                ("V2", 60.8),
                ("W1", 93.5),
                ("W2", 93.5),
                ("W3", 93.5),
                ("W4", 93.5),
            )
        ),
    ),
)


# ----------------------------------------------------------------------------------
# Planck PR3 (2018) — ESA Planck Legacy Archive
# ----------------------------------------------------------------------------------

PLANCK_PR3 = DatasetSpec(
    slug="planck-pr3",
    name="Planck 2018 Data Release (PR3)",
    mission="Planck",
    release="PR3 / 2018",
    archive="PLA",
    reference="2020A&A...641A...6P",
    description=(
        "Planck full-mission maps at Nside=2048. Four independent component-separation "
        "pipelines on identical data, which doubles as a systematics cross-check."
    ),
    products=(
        *(
            ProductSpec(
                slug=f"cmb-{method.lower()}",
                kind="map",
                url=f"{PLA_MAP}COM_CMB_IQU-{method.lower()}_2048_R3.00_full.fits",
                filename=f"COM_CMB_IQU-{method.lower()}_2048_R3.00_full.fits",
                unit="K_CMB",
                nside=2048,
                component_method=method,
                approx_mb=600.0,
                dipole_removed=True,
                notes=f"{method} component-separated CMB map. Field 0=I, 1=Q, 2=U.",
            )
            for method in ("COMMANDER", "NILC", "SEVEM", "SMICA")
        ),
        ProductSpec(
            slug="common-mask-int",
            kind="mask",
            url=f"{PLA_MAP}COM_Mask_CMB-common-Mask-Int_2048_R3.00.fits",
            filename="COM_Mask_CMB-common-Mask-Int_2048_R3.00.fits",
            nside=2048,
            approx_mb=50.0,
            notes="Common intensity confidence mask used across all four methods.",
        ),
        ProductSpec(
            slug="tt-spectrum-binned",
            kind="spectrum",
            url=f"{PLA_COSMO}COM_PowerSpect_CMB-TT-binned_R3.01.txt",
            filename="COM_PowerSpect_CMB-TT-binned_R3.01.txt",
            approx_mb=0.006,
            notes="Binned TT spectrum. Columns: ell, D_ell, -dD_ell, +dD_ell in uK^2.",
        ),
        ProductSpec(
            slug="tt-spectrum-full",
            kind="spectrum",
            url=f"{PLA_COSMO}COM_PowerSpect_CMB-TT-full_R3.01.txt",
            filename="COM_PowerSpect_CMB-TT-full_R3.01.txt",
            approx_mb=0.1,
            notes="Unbinned TT spectrum, ell=2..2508.",
        ),
    ),
)


DATASETS: tuple[DatasetSpec, ...] = (WMAP9, PLANCK_PR3)

#: The minimum set needed to produce a real power spectrum. About 170 MB total.
#: V1 and V2 are the cleanest CMB channels and have independent noise, so their
#: cross-spectrum is the standard route to an unbiased estimate.
BOOTSTRAP_PRODUCTS: tuple[tuple[str, str], ...] = (
    ("wmap9", "ilc-map"),
    ("wmap9", "mask-kq75"),
    ("wmap9", "da-v1"),
    ("wmap9", "da-v2"),
    ("wmap9", "beam-v1"),
    ("wmap9", "beam-v2"),
    ("wmap9", "tt-spectrum-binned"),
    ("planck-pr3", "tt-spectrum-binned"),
)


def get_dataset(slug: str) -> DatasetSpec:
    for dataset in DATASETS:
        if dataset.slug == slug:
            return dataset
    raise KeyError(f"Unknown dataset {slug!r}. Known: {[d.slug for d in DATASETS]}")


def get_product(dataset_slug: str, product_slug: str) -> ProductSpec:
    dataset = get_dataset(dataset_slug)
    for product in dataset.products:
        if product.slug == product_slug:
            return product
    raise KeyError(
        f"Unknown product {product_slug!r} in {dataset_slug!r}. "
        f"Known: {[p.slug for p in dataset.products]}"
    )


def iter_products() -> list[tuple[DatasetSpec, ProductSpec]]:
    return [(dataset, product) for dataset in DATASETS for product in dataset.products]
