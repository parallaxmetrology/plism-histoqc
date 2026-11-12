"""Recompute the frozen and exploratory tables from published stage fractions."""
import csv
from collections import Counter,defaultdict
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
def read(name):
    with (ROOT/name).open(newline='') as f:return list(csv.DictReader(f))
def run(out):
    groups=defaultdict(list)
    for r in read('field_stages.csv'):
        groups[(r['section'],int(r['field']))].append(r)
    assert len(groups)==156 and len(set(s for s,j in groups))==13
    section_counts=defaultdict(Counter);first=Counter();persistent=Counter();stage_n=Counter()
    details=[];temporary=[];expected={(r['slide'],int(r['field'])):r for r in read('frozen_fields.csv')}
    assert groups.keys()==expected.keys()
    stage_names=None
    for (section,j),rows in sorted(groups.items()):
        assert [int(r['step']) for r in rows]==list(range(len(rows)))
        labels=[r['stage'] for r in rows]
        if stage_names is None:stage_names=labels
        assert labels==stage_names
        fractions=[(float(r['AT2']),float(r['GT450'])) for r in rows]
        assert all(0<=v<=1+1e-10 for pair in fractions for v in pair)
        def state(a,b):
            return ('both_in' if b>=.5 else 'AT2_only') if a>=.5 else ('GT450_only' if b>=.5 else 'both_out')
        states=[state(a,b) for a,b in fractions];end=states[-1]
        assert states[0]=='both_in'
        ref=expected[(section,j)]
        assert max(abs(fractions[-1][k]-float(ref[n+'_fraction'])) for k,n in enumerate(['AT2','GT450']))<1e-9
        section_counts[section][end]+=1
        for i,st in enumerate(states):
            if st.endswith('_only'):stage_n[i]+=1
        if end.endswith('_only'):
            f=states.index(end);p=1+max(i for i,st in enumerate(states) if st!=end)
            lost=sum(a==end and b!=end for a,b in zip(states,states[1:]))
            opposite=any(st.endswith('_only') and st!=end for st in states)
            details.append([section,j,end,labels[f],labels[p],lost,int(opposite)])
            first[f]+=1;persistent[p]+=1
        elif any(st.endswith('_only') for st in states):
            temporary.append([section,j,end,labels[next(i for i,st in enumerate(states) if st.endswith('_only'))]])
    def save(name,header,records):
        with (out/name).open('x',newline='') as f:
            w=csv.writer(f);w.writerow(header.split(','));w.writerows(records)
    sections=[]
    for s,c in sorted(section_counts.items()):
        assert sum(c.values())==12
        sections.append([s,c['both_in'],c['AT2_only'],c['GT450_only'],c['both_out'],(c['AT2_only']+c['GT450_only'])/12])
    save('sections.csv','section,both_in,AT2_only,GT450_only,both_out,disagreement',sections)
    save('switches.csv','section,field,final_direction,first,persistent,lost_direction_count,ever_opposite',details)
    save('transient.csv','section,field,final_state,first_transient',temporary)
    save('stages.csv','step,stage,total_discordant,first_of_final,persistent_of_final',
         [[i,n,stage_n[i],first[i],persistent[i]] for i,n in enumerate(stage_names)])
    print(f'{len(details)} final switches; {len(temporary)} temporary-only disagreements across {len(sections)} sections.')
if __name__=='__main__':
    dest=Path(sys.argv[1]);dest.mkdir(exist_ok=False,parents=True);run(dest)
