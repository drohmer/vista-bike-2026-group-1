"""Metrics and Pareto front for a candidate photo selection.

Compares route error, coverage and vegetation across selections. Expects
photo_metadata.json and selection-30.txt next to it (copy them from data/).
"""
import json, math, os, numpy as np
HERE=os.path.dirname(os.path.abspath(__file__))
recs=[r for r in json.load(open(HERE+'/photo_metadata.json')) if 'lat' in r and r.get('datetime')]
recs.sort(key=lambda r:(r['datetime'],r['file']))
kept=[]
for r in recs:
    dh=r.get('dhash'); tw=None
    if dh:
        for k in kept:
            if k.get('dhash') and sum(a!=b for a,b in zip(dh,k['dhash']))<=5: tw=k;break
    if tw is None: kept.append(r)
recs=kept; n=len(recs)
lat=np.array([r['lat'] for r in recs]);lon=np.array([r['lon'] for r in recs]);l0=lat.mean()
X=(lon-lon.mean())*111320*math.cos(math.radians(l0));Y=(lat-l0)*110540
veg=np.array([r.get('veg_frac',0.) for r in recs])
name={r['file']:i for i,r in enumerate(recs)}
E=np.full((n,n),np.inf)
for i in range(n):
    E[i,i]=0.
    for j in range(i+1,n):
        if j==i+1: E[i,j]=0.;continue
        dx,dy=X[j]-X[i],Y[j]-Y[i];L2=dx*dx+dy*dy;k=np.arange(i+1,j)
        px,py=X[k]-X[i],Y[k]-Y[i]
        if L2<1e-9: d=np.hypot(px,py)
        else:
            t=np.clip((px*dx+py*dy)/L2,0,1);d=np.hypot(px-t*dx,py-t*dy)
        E[i,j]=float(d.max())
pts=[]
for a in range(n-1):
    d=math.hypot(X[a+1]-X[a],Y[a+1]-Y[a]);m=max(2,int(d/5))
    for u in np.linspace(0,1,m,endpoint=False): pts.append((X[a]+u*(X[a+1]-X[a]),Y[a]+u*(Y[a+1]-Y[a])))
P=np.array(pts)
def cov(idx,rad=150.):
    D=np.hypot(P[:,0][:,None]-X[idx][None,:],P[:,1][:,None]-Y[idx][None,:]);return float((D.min(1)<rad).mean())
def err(idx):
    return max(E[a,b] for a,b in zip(idx[:-1],idx[1:]))
def show(lbl,files):
    idx=sorted(name[f] for f in files if f in name)
    print('%-26s %2d ph | route error %7.1f m | cov<150m %5.1f%% | veg %.3f'
          %(lbl,len(idx),err(idx),100*cov(idx),veg[idx].mean()))
show('ALL (%d)'%n, [r['file'] for r in recs])
show('candidate selection', open(HERE+'/selection-30.txt').read().split('\n'))
for w in ['0','20','50']:
    os.system('cd %s && python3 choose_v4.py 30 %s >/dev/null 2>&1'%(HERE,w))
    show('v4 W_VEG=%s'%w, json.load(open(HERE+'/selection_v4.json')))
print()
print('Pareto front under HARD CONSTRAINT (max vegetation, error <= Emax):')
for em in [10,25,50,100,200]:
    os.system('cd %s && python3 choose_v4.py 30 500 %d >/dev/null 2>&1'%(HERE,em))
    try: show('  error <= %3d m'%em, json.load(open(HERE+'/selection_v4.json')))
    except Exception: print('  error <= %3d m : infeasible'%em)
