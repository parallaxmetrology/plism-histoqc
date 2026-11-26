# Colour-profile rerun (added in v1.1.0, 25 November 2026)

Both scanners embed an ICC colour profile in the file: "AT2" in the AT2 scans, "Segue_v2" in the GT450 scans. HistoQC reads pixels through OpenSlide without applying it. Following the suggestion on [choosehappy/HistoQC#343](https://github.com/choosehappy/HistoQC/issues/343), we reran the paired comparison with one change: `openslide.OpenSlide` is replaced at run time by a subclass whose `read_region` converts each region from the slide's own profile to sRGB (Pillow ImageCms / LittleCMS, perceptual intent, alpha kept). `get_thumbnail` goes through the same call. HistoQC's packaged training and template images are not converted. HistoQC's source, revision, default configuration, seed, shared classifiers, fields and scoring are unchanged.

| | default read (v1.0.0) | profile applied |
|---|---|---|
| fields that switch, of 156 | 52 (47 AT2-only, 5 GT450-only) | 5 (3 AT2-only, 2 GT450-only) |
| admitted on both scans | 4 | 23 |
| excluded on both scans | 100 | 128 |
| fields admitted on AT2 / GT450 | 51 / 9 | 26 / 25 |

With the profile applied, AT2 loses 33 admitted fields and gains 8; GT450 gains 16 and loses none. No mask is empty (in v1.0.0 the GT450 masks of KR and MY were). Most of the scanner disagreement in v1.0.0 therefore comes from reading pixels without the embedded profile. Most of the 156 sites, chosen as tissue locations, stay excluded on both scans under the default configuration.

**Gate.** Before the converted run, the same subclass with the conversion switched off reproduced all 26 final mask hashes in `../final_hashes.csv`, in an environment rebuilt to `../qc_environment.json`.

## Check

With Python 3.10 or newer, NumPy, Pillow and Shapely 2, from the repository root:

    python3 colour-profile/check_colour_profile.py

It checks the plan hash and the gate, then recomputes every field fraction and decision, every section count and the totals for both mask sets from the stored final masks and `../native_fields.json`, and prints `ALL MATCH`. It takes a few seconds and needs no slides or HistoQC install.

## Contents

- `PLAN.md`: written and frozen before any HistoQC run in this rerun (SHA-256 in `PLAN.sha256`, time in `PLAN.frozen_at.txt`). It discloses one prior look, the thumbnail brightness check below.
- `masks/default/`, `masks/profile/`: HistoQC's final `mask_use` PNG for each scan, with a JSON record of mask and slide size, pyramid reads, completed pipeline steps and the PNG's SHA-256. `default` is the gate run (conversion off), `profile` the converted run.
- `results/default/`, `results/profile/`: `field_results.csv` (every field), `slide_results.csv` (per section), `mask_pixels.csv`; `results/default/gate.json`.
- `scripts/`: as run. `run_masks.py` runs HistoQC with the subclass, `score.py` scores a mask folder, `build_labbook.py` builds the lab book. They expect the slides and a HistoQC checkout at local paths; `check_colour_profile.py` is the portable check.
- `brightness/`: `thumbnail_check.py` and its output, median tissue brightness (0 to 255) on 2000-pixel OpenSlide thumbnails, without and with the profile. Without it, AT2 is darker on all 13 sections (median gap 40.5); with it, AT2 is brighter on all 13 (median gap 6.9). This needs the slides.
- `LABBOOK.html`: the rerun's lab book.

## Scope

One rendering intent. Descriptive: it says how field selection changes when the vendor profiles are applied, not which scanner or mask is right, and not what another intent or a calibrated target would do.
