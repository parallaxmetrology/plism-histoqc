# Plan: paired HistoQC rerun with embedded ICC profiles applied

Written and frozen 24 November 2026, before any HistoQC run in this folder. Prompted by the HistoQC owner's suggestion on choosehappy/HistoQC#343.

## Question

The 26 PLISM scans (13 sections, Aperio AT2 and Aperio GT450) each embed an ICC profile ("AT2" in the AT2 files, "Segue_v2" in the GT450 files). Neither HistoQC nor OpenSlide applies it. If every pixel HistoQC reads is first converted from the scan's own profile to sRGB, how many of the same 156 registered fields switch admission between the two scanners? The original study, with no profile applied, found 52 (47 AT2-only, 5 GT450-only).

## Prior look (disclosed)

Before this plan, 2000-pixel thumbnails of all 26 scans were converted to sRGB with their own profiles (perceptual intent) and the median tissue luma compared. The median AT2 to GT450 gap across sections fell from 40.5 to 6.9 (0 to 255). No mask was computed. No direction or size of change in field switches is predicted.

## Everything held fixed

Same as the frozen original design (`PLISM_01/design.txt`, 12 November 2026), unchanged and read in place:

- Sources: the 26 scans in `PLISM_01/sources/`, read only at reduced levels (a level-0 read stops the run).
- HistoQC at upstream revision f35e518 (`HISTOQC_PAIRED_SELECTION_20261111/upstream/`, read in place), default `config.ini`, one process, one shared set of classifier models across all scans in filename order, seed 20261111, `LOKY_MAX_CPU_COUNT=4`, `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MPLBACKEND=Agg`.
- Environment rebuilt to `PLISM_01/qc_environment.json`: Python 3.10.22, numpy 1.23.5, scipy 1.10.0, scikit-learn 1.2.1, scikit-image 0.19.3, Pillow 9.4.0, openslide-python 1.4.6, OpenSlide 4.0.1, tifffile 2025.5.10, joblib 1.6.0, matplotlib 3.7.1.
- Fields: the 156 native pixel-centre polygons in `PLISM_01/maps/`. Scoring: exact polygon overlap with positive pixels of the final `mask_use`, admitted at a fraction of 0.50 or more; the original `score.py` logic, unchanged except for input and output folders.

## The one change

`OpenSlide.read_region` is wrapped at run time (HistoQC source untouched). Each region is converted from the slide's embedded profile to sRGB with Pillow ImageCms (LittleCMS), perceptual rendering intent, applied to the RGB channels; alpha is kept. OpenSlide's `get_thumbnail` goes through the same method. HistoQC's packaged training and template images are not converted.

## Gate (before any ICC run)

Run the same wrapper with the conversion switched off. All 26 final mask PNGs must match the SHA-256 in `final_hashes.csv` of the original study. If any differs, the rebuilt environment is not the original one: stop and report, with no ICC run.

## Readings

1. Primary: fields that switch, of 156, with AT2-only and GT450-only counts; per-section counts; mean section switch fraction. Reported beside the original 52.
2. Secondary: whole-slide positive mask pixels, GT450 over AT2, per section (original median 0.065); any empty mask.
3. Secondary: which fields change decision between the original and the ICC run, per scanner.

## Scope

Same array, same scanners, same pipeline and settings; only the colour conversion changes. Descriptive. It says whether applying the vendor profiles changes field selection here, not which scanner or mask is right, and not whether other profile handling (another intent, or a calibrated target) would do differently. One rendering intent is run.
