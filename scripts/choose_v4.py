"""Selection v4 — refonte suite aux trois audits.

Changements de fond :
 - objectif = SIMPLIFICATION DE COURBE (erreur de polyligne en metres),
   pas couverture d'un ensemble de points. Un trou coute desormais cher.
 - resolution par DP EXACTE sur DAG ordonne (O(k n^2)), plus d'approximation
   gloutonne ni de garantie 1-1/e a invoquer.
 - suppression du terme 'turn' (bruit GPS : angles calcules entre segments
   de 2838 m et 5 m) et du double comptage de la vegetation.
 - suppression du proxy d'angle HSV : mesure invalidee (deux vues disjointes
   au meme point obtenaient 0.79, au-dessus du 95e centile).
 - dedup : on conserve le nom de l'ORIGINAL, pas celui du doublon.
"""
import json, math, sys, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BUDGET = int(sys.argv[1]) if len(sys.argv) > 1 else 30
W_VEG  = float(sys.argv[2]) if len(sys.argv) > 2 else 50.0   # poids vegetation
EMAX   = float(sys.argv[3]) if len(sys.argv) > 3 else 1e9    # contrainte dure (m)

recs = json.load(open(os.path.join(HERE, 'meta_photos.json')))
recs = [r for r in recs if 'lat' in r and r.get('datetime')]
recs.sort(key=lambda r: (r['datetime'], r['file']))

# ---------- dedup : garder l'ORIGINAL (bug B5 des audits) ----------
kept = []
for r in recs:
    dh = r.get('dhash'); twin = None
    if dh:
        for k in kept:
            if k.get('dhash') and sum(a != b for a, b in zip(dh, k['dhash'])) <= 5:
                twin = k; break
    if twin is None:
        kept.append(r)
    else:
        print('-- doublon : %s ~ %s (on garde %s)' % (r['file'], twin['file'], twin['file']),
              file=sys.stderr)
recs = kept
n = len(recs)

lat = np.array([r['lat'] for r in recs]); lon = np.array([r['lon'] for r in recs])
l0 = lat.mean()
X = (lon - lon.mean()) * 111320 * math.cos(math.radians(l0))
Y = (lat - l0) * 110540
veg = np.array([r.get('veg_frac', 0.0) for r in recs])

# qualite : nettete penalisee par sur/sous-exposition, normalisee
sh = np.array([r.get('sharp', 0.0) for r in recs])
sh = (sh - sh.min()) / (np.ptp(sh) + 1e-9)
ex = np.array([r.get('expo', 0.45) for r in recs])
qual = sh * np.clip(1 - np.abs(ex - 0.45) * 1.6, 0, 1)

# ---------- E[i,j] : erreur max de polyligne si l'on saute i+1..j-1 ----------
E = np.full((n, n), np.inf)
for i in range(n):
    E[i, i] = 0.0
    for j in range(i + 1, n):
        if j == i + 1:
            E[i, j] = 0.0; continue
        ax, ay, bx, by = X[i], Y[i], X[j], Y[j]
        dx, dy = bx - ax, by - ay
        L2 = dx*dx + dy*dy
        k = np.arange(i + 1, j)
        px, py = X[k] - ax, Y[k] - ay
        if L2 < 1e-9:
            d = np.hypot(px, py)
        else:
            t = np.clip((px*dx + py*dy) / L2, 0, 1)
            d = np.hypot(px - t*dx, py - t*dy)
        E[i, j] = float(d.max())

# ---------- DP exacte : chemin a exactement BUDGET sommets, de 0 a n-1 ----------
NEG = -1e18
unary = W_VEG * veg + 0.15 * qual
dp = np.full((BUDGET + 1, n), NEG)
par = np.full((BUDGET + 1, n), -1, dtype=int)
dp[1, 0] = unary[0]                       # on impose de partir de la 1re photo
for t in range(1, BUDGET):
    for j in range(n):
        if dp[t, j] <= NEG / 2: continue
        base = dp[t, j]
        for m in range(j + 1, n):
            e = E[j, m]
            if e > EMAX: continue          # contrainte dure
            v = base + unary[m] - e
            if v > dp[t + 1, m]:
                dp[t + 1, m] = v; par[t + 1, m] = j
if dp[BUDGET, n - 1] <= NEG / 2:
    print('infaisable avec EMAX=%.0f m' % EMAX, file=sys.stderr); sys.exit(1)

sel, t, j = [], BUDGET, n - 1              # on impose d'arriver a la derniere
while j >= 0 and t >= 1:
    sel.append(j); j = par[t, j]; t -= 1
sel = sorted(sel)

# ---------- metriques honnetes ----------
def polyline_err(idx):
    e = 0.0
    for a, b in zip(idx[:-1], idx[1:]): e = max(e, E[a, b])
    return e
def coverage(idx, rad=150.0):
    """couverture evaluee sur une GRILLE DENSE du chemin, pas sur les photos"""
    pts = []
    for a, b in zip(range(n-1), range(1, n)):
        d = math.hypot(X[b]-X[a], Y[b]-Y[a]); m = max(2, int(d/5))
        for u in np.linspace(0, 1, m, endpoint=False):
            pts.append((X[a]+u*(X[b]-X[a]), Y[a]+u*(Y[b]-Y[a])))
    P = np.array(pts)
    D = np.hypot(P[:, 0][:, None] - X[idx][None, :], P[:, 1][:, None] - Y[idx][None, :])
    return float((D.min(1) < rad).mean())

allidx = list(range(n))
print('\n%d photos uniques | budget %d' % (n, BUDGET), file=sys.stderr)
print('                        erreur trace   couverture<150m   vegetation', file=sys.stderr)
print('  les %d photos          %7.1f m        %6.1f%%          %.3f'
      % (n, polyline_err(allidx), 100*coverage(allidx), veg.mean()), file=sys.stderr)
print('  selection v4          %7.1f m        %6.1f%%          %.3f'
      % (polyline_err(sel), 100*coverage(sel), veg[sel].mean()), file=sys.stderr)

json.dump([recs[i]['file'] for i in sel], open(os.path.join(HERE, 'selection_v4.json'), 'w'), indent=1)
open(os.path.join(HERE, 'selection_v4.txt'), 'w').write(
    '\n'.join(recs[i]['file'] for i in sel) + '\n')
for i in sel:
    print('%-34s veg=%.2f' % (recs[i]['file'][:34], veg[i]))
