"""Optional audit of the published per-field values using stored binary mask windows (requires NumPy)."""
import csv
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parent
lookup={(r['section'],int(r['field']),int(r['step'])):r for r in csv.DictReader((root/'field_stages.csv').open())}
seen=set()
for path in sorted((root/'windows').glob('*.svs.npz')):
    section,scan=path.name.removesuffix('.svs.npz').split('_')
    with np.load(path) as arrays:
        for j in range(12):
            weights=arrays[f'weight_{j}']; masks=arrays[f'mask_{j}']
            assert set(np.unique(masks))<={0,1} and (weights>=0).all()
            for i,m in enumerate(masks):
                key=(section,j,i);v=float((weights*m).sum()/weights.sum())
                assert abs(v-float(lookup[key][scan]))<1e-10
                seen.add((*key,scan))
assert len(seen)==2*len(lookup)
print(f'{len(seen)} scanner-field-stage fractions reproduced.')
