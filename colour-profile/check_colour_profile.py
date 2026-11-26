"""Recompute the colour-profile rerun from the stored final masks.

    python3 colour-profile/check_colour_profile.py

Needs Python 3.10+, NumPy, Pillow and Shapely 2. No slides or HistoQC install needed. It checks:
  1. colour-profile/PLAN.md matches its recorded SHA-256;
  2. the gate: the 26 masks rerun with the wrapper on and the conversion off match the original
     final mask hashes in final_hashes.csv;
  3. for both mask sets, every field fraction and decision, every section count and the switch totals,
     against colour-profile/results/. The scoring is the original study's: exact polygon overlap with
     the positive pixels of the final mask, admitted at 0.50 or more.
It prints ALL MATCH and exits 0 when everything agrees.
"""
import csv, hashlib, json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image
from shapely.geometry import Polygon, box

CP = Path(__file__).resolve().parent
ROOT = CP.parent
problems = []


def check(ok, msg):
    if not ok:
        problems.append(msg)


want = (CP / 'PLAN.sha256').read_text().split()[0]
check(want == hashlib.sha256((CP / 'PLAN.md').read_bytes()).hexdigest(), 'PLAN.md hash differs from PLAN.sha256')

original = {r['scan']: r['matched_png_sha256'] for r in csv.DictReader(open(ROOT / 'final_hashes.csv', newline=''))}
gate = [k for k in original if hashlib.sha256((CP / 'masks' / 'default' / f'{k}.png').read_bytes()).hexdigest() != original[k]]
check(len(original) == 26 and not gate, f'gate: masks differing from final_hashes.csv: {gate}')
print(f'gate: {len(original) - len(gate)} of {len(original)} masks match the original final hashes')

native = json.loads((ROOT / 'native_fields.json').read_text())
sections = sorted({k.rsplit('_', 1)[0] for k in native})


def fraction(vertices, mask, scale):
    p = Polygon((np.array(vertices, dtype=float) + .5) * scale)  # pixel centres to edges, then to mask pixels
    x, y, X, Y = p.bounds
    total = keep = 0.
    for j in range(math.floor(y), math.ceil(Y)):
        for i in range(math.floor(x), math.ceil(X)):
            area = p.intersection(box(i, j, i + 1, j + 1)).area
            total += area
            if mask[j, i]:
                keep += area
    assert abs(total - p.area) < 1e-7
    return keep / total


for arm in ['default', 'profile']:
    shipped = {(r['slide'], r['field']): r for r in csv.DictReader(open(CP / 'results' / arm / 'field_results.csv', newline=''))}
    shipped_sec = {r['slide']: r for r in csv.DictReader(open(CP / 'results' / arm / 'slide_results.csv', newline=''))}
    totals = dict(both_in=0, AT2_only=0, GT450_only=0, both_out=0)
    for sec in sections:
        masks = []
        for scan in ['AT2', 'GT450']:
            name = f'{sec}_{scan}.svs'
            meta = json.loads((CP / 'masks' / arm / f'{name}.json').read_text())
            png = CP / 'masks' / arm / f'{name}.png'
            check(hashlib.sha256(png.read_bytes()).hexdigest() == meta['sha256'], f'{arm} {name}: PNG hash differs from its JSON')
            masks.append((np.array(Image.open(png)) > 0, np.array(meta['mask_size']) / np.array(meta['base'])))
        fields = {scan: {f['j']: f['vertices'] for f in native[f'{sec}_{scan}.svs']['fields']} for scan in ['AT2', 'GT450']}
        counts = dict(both_in=0, AT2_only=0, GT450_only=0, both_out=0)
        for j in sorted(fields['AT2']):
            fa, fb = (fraction(fields[s][j], m, sc) for s, (m, sc) in zip(['AT2', 'GT450'], masks))
            a, b = int(fa >= .5), int(fb >= .5)
            key = ['both_out', 'GT450_only', 'AT2_only', 'both_in'][2 * a + b]
            counts[key] += 1
            ref = shipped[(sec, str(j))]
            check((a, b) == (int(ref['AT2_in']), int(ref['GT450_in'])), f'{arm} {sec} field {j}: decision differs')
            check(abs(fa - float(ref['AT2_fraction'])) < 1e-9 and abs(fb - float(ref['GT450_fraction'])) < 1e-9, f'{arm} {sec} field {j}: fraction differs')
        check(all(int(shipped_sec[sec][k]) == v for k, v in counts.items()), f'{arm} {sec}: section counts differ')
        for k, v in counts.items():
            totals[k] += v
    print(f"{arm:8s} {totals['AT2_only'] + totals['GT450_only']:3d} of 156 fields switch "
          f"({totals['AT2_only']} AT2-only, {totals['GT450_only']} GT450-only); {totals['both_in']} admitted on both, {totals['both_out']} excluded on both")

print('\nALL MATCH' if not problems else '\n' + '\n'.join(problems))
sys.exit(1 if problems else 0)
