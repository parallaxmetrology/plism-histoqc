"""Score a mask folder on the 156 fields: PLISM_01/score.py logic unchanged, input/output folders as arguments.

    python score.py baseline   # also checks every mask hash against the original final_hashes.csv (the gate)
    python score.py icc
"""
from pathlib import Path
import csv, json, math, hashlib, sys
import numpy as np
from PIL import Image
from shapely.geometry import Polygon, box

HERE = Path(__file__).resolve().parent
P1 = Path('/Volumes/Temp_flex/parallax_pathology/HISTOQC_PAIRED_SELECTION_20261111/PLISM_01')
MODE = sys.argv[1]
masks_dir = HERE / f'masks_{MODE}'
res = HERE / f'results_{MODE}'
res.mkdir(exist_ok=True)

if MODE == 'baseline':
    want = {r['scan']: r['matched_png_sha256'] for r in csv.DictReader(open(P1 / 'STEP_TRACE/plism-histoqc/final_hashes.csv'))}
    got = {p.name[:-4]: hashlib.sha256(p.read_bytes()).hexdigest() for p in masks_dir.glob('*.svs.png')}
    bad = sorted(k for k in want if got.get(k) != want[k])
    print('gate:', len(want), 'original hashes;', len(want) - len(bad), 'reproduced;', 'differ:', bad)
    (res / 'gate.json').write_text(json.dumps(dict(original=len(want), reproduced=len(want) - len(bad), differ=bad), indent=1))

fields, slides, pixels = [], [], []
for file in sorted((P1 / 'maps').glob('*.json')):
    rows = json.loads(file.read_text())
    masks = []
    for scan in ['AT2', 'GT450']:
        prefix = masks_dir / (file.stem + '_' + scan + '.svs')
        meta = json.loads(Path(str(prefix) + '.json').read_text())
        p = Path(str(prefix) + '.png')
        assert hashlib.sha256(p.read_bytes()).hexdigest() == meta['sha256']
        mask = np.array(Image.open(p)) > 0
        pixels.append([file.stem, scan, int(mask.sum()), mask.size])
        masks.append((mask, np.array(meta['mask_size']) / np.array(meta['base'])))
    counts = [0] * 4
    for row in rows:
        frac = []
        for coords, (mask, scale) in zip(row['native_pixel_center_frame'], masks):
            p = Polygon((np.array(coords) + .5) * scale)
            x, y, X, Y = p.bounds
            total = keep = 0.
            for j in range(math.floor(y), math.ceil(Y)):
                for i in range(math.floor(x), math.ceil(X)):
                    area = p.intersection(box(i, j, i + 1, j + 1)).area
                    total += area
                    if mask[j, i]:
                        keep += area
            assert abs(total - p.area) < 1e-7
            frac.append(keep / total)
        a, b = [int(f >= .5) for f in frac]
        counts[2 * a + b] += 1
        fields.append([file.stem, row['j'], row['status'], *frac, a, b, a != b])
    neither, b_only, a_only, both = counts
    slides.append([file.stem, len(rows), both, a_only, b_only, neither, (a_only + b_only) / len(rows)])
assert len(fields) == 156 and len(slides) == 13
for fn, header, rows in [('field_results.csv', 'slide,field,prior_status,AT2_fraction,GT450_fraction,AT2_in,GT450_in,discordant', fields),
                         ('slide_results.csv', 'slide,n,both_in,AT2_only,GT450_only,both_out,disagreement', slides),
                         ('mask_pixels.csv', 'slide,scan,positive_pixels,mask_pixels', pixels)]:
    with (res / fn).open('w', newline='') as f:
        w = csv.writer(f); w.writerow(header.split(',')); w.writerows(rows)
sw = [r for r in fields if r[-1]]
print(MODE, 'switched', len(sw), 'AT2-only', sum(r[5] == 1 for r in sw), 'GT450-only', sum(r[6] == 1 for r in sw))
