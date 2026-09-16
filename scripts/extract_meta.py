#!/usr/bin/env python3
"""Per-photo metadata and image measurements.
Extracts EXIF (GPS, timestamp, altitude, focal length, speed, accuracy) and computes
per-image measurements: vegetation index, sharpness, exposure, appearance descriptor."""
import sys, os, math, json, csv
from PIL import Image, ImageFilter
import numpy as np

EXTS = {'.jpg', '.jpeg', '.png', '.heic', '.tif', '.tiff'}
BUDGET = int(sys.argv[2]) if len(sys.argv) > 2 else 30
FOLDER = sys.argv[1]

# ---------- 1. EXIF ----------
def rat(x):
    try: return float(x)
    except Exception: return float(x[0]) / float(x[1])

def dms(v, ref):
    d = rat(v[0]) + rat(v[1]) / 60 + rat(v[2]) / 3600
    return -d if ref in ('S', 'W') else d

def exif_of(p):
    out = {}
    try:
        im = Image.open(p)
        ex = im.getexif()
        dt = None
        for ifd in (ex, ex.get_ifd(0x8769)):
            if not ifd: continue
            for tag in (36867, 36868, 306):
                if tag in ifd: dt = ifd[tag]; break
            if dt: break
        out['datetime'] = dt
        g = ex.get_ifd(0x8825)
        if g and 2 in g and 4 in g:
            out['lat'] = dms(g[2], g.get(1, 'N'))
            out['lon'] = dms(g[4], g.get(3, 'E'))
            if 6 in g:
                alt = rat(g[6])
                out['alt'] = -alt if g.get(5, 0) == 1 else alt
        if g and 17 in g:  # GPSImgDirection = camera heading (absent here)
            out['heading'] = rat(g[17])
        if g and 13 in g: out['speed'] = rat(g[13])      # GPSSpeed
        if g and 31 in g: out['gps_err'] = rat(g[31])    # GPSHPositioningError
        ex2 = ex.get_ifd(0x8769)
        if ex2 and 41989 in ex2:                          # 35 mm-equivalent focal length
            f35 = float(ex2[41989])
            if f35 > 0:
                out['f35'] = f35
                # horizontal field of view (36 mm reference)
                out['fov'] = math.degrees(2 * math.atan(36.0 / (2 * f35)))
        out['model'] = str(ex.get(272) or '')
    except Exception as e:
        out['exif_error'] = str(e)
    return out

# ---------- 2. Image content: vegetation + sharpness ----------
def content_of(p):
    im = Image.open(p)
    im.draft('RGB', (512, 512))          # fast JPEG decoding
    im = im.convert('RGB')
    im.thumbnail((400, 400))
    a = np.asarray(im, dtype=np.float32) / 255.0
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    S = R + G + B + 1e-6
    # normalised Excess Green (standard RGB vegetation index)
    exg = 2 * (G / S) - (R / S) - (B / S)
    veg_mask = exg > 0.05
    veg_frac = float(veg_mask.mean())
    veg_strength = float(np.clip(exg, 0, None).mean())
    # sharpness: edge-response variance
    gray = np.asarray(im.convert('L').filter(ImageFilter.FIND_EDGES), dtype=np.float32)
    sharp = float(gray.var())
    expo = float(a.mean())
    # Appearance descriptor: HSV histogram on a 2x2 grid.
    # NOTE: this was used as a proxy for view angle and was later INVALIDATED --
    # it measures brightness and colour, not orientation. Kept for reference only.
    hsv = np.asarray(im.convert('HSV').resize((64, 64), Image.BILINEAR), dtype=np.float32)
    desc = []
    for gy in range(2):
        for gx in range(2):
            c = hsv[gy*32:(gy+1)*32, gx*32:(gx+1)*32]
            hh, _ = np.histogram(c[..., 0], bins=8, range=(0, 256))
            ss, _ = np.histogram(c[..., 1], bins=4, range=(0, 256))
            vv, _ = np.histogram(c[..., 2], bins=4, range=(0, 256))
            desc += list(hh) + list(ss) + list(vv)
    desc = np.asarray(desc, dtype=np.float32)
    desc /= desc.sum() + 1e-9

    # 8x8 dHash: perceptual signature, robust to JPEG re-encoding
    g = np.asarray(im.convert('L').resize((9, 8), Image.BILINEAR), dtype=np.int16)
    dh = ''.join('1' if c else '0' for c in (g[:, 1:] > g[:, :-1]).ravel())
    return dict(dhash=dh, desc=[round(float(v), 6) for v in desc],
                portrait=bool(im.size[1] > im.size[0]), veg_frac=veg_frac, veg_strength=veg_strength,
                sharp=sharp, expo=expo, w=im.size[0], h=im.size[1])

# ---------- 3. Geometry ----------
def to_xy(lats, lons):
    lat0 = np.mean(lats)
    x = (np.asarray(lons) - np.mean(lons)) * 111320 * math.cos(math.radians(lat0))
    y = (np.asarray(lats) - lat0) * 110540
    return x, y


def main():
    files = sorted(f for f in os.listdir(FOLDER)
                   if os.path.splitext(f)[1].lower() in EXTS and not f.startswith('.'))
    recs = []
    for f in files:
        p = os.path.join(FOLDER, f)
        if os.path.getsize(p) == 0:
            print(f"!! {f} : unhydrated placeholder -> SKIPPED", file=sys.stderr); continue
        r = {'file': f, 'bytes': os.path.getsize(p)}
        r.update(exif_of(p))
        try:
            r.update(content_of(p))
        except Exception as e:
            r['content_error'] = str(e)
        if 'lat' not in r: print(f"!! {f} : no GPS", file=sys.stderr)
        if not r.get('datetime'): print(f"!! {f} : no timestamp", file=sys.stderr)
        recs.append(r)
        print(f"ok {f}", file=sys.stderr)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'meta_photos.json')
    json.dump(recs, open(out + '.tmp', 'w'), indent=1)
    os.replace(out + '.tmp', out)          # atomic write
    print(f"\n{len(recs)} images -> {out}", file=sys.stderr)

main()
