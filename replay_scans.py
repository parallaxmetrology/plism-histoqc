from pathlib import Path
import sys,os,json,tempfile,logging,threading,configparser,gc,hashlib
from types import SimpleNamespace
from functools import wraps
import numpy as np
from scipy import ndimage
here=Path(__file__).resolve().parent
import argparse
import openslide
from histoqc._worker import worker
from histoqc.config import read_config_template
from histoqc.data import managed_pkg_data
from histoqc._pipeline import load_pipeline
class WholePyramid(openslide.OpenSlide):
    def read_region(self,location,level,size):
        assert level>0, 'Unexpected baseline read from partial baseline'
        self.reads.append([list(location),int(level),list(size)])
        return super().read_region(location,level,size)
    def __init__(self,*args):
        super().__init__(*args);self.reads=[];audit.append(self)
def components(mask):
    cc,n=ndimage.label(mask)
    sizes=np.bincount(cc.ravel())[1:]
    return dict(count=int(n),largest=int(sizes.max(initial=0)),ge10000=int((sizes>=10000).sum()),positive=int(mask.sum()))
def main():
    global audit
    parser=argparse.ArgumentParser(description='Reproduce the ordered stage windows from the 26 original AT2 and GT450 PLISM SVS files.')
    parser.add_argument('slides',type=Path)
    parser.add_argument('out',type=Path)
    args=parser.parse_args()
    out=args.out;out.mkdir(exist_ok=False)
    scans=json.loads((here/'native_fields.json').read_text())
    config=configparser.ConfigParser();config.read_string(read_config_template('default'))
    openslide.OpenSlide=WholePyramid;shared={}
    with managed_pkg_data:
        managed_pkg_data.inject_pkg_data_fallback(config)
        queue=load_pipeline(config)
        for i,n in enumerate(sorted(scans)):
            path=args.slides/n
            audit=[];sname,scan=path.stem.split('_')
            orig=scans[path.name]
            scale=np.array(orig['mask_size'])/orig['base']
            windows=[]
            for row in orig['fields']:
                poly=(np.array(row['vertices'])+.5)*scale
                a,b=np.floor(poly.min(0)).astype(int);c,d=np.ceil(poly.max(0)).astype(int)
                windows.append([int(row['j']),int(a),int(b),int(c),int(d)])
            stages=[];arrays={};cc={}
            def snap(label,s):
                m=s['img_mask_use']
                assert tuple(m.shape[::-1])==tuple(orig['mask_size'])
                stages.append([label,int(m.sum())])
                for j,a,b,c,d in windows:arrays[f's{len(stages)-1}_f{j}']=m[b:d,a:c].astype(bool,copy=True)
            def decorate(fn,label):
                @wraps(fn)
                def wrapped(s,params):
                    if not stages:snap('initial',s)
                    if fn.__name__=='finalProcessingArea':cc['before']=components(s['img_mask_use'])
                    fn(s,params)
                    snap(label,s)
                    if fn.__name__=='finalProcessingArea':cc['after']=components(s['img_mask_use'])
                return wrapped
            labels=config['pipeline']['steps'].split()
            assert len(labels)==len(queue)
            q=[(decorate(fn,label),params) for label,(fn,params) in zip(labels,queue)]
            with tempfile.TemporaryDirectory() as tmp:
                s=worker(i,str(path),process_queue=q,config=config,outdir=tmp,log_manager=SimpleNamespace(logger=logging.getLogger('trace')),lock=threading.Lock(),shared_dict=shared,num_files=26,force=False,seed=20261111,debug=False)
                sha=hashlib.sha256((Path(tmp)/path.name/(path.name+'_mask_use.png')).read_bytes()).hexdigest()
                assert sha==orig['sha256'],(path.name,sha,orig['sha256'])
                assert audit[0].reads==orig['level_reads']
                np.savez_compressed(out/(path.name+'.npz'),**arrays)
                (out/(path.name+'.json')).write_text(json.dumps(dict(scan=path.name,windows=windows,stages=stages,component_filter=cc,sha256=sha)))
                audit[0].close();del s;gc.collect()
                print(path.name,sha,flush=True)
if __name__=='__main__':main()
