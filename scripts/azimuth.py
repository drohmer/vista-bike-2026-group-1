"""Estimation a posteriori des azimuts de visee.

Principe : l'appariement de points entre deux photos ne donne que leur pose
RELATIVE. Le GPS fournit l'ancrage absolu manquant :
  - recoverPose donne la direction A->B dans le repere CAMERA de A
  - le GPS donne la direction A->B par rapport au NORD
  - la difference des deux = azimut absolu de l'axe optique de A
"""
import json, math, os, sys, itertools
import numpy as np, cv2
from PIL import Image, ImageOps

FOLDER = sys.argv[1]
MAXW = 1400
BMIN, BMAX = 15.0, 300.0      # bornes de baseline GPS (m)

meta = [r for r in json.load(open('meta_photos.json')) if 'lat' in r and r.get('datetime')]
meta.sort(key=lambda r: (r['datetime'], r['file']))
n = len(meta)
lat = np.array([r['lat'] for r in meta]); lon = np.array([r['lon'] for r in meta])
l0 = lat.mean()
E = (lon - lon.mean()) * 111320 * math.cos(math.radians(l0))   # est
N = (lat - l0) * 110540                                        # nord

# ---------- chargement + SIFT ----------
import pickle
_cache = pickle.load(open('feats.pkl','rb')) if os.path.exists('feats.pkl') else None
sift = cv2.SIFT_create(nfeatures=6000)
feats = []
for r in meta:
    im = Image.open(os.path.join(FOLDER, r['file']))
    im = ImageOps.exif_transpose(im)          # redresse selon l'EXIF Orientation
    w0, h0 = im.size
    sc = MAXW / max(w0, h0)
    im = im.resize((max(1,int(w0*sc)), max(1,int(h0*sc))), Image.BILINEAR).convert('L')
    a = np.asarray(im)
    W, H = a.shape[1], a.shape[0]
    f35 = r.get('f35', 28.0)
    fpx = f35 / 36.0 * max(W, H)              # convention equivalent 24x36
    K = np.array([[fpx, 0, W/2.0], [0, fpx, H/2.0], [0, 0, 1.0]])
    if _cache is not None:
        pts, de = _cache[len(feats)]
        kp = [cv2.KeyPoint(float(p[0]), float(p[1]), 1.0) for p in pts]
    else:
        kp, de = sift.detectAndCompute(a, None)
    feats.append(dict(kp=kp, de=de, K=K, wh=(W, H)))
    print('sift %-34s %5d pts' % (r['file'][:34], 0 if de is None else len(kp)), file=sys.stderr)

bf = cv2.BFMatcher()
est = [[] for _ in range(n)]   # est[i] = liste (azimut, poids, autre, inliers)
rel = []                       # rotations relatives, pour validation croisee

def horiz_angle(v):
    """angle horizontal (rad) d'un vecteur du repere camera (x droite, y bas, z avant)"""
    return math.atan2(v[0], v[2])

pairs = [(i, j) for i, j in itertools.combinations(range(n), 2)
         if BMIN <= math.hypot(E[j]-E[i], N[j]-N[i]) <= BMAX]
print('\n%d paires candidates' % len(pairs), file=sys.stderr)

ok = 0
for i, j in pairs:
    fi, fj = feats[i], feats[j]
    if fi['de'] is None or fj['de'] is None: continue
    mm = bf.knnMatch(fi['de'], fj['de'], k=2)
    good = [a for a, b in (p for p in mm if len(p) == 2) if a.distance < 0.75 * b.distance]
    if len(good) < 30: continue
    p1 = np.float32([fi['kp'][g.queryIdx].pt for g in good])
    p2 = np.float32([fj['kp'][g.trainIdx].pt for g in good])
    # matrice essentielle avec les intrinseques de i (focales proches)
    Emat, mask = cv2.findEssentialMat(p1, p2, fi['K'], method=cv2.USAC_MAGSAC,
                                      prob=0.9999, threshold=3.0)
    if Emat is None or Emat.shape != (3, 3): continue
    ninl, R, t, mask2 = cv2.recoverPose(Emat, p1, p2, fi['K'], mask=mask)
    if ninl < 20: continue

    base = math.hypot(E[j]-E[i], N[j]-N[i])
    # direction A->B dans le repere camera de A :  C_B = -R^T t
    dA = (-R.T @ t).ravel()
    # direction B->A dans le repere camera de B :  C_A = t  (origine de A vue de B)
    dB = (t).ravel()
    thAB = math.atan2(E[j]-E[i], N[j]-N[i])        # azimut monde A->B (0=nord)
    thBA = thAB + math.pi
    azA = (thAB - horiz_angle(dA)) % (2*math.pi)
    azB = (thBA - horiz_angle(dB)) % (2*math.pi)
    # poids : baseline longue = ancrage GPS fiable ; beaucoup d'inliers = geometrie sure
    w = min(base / 4.7, 12.0) * math.log1p(ninl)
    est[i].append((azA, w, j, ninl, base))
    est[j].append((azB, w, i, ninl, base))
    rel.append((i, j, R, ninl, base))
    ok += 1
    print('  %2d-%2d base=%5.1fm inl=%4d  azA=%5.1f azB=%5.1f' %
          (i, j, base, ninl, math.degrees(azA), math.degrees(azB)), file=sys.stderr)

print('\n%d/%d paires reconstruites' % (ok, len(pairs)), file=sys.stderr)

# ---------- consolidation par moyenne circulaire ponderee ----------
out = []
for i, r in enumerate(meta):
    if not est[i]:
        out.append(dict(file=r['file'], azimuth=None, n_est=0)); continue
    a = np.array([e[0] for e in est[i]]); w = np.array([e[1] for e in est[i]])
    C, S = (w*np.cos(a)).sum(), (w*np.sin(a)).sum()
    mean = math.atan2(S, C) % (2*math.pi)
    Rbar = math.hypot(C, S) / w.sum()              # 1 = parfaitement concordant
    disp = math.degrees(math.sqrt(max(0.0, -2*math.log(max(Rbar, 1e-9)))))  # ecart-type circulaire
    out.append(dict(file=r['file'], azimuth=math.degrees(mean), n_est=len(a),
                    concordance=round(Rbar, 3), sigma_deg=round(disp, 1),
                    lat=r['lat'], lon=r['lon'],
                    fov=math.degrees(2*math.atan((24.0 if r.get('portrait') else 36.0)
                                                 / (2*r.get('f35', 28.0))))))
json.dump(out, open('azimuths.json', 'w'), indent=1)

good = [o for o in out if o['azimuth'] is not None and o['n_est'] >= 2 and o['sigma_deg'] < 40]
print('\n%d/%d photos avec azimut ; %d fiables (>=2 estimations, sigma<40 deg)'
      % (sum(o['azimuth'] is not None for o in out), n, len(good)), file=sys.stderr)

# ---------- validation croisee independante ----------
errs = []
azd = {o['file']: o for o in out}
for i, j, R, ninl, base in rel:
    ai, aj = out[i]['azimuth'], out[j]['azimuth']
    if ai is None or aj is None: continue
    # rotation relative mesuree -> difference de cap predite
    pred = math.degrees(horiz_angle((R.T @ np.array([0, 0, 1.0]))))
    obs = (aj - ai + 180) % 360 - 180
    errs.append(abs((obs - pred + 180) % 360 - 180))
if errs:
    errs = np.array(errs)
    print('validation croisee (coherence des rotations relatives) :', file=sys.stderr)
    print('  erreur mediane %.1f deg | %.0f%% des paires sous 30 deg'
          % (np.median(errs), 100*(errs < 30).mean()), file=sys.stderr)
