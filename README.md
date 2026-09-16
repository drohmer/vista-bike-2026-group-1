# VISTA Bike 2026 — Group 1

The 30 photos submitted for the **Scandibérique Map Challenge**, together with the
analysis of the corpus they come from.

Ride of **15 September 2026**, 15:35 → 18:48, along the canal. A **12.9 km** loop, two
cameras (an iPhone 16 Pro and an Android phone), **53 photos taken**, **51 unique**,
**30 submitted**.

![The 30 submitted photos](analysis/contact-sheet.jpg)

---

## What to know before building the map

Four facts measured on the files themselves. Each weighs more on the score than the
choice of photos does.

### 1. No photo carries a compass heading

Verified by raw EXIF read across all 53 files, both cameras: `GPSImgDirection` is
**absent everywhere**. The applicable scoring convention is therefore the **50 m disk**,
never the 60° / 150 m cone.

Consequence, on a grid of 50 m cells:

| | observed cells |
|---|---:|
| the 51 unique photos | 93 |
| **the 30 submitted** | **86** |
| theoretical optimum at 30 photos | 91 |

**That is 0.7 % of the 12,221 cells.** In other words **99.3 % of the map comes from
the prior**, not from observation. Which 30 photos we hand in is therefore a near-zero
lever: the gap between our selection and the optimum is 5 cells, or 0.04 % of the map.

> ⚠️ **To clarify with the organisers**: does "50 m disk" mean a radius or a diameter?
> If it is a diameter, coverage drops to 21–24 cells and 9 of the 30 photos stop
> contributing any new cell at all.

### 2. Two of the five classes are poorly covered

Visual inspection of the 30 submitted photos (see the contact sheet above):

| class | presence in the corpus |
|---|---|
| `water` | very strong — the canal is in almost every frame |
| `built` | strong — village, half-timbered houses, château, grain silos, streets |
| `broadleaf` | strong — plane trees and riverbank hardwoods |
| `open` | **weak** — almost no field is framed |
| `conifer` | **absent** — no conifer found in any of the 30 |

Since IoU is averaged over the five classes, `conifer` and `open` are worth one fifth
of the score each and will rest almost entirely on the prior. This is exactly the trap
the slides warn about ("nobody points a camera at a field").

### 3. Canal water passes for vegetation

Measured, not assumed: under the *Excess Green* index, the canal surface clears the
green-chromaticity threshold, and in a photo taken from a bridge **the trees and their
reflection are both counted**. Any classifier built on an RGB colour index will confuse
`water` with `broadleaf` — the two best-represented classes here.

Also measured on this corpus:

- foliage in shade is **underestimated** (by up to −0.16): the sky lights shadows at
  ~15,000 K, green chromaticity drops below the threshold;
- blue sky is **never** falsely counted as vegetation;
- any yellow or ochre object clears the threshold (a kerbside bollard scores 100 %);
- **Otsu and VARI are unusable here**: Otsu returns 0.744 vegetation on the château
  photo (2 % in reality), VARI returns 0.551 on the same image, its denominator
  flipping sign over blue sky.

### 4. 32 of the 53 photos are EXIF orientation 6

iPhone portrait stored as landscape. Without `ImageOps.exif_transpose()`, any spatial
subdivision (grid, patches) ends up **rotated by 90°** between photos of differing
orientation, and cross-photo comparisons become incoherent.

---

## Selecting the 30

The 30 photos were chosen by **exact dynamic programming** over the ordered sequence,
minimising the polyline simplification error of the route under a hard constraint, at
maximum vegetation.

| | route error | coverage < 150 m | vegetation |
|---|---:|---:|---:|
| all 51 photos | 0.0 m | 55.0 % | 0.306 |
| **the 30 submitted** | **8.2 m** | **53.2 %** | 0.329 |

```
python3 scripts/choose_v4.py 30 500 10
```

---

## Repository contents

```
photos/                  the 30 originals, EXIF intact
data/
  selection-30.txt       the list
  photo_metadata.json    EXIF + measurements, all 53 photos
  photo_scores.csv       flat table, including a duplicate-of column
analysis/
  contact-sheet.jpg      the sheet above
  methodologie.html      full method, open in a browser (French)
  corpus-notes.md        detailed corpus notes (French)
  figures/               GPS track, fields of view, azimuths
scripts/
  extract_meta.py        EXIF + measurements  →  photo_metadata.json
  choose_v4.py           selection by exact DP
  compare.py             metrics and Pareto front
  azimuth.py, synth.py   azimuth estimation, and its validation
```

The photos are the **originals**, EXIF preserved — messaging apps and "optimised"
copies strip the GPS tag, which is the only positional information available here.

---

## The corpus

- **53 files, 51 unique photos.** Duplicates removed: `IMG_6724` ≡ `IMG_6723`, and
  `IMG_6760 Dd` ≡ `IMG_6760 Damien`. That second case has a **byte-identical file size**
  but a different MD5: binary deduplication misses it, perceptual hashing is required
  (dHash, Hamming distance ≤ 5).
- `IMG_6727 Damien.mov` is a video, excluded.
- **A single ride**: timestamps from the two cameras interleave (15:37:37 then
  15:37:54).
- Closed loop — start and finish are 20 m apart.
- **Six gaps longer than 500 m** with no photo at all, including 2,838 m between 15:58
  and 16:18, and 2,501 m on the way back. 78 % of the route length falls inside a gap
  longer than 300 m.
- Flat terrain: elevations from 57 to 111 m.
- 35 mm-equivalent focal lengths from **13 to 105 mm** — the Android is an ultra-wide,
  the iPhone reaches telephoto.
- Reported GPS accuracy ≈ **4.7 m**.

---

## Recovering headings: attempted, inconclusive

Post-hoc estimation via SIFT matching, the essential matrix and anchoring on GPS
positions: **9 pairs reconstructed out of 117, and 2 photos genuinely determined out of
53**. A per-pair bootstrap gives dispersions of 44° to 113°, i.e. uniform on the circle.

The cause is structural: the pairs that match best sit at zero baseline, hence
degenerate for translation, while long-baseline pairs — the only ones able to anchor an
azimuth — match at only 15 %.

One avenue left unexplored, requiring no matching: **the sun**. On 15 September at
48.24° N between 15:35 and 18:48, its azimuth runs from 215° to 260° and its elevation
from 39° to 12°. Cast shadows and backlighting yield the absolute azimuth of a single
photo on its own. Several photos in this corpus have the sun directly in frame.

`scripts/synth.py` validates the geometric chain against synthetic data with known
ground truth.
