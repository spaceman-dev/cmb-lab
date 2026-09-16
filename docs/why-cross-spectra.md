
---

## 7. Why the ILC map is the wrong input for a power spectrum

This is the single most useful thing we learned building the pipeline, so it is worth
stating plainly.

The WMAP Internal Linear Combination map is the obvious first choice: it is a single,
foreground-cleaned, full-sky CMB map. Using it produces a spectrum that **rises
monotonically** instead of showing acoustic peaks. Two independent reasons:

**1. Noise bias.** An auto-spectrum measures signal *plus* the map's own noise:

```
C_l^measured  =  C_l^signal  +  N_l
```

Deconvolving the beam divides everything by b_l², and since b_l falls exponentially while
N_l does not, the noise term explodes. Our measured spectrum was 26× the truth at ℓ = 350.

**2. A non-Gaussian effective beam.** The ILC is a weighted combination of five frequency
bands with five different beams, then smoothed. Assuming a 1° Gaussian over-corrects:
fitting the effective transfer function empirically gave ≈ 51′, not 60′.

### The fix, which is what the WMAP team actually does

Use two detectors that observed the same sky with **independent** noise, and correlate
them:

```
<a_lm^V1 a_lm^V2*>  =  C_l b_l^V1 b_l^V2  +  <n^V1 n^V2*>
                                              ~~~~~~~~~~~~
                                              zero: uncorrelated
```

The noise term vanishes by construction. No noise model, no instrument simulation. Combine
that with the archive's **measured** per-detector beam transfer functions
(`wmap_ampl_bl_*.txt`) and the spectrum snaps into shape:

| Input | First peak | χ²/dof vs published |
|---|---|---|
| ILC auto-spectrum, 1° Gaussian beam | ℓ = 343 (wrong) | 1669 |
| V1 × V2 cross-spectrum, measured beams | ℓ = 220 | 32 |
| … plus point source subtraction | ℓ = 220 | **1.02** |

### The last 3%: unresolved point sources

Cross-spectra cancel *noise*, not *sky*. Faint extragalactic radio sources below the
detection threshold form a Poisson field with a flat C_l, which becomes ℓ²-growing in D_l.
That is exactly the residual shape we measured — and subtracting it is the final step that
brings χ²/dof to 1.

The bonus: because V band (60.8 GHz) and W band (93.5 GHz) are independent instruments, you
can run the whole analysis twice as a free systematics check. We get ℓ = 220 and ℓ = 218.
