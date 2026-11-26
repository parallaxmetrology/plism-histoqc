"""HistoQC whole-slide masks for the 26 PLISM scans, as PLISM_01/masks.py, with an optional ICC conversion.

    python run_masks.py baseline   # gate: no conversion, must reproduce the original 26 mask hashes
    python run_masks.py icc        # each read_region converted from the slide's embedded profile to sRGB

Sources, HistoQC upstream and maps are read in place and never written.
"""
from pathlib import Path
import sys, threading, logging, tempfile, json, shutil, configparser, hashlib, gc, io
from types import SimpleNamespace
HERE = Path(__file__).resolve().parent
STUDY = Path('/Volumes/Temp_flex/parallax_pathology/HISTOQC_PAIRED_SELECTION_20261111')
sys.path.insert(0, str(STUDY / 'upstream'))
import openslide, numpy as np
from PIL import Image, ImageCms
from histoqc._worker import worker
from histoqc.config import read_config_template
from histoqc.data import managed_pkg_data
from histoqc._pipeline import load_pipeline

MODE = sys.argv[1]
assert MODE in ('baseline', 'icc')
out = HERE / f'masks_{MODE}'
out.mkdir(exist_ok=True)
SRGB = ImageCms.createProfile('sRGB')


class WholePyramid(openslide.OpenSlide):
    def __init__(self, *args):
        super().__init__(*args)
        self.reads = []
        self.icc = None
        if MODE == 'icc':
            prof = self.color_profile
            assert prof is not None, 'no embedded profile'
            self.icc_name = ImageCms.getProfileDescription(prof).strip()
            self.icc = ImageCms.buildTransform(prof, SRGB, 'RGB', 'RGB', renderingIntent=ImageCms.INTENT_PERCEPTUAL)
        audit.append(self)

    def read_region(self, location, level, size):
        assert level > 0, 'Unexpected baseline read from partial baseline'
        self.reads.append([list(location), int(level), list(size)])
        im = super().read_region(location, level, size)
        if self.icc is None:
            return im
        rgb = ImageCms.applyTransform(im.convert('RGB'), self.icc)
        rgb.putalpha(im.getchannel('A'))
        return rgb


def main():
    global audit
    logging.basicConfig(level=logging.WARNING)
    config = configparser.ConfigParser()
    config.read_string(read_config_template('default'))
    log = SimpleNamespace(logger=logging.getLogger('histoqc'))
    openslide.OpenSlide = WholePyramid
    with managed_pkg_data:
        managed_pkg_data.inject_pkg_data_fallback(config)
        queue = load_pipeline(config)
        shared = {}
        for i, path in enumerate(sorted((STUDY / 'PLISM_01' / 'sources').glob('*.svs'))):
            audit = []
            receipt = out / (path.name + '.json')
            if receipt.exists():
                continue
            with tempfile.TemporaryDirectory() as tmp:
                s = worker(i, str(path), process_queue=queue, config=config, outdir=tmp, log_manager=log,
                           lock=threading.Lock(), shared_dict=shared, num_files=26, force=False, seed=20261111, debug=False)
                dest = out / (path.name + '.png')
                f = Path(tmp) / path.name / (path.name + '_mask_use.png')
                assert len(audit) == 1 and audit[0].reads
                assert s['img_bbox'] == (0, 0, *audit[0].dimensions)
                with Image.open(f) as im:
                    vals = np.unique(im)
                    assert set(vals) <= {0, 255}
                    shape = im.size
                shutil.copyfile(f, dest)
                receipt.write_text(json.dumps(dict(
                    name=path.name, mode=MODE, icc=getattr(audit[0], 'icc_name', None), mask_size=shape,
                    base=audit[0].dimensions, level_reads=audit[0].reads, completed=s['completed'], warnings=s['warnings'],
                    sha256=hashlib.sha256(dest.read_bytes()).hexdigest()), default=str))
                audit[0].close()
                del s
                gc.collect()
                print('mask', MODE, path.name, flush=True)


if __name__ == '__main__':
    main()
