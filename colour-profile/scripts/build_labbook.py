"""Build LABBOOK.html for the ICC rerun from results_baseline/ and results_icc/."""
import csv, json, glob, hashlib, statistics as st, html
from pathlib import Path
HERE = Path(__file__).resolve().parent
R = lambda m, f: list(csv.DictReader(open(HERE / f'results_{m}/{f}')))
gate = json.loads((HERE / 'results_baseline/gate.json').read_text())
th = json.loads((HERE / 'thumbnail_check.json').read_text())


def summary(m):
    S = R(m, 'slide_results.csv'); F = R(m, 'field_results.csv')
    P = {(r['slide'], r['scan']): int(r['positive_pixels']) for r in R(m, 'mask_pixels.csv')}
    secs = sorted({k[0] for k in P})
    rat = [P[(s, 'GT450')] / P[(s, 'AT2')] for s in secs]
    return dict(S=S, F={(r['slide'], r['field']): r for r in F},
                tot={k: sum(int(r[k]) for r in S) for k in ['both_in', 'AT2_only', 'GT450_only', 'both_out']},
                msf=st.mean(float(r['disagreement']) for r in S), ratio=st.median(rat), smaller=sum(x < 1 for x in rat),
                empty=[f'{k[0]}_{k[1]}' for k, v in P.items() if v == 0],
                adm={sc: sum(int(r[sc + '_in']) for r in F) for sc in ['AT2', 'GT450']}, P=P)


B, I = summary('baseline'), summary('icc')
sw = lambda X: X['tot']['AT2_only'] + X['tot']['GT450_only']


def table(head, rows, num=()):
    h = ''.join(f'<th{" class=n" if i in num else ""}>{html.escape(c)}</th>' for i, c in enumerate(head))
    b = ''.join('<tr>' + ''.join(f'<td{" class=n" if i in num else ""}>{c}</td>' for i, c in enumerate(r)) + '</tr>' for r in rows)
    return f'<div class=tw><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


main_rows = [[lab, sw(X), X['tot']['AT2_only'], X['tot']['GT450_only'], X['tot']['both_in'], X['tot']['both_out'], f"{X['msf']:.3f}",
              X['adm']['AT2'], X['adm']['GT450'], f"{X['ratio']:.3f}", ', '.join(X['empty']) or 'none']
             for lab, X in [('No profile (original; reproduced here)', B), ('Embedded profile applied', I)]]
sec_rows = []
for b, i in zip(B['S'], I['S']):
    s = b['slide']
    sec_rows.append([s, int(b['AT2_only']) + int(b['GT450_only']), int(i['AT2_only']) + int(i['GT450_only']),
                     f"{B['P'][(s, 'GT450')] / B['P'][(s, 'AT2')]:.3f}", f"{I['P'][(s, 'GT450')] / I['P'][(s, 'AT2')]:.3f}",
                     f"{th[s]['raw'][0]:.1f} / {th[s]['raw'][1]:.1f}", f"{th[s]['icc'][0]:.1f} / {th[s]['icc'][1]:.1f}"])
mv = []
for sc in ['AT2', 'GT450']:
    gain = sum(1 for k in B['F'] if B['F'][k][sc + '_in'] == '0' and I['F'][k][sc + '_in'] == '1')
    lose = sum(1 for k in B['F'] if B['F'][k][sc + '_in'] == '1' and I['F'][k][sc + '_in'] == '0')
    mv.append([sc, B['adm'][sc], I['adm'][sc], gain, lose])
icc_sw = [[k[0], k[1], f"{float(r['AT2_fraction']):.3f}", f"{float(r['GT450_fraction']):.3f}", 'AT2 only' if r['AT2_in'] == '1' else 'GT450 only']
          for k, r in I['F'].items() if r['discordant'] == 'True']
plan_sha = (HERE / 'PLAN.sha256').read_text().split()[0]
assert plan_sha == hashlib.sha256((HERE / 'PLAN.md').read_bytes()).hexdigest()

body = f"""
<p class=kicker>Lab book · Parallax Metrology · built by build_labbook.py</p>
<h1>Paired HistoQC with embedded ICC profiles applied</h1>
<p class=lede>Same 26 PLISM scans, same HistoQC revision, configuration, seed and 156 fields as the original paired study. One change: every region HistoQC reads is first converted from the scan's embedded colour profile to sRGB. Prompted by the HistoQC owner's suggestion on choosehappy/HistoQC#343.</p>

<h2>1. Record</h2>
<ul>
<li>Plan written and frozen before any run in this folder: <code>PLAN.md</code>, SHA-256 <code>{plan_sha}</code>, {(HERE / 'PLAN.frozen_at.txt').read_text().strip()}.</li>
<li>Prior look, disclosed in the plan: thumbnail tissue brightness with and without profiles (section 5).</li>
<li>Environment rebuilt to the original record: Python 3.10.22, numpy 1.23.5, scipy 1.10.0, scikit-learn 1.2.1, scikit-image 0.19.3, Pillow 9.4.0, openslide-python 1.4.6, OpenSlide 4.0.1. HistoQC f35e518, default <code>config.ini</code>, seed 20261111, one process.</li>
<li>Conversion: <code>OpenSlide.read_region</code> wrapped at run time (HistoQC source untouched); Pillow ImageCms (LittleCMS), perceptual intent, RGB converted and alpha kept. HistoQC's packaged training and template images are not converted.</li>
<li>Result posted as a reply on choosehappy/HistoQC#343, 24 November 2026.</li>
</ul>

<h2>2. Gate</h2>
<p>With the conversion switched off, the rebuilt environment reproduced all {gate['reproduced']} of {gate['original']} original final mask PNGs byte for byte (SHA-256 against the original <code>final_hashes.csv</code>), and the original result: {sw(B)} switched, {B['tot']['AT2_only']} AT2-only, {B['tot']['GT450_only']} GT450-only. Pass. In the converted run, all 26 scans carried a profile ("AT2" on every AT2 file, "Segue_v2" on every GT450 file), and every scan read the same pyramid levels and produced the same mask size as without conversion.</p>

<h2>3. Result</h2>
{table(['run', 'fields switched (of 156)', 'AT2 only', 'GT450 only', 'both in', 'both out', 'mean section switch fraction', 'admitted on AT2', 'admitted on GT450', 'median GT450/AT2 mask pixels', 'empty masks'], main_rows, num=range(1, 10))}
<p>With the profiles applied, {sw(I)} fields switch instead of {sw(B)}. The two scanners now admit nearly the same number of fields ({I['adm']['AT2']} and {I['adm']['GT450']}, against {B['adm']['AT2']} and {B['adm']['GT450']}). Agreement rises mainly through fields excluded on both scans ({B['tot']['both_out']} to {I['tot']['both_out']}); fields admitted on both rise from {B['tot']['both_in']} to {I['tot']['both_in']}. No mask is empty. GT450's whole-slide usable area is smaller than AT2's on {I['smaller']} of 13 sections, with a median ratio of {I['ratio']:.3f} (was {B['ratio']:.3f}).</p>
{table(['scanner', 'admitted, no profile', 'admitted, profile', 'gained', 'lost'], mv, num=(1, 2, 3, 4))}
<p>Fields still switching with the profiles applied:</p>
{table(['section', 'field', 'fraction inside, AT2', 'fraction inside, GT450', 'admitted on'], icc_sw, num=(1, 2, 3))}

<h2>4. Per section</h2>
{table(['section', 'switched, no profile', 'switched, profile', 'GT450/AT2 mask pixels, no profile', 'with profile', 'tissue luma AT2 / GT450, no profile', 'with profile'], sec_rows, num=(1, 2, 3, 4))}

<h2>5. Prior thumbnail look</h2>
<p>Before the plan: median tissue luma (0 to 255) on 2000-pixel thumbnails, tissue taken as luma below the 95th percentile minus 25 on the unconverted thumbnail, and the same pixels measured after conversion (table above). Median AT2 to GT450 gap across sections: {th['_median_gap_raw']:.1f} without profiles, {th['_median_gap_icc']:.1f} with. With the profiles, AT2 renders slightly brighter than GT450 on {th['_icc_AT2_brighter']} of 13 sections.</p>

<h2>6. Scope</h2>
<p>Same array, scanners, pipeline and settings; only the colour conversion changes. One rendering intent was run. Descriptive: it shows that applying the vendor profiles changes which fields the default pipeline admits here, and how far the two scanners then agree. It does not say which mask is right. Most of the 156 fields, which were chosen as tissue locations, are excluded on both scans under the default configuration with or without profiles; no step trace was run for the converted masks, so which steps drive the remaining exclusions and switches is not measured here.</p>

<h2>7. Files</h2>
<p><code>PLAN.md</code>, <code>PLAN.sha256</code>, <code>PLAN.frozen_at.txt</code>; <code>run_masks.py</code> (masks, both modes), <code>score.py</code> (scoring and gate), <code>thumbnail_check.py</code>, <code>build_labbook.py</code>; <code>masks_baseline/</code>, <code>masks_icc/</code> (PNG + receipt per scan); <code>results_baseline/</code>, <code>results_icc/</code>; <code>logs/</code>.</p>
"""
css = """:root{--bg:#fcfcfb;--fg:#0b0b0b;--fg2:#52514e;--line:#e8e7e3;--card:#f3f2ee}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#1a1a19;--fg:#f0efec;--fg2:#c3c2b7;--line:#33332f;--card:#24241f}}
:root[data-theme="dark"]{--bg:#1a1a19;--fg:#f0efec;--fg2:#c3c2b7;--line:#33332f;--card:#24241f}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 ui-sans-serif,-apple-system,"Helvetica Neue",Arial,sans-serif}
main{max-width:900px;margin:0 auto;padding:32px 16px 80px}h1{font-size:1.6rem;line-height:1.25}h2{font-size:1.1rem;margin-top:2em;padding-top:.6em;border-top:1px solid var(--line)}
.kicker{color:var(--fg2);font-size:.85rem}.lede{color:var(--fg2)}code{font:.86em ui-monospace,Menlo,monospace;background:var(--card);padding:1px 4px;border-radius:4px;overflow-wrap:anywhere}
.tw{overflow-x:auto;margin:1em 0}table{border-collapse:collapse;font-size:.85rem;width:100%}th,td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--fg2);font-weight:600}.n{text-align:right;font-variant-numeric:tabular-nums}"""
(HERE / 'LABBOOK.html').write_text(f'<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>ICC Rerun Lab Book</title><style>{css}</style></head><body><main>{body}</main></body></html>')
print('LABBOOK.html written')
