# Paired HistoQC field inclusion on PLISM

Open **note.html** for results, mask examples, study limits, and attribution. The frozen primary endpoint is the fraction of 12 fields per section switching inclusion on two scans; each of the 13 related array sections has equal weight. The exploratory step trace follows the original 156 mapped fields and the frozen 50% field-area cutoff.

## Colour-profile rerun (v1.1.0, 25 November 2026)

Both scanners embed an ICC colour profile in the file, and HistoQC reads pixels without applying it. With each scan's profile applied before HistoQC reads it, and nothing else changed, 5 of the 156 fields switch instead of 52, and 23 are admitted on both scans instead of 4. The masks, results, frozen plan, gate and a portable check are in [colour-profile/](colour-profile/README.md). The v1.0.0 files are unchanged apart from this README and SHA256SUMS.

## Reproduce the tables

With Python 3.10 or newer, from the unpacked directory:

    python3 reproduce.py my-results

The output directory must be new. No downloads or nonstandard packages are required. Compare the four CSV files to those in tables/. Each row of field_stages.csv gives the fractions inside the positive AT2 and GT450 masks; stage zero is the initial mask. frozen_fields.csv records the primary measurements against which all final fractions are verified.

For a second check, install NumPy and run:

    python3 check_windows.py

This integrates each stored binary mask window using its field's precomputed polygon/pixel intersection areas and checks all reported stage fractions. In windows/, weights are in square working-mask pixels, mask arrays are ordered by pipeline step, and polygon vertices are relative to the window's upper left edge. All 26 source scans contributed a verified window for each selected region. The scoped artifact reproduces measurements and decision tables from recorded masks. Full whole-slide inference requires the source scans and upstream software. No private Parallax operators are required.

## Provenance

Source imagery: PLISM, Original Whole Slide Images Dataset, version 1, https://doi.org/10.25452/figshare.plus.24988074.v1.
Mask generation: HistoQC, https://github.com/choosehappy/HistoQC/tree/f35e518d875e3e3799f89a7aed4e766c5a9d35e4, upstream default config.ini, seed 20261111, one shared classifier set in a single worker. See frozen_design.txt and qc_environment.json. All 26 final PNG hashes were checked against the initial run before interpreting any intermediate measurement. Mask windows, area weights and figures are derived outputs. Acquisition and model choices are fixed for this example.

## Optional whole-slide replay

The native polygon manifest (native_fields.json) lists the two scanner files, public Figshare download URL, original publisher MD5, expected final mask hash, dimensions and field vertices for every section. Coordinates are native level-zero pixel-centre coordinates, in perimeter order, with pixel edges half a sample from the centre. Use the original SVS filenames. With the exact upstream HistoQC revision installed or placed first on PYTHONPATH, Python and numerical dependencies as in qc_environment.json, run:

    LOKY_MAX_CPU_COUNT=4 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MPLBACKEND=Agg python replay_scans.py /path/to/PLISM/slides new-receipts

This optional path invokes the upstream whole-slide worker, records its registered mask windows after each pipeline operation, and verifies each final PNG hash and OpenSlide read sequence. One process shares its fitted classifiers across the 26 scans in filename order. The original files total roughly 41 GiB. The CSV and window reproductions above work offline without the WSIs. HistoQC and the input images are separately distributed by their authors.

## Licence

Code in this repository is MIT licensed (see LICENSE). Images, masks and figures derived from PLISM keep its CC BY 4.0 terms; HistoQC and the source scans are separately distributed by their authors under their own licences.
