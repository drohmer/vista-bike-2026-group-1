# The corpus

438 photos were taken during the ride by five cameras. **Only 53 carry a GPS fix.**
This single fact drives every downstream decision.

| contributor | photos | with GPS | without | first | last |
|---|---:|---:|---:|---|---|
| Emery | 359 | 0 | **359** | 15:34:43 | 18:54:23 |
| Damien | 48 | **48** | 0 | 15:37:54 | 18:48:23 |
| Rodrigo | 21 | 0 | **21** | 15:37:32 | 18:40:05 |
| nizar | 5 | 0 | **5** | 15:36:13 | 15:41:57 |
| Xavier | 5 | **5** | 0 | 15:35:48 | 15:49:23 |
| **Total** | **438** | **53** | **385** | | |

## Missing GPS is a camera setting, not a transfer loss

The split is binary per camera, never partial: a camera either tags every photo or none. On the 385 files without a fix, the rest
of the EXIF is **intact** — `make`, `model`, `software` and `datetime` are all present.
Had a transfer or an archive stripped the metadata, those fields would have gone too.
Location services were simply off on three of the five cameras.

Coordinates were searched in three independent places — the EXIF GPS IFD, the XMP
block, and a raw byte scan for `GPSLatitude` / `GPSLongitude` / `location`. **Zero hits
outside the standard IFD**, on all 438 files, none unreadable.

## No photo carries a heading

`GPSImgDirection` is absent from all 438 files. The scoring convention is therefore the
**50 m disk**, never the 60° / 150 m cone — confirmed by the official tool, which
reports `0 with a heading`.

## Duplicates and non-photos

- `IMG_6724` is a duplicate of `IMG_6723`.
- `IMG_6760 Dd` is a duplicate of `IMG_6760 Damien` with a **byte-identical file size**
  but a different MD5 — binary deduplication misses it; perceptual hashing (dHash,
  Hamming distance ≤ 5) is required.
- `IMG_6727` is a video, excluded.

That leaves **51 unique geolocated photos**, of which 30 are submitted.

## One ride, five cameras

Timestamps interleave across devices (15:37:32, 15:37:54, 15:35:48 …), so this is a
single outing, not several. Full span **15:34:43 → 18:54:23**, a 12.9 km loop whose
start and finish are 20 m apart.

The GPS track has **six gaps longer than 500 m**, the largest being 2,838 m between
15:58 and 16:18 and 2,501 m on the way back. 78 % of the route length falls inside a
gap longer than 300 m — which is why interpolating positions for the 385 GPS-less
photos degrades sharply on those stretches.

## Vegetation measurement: a caveat

Vegetation was scored with a normalised Excess Green index, which reduces exactly to
`3g - 1` — a threshold on green chromaticity at 0.35. It ranks images well (Spearman
0.93 against human judgement on 17 inspected photos) but has two measured failure modes
that matter on a canal route:

- **canal water clears the threshold** and counts as vegetation; from a bridge, trees
  and their reflection are both counted;
- **foliage in shade is underestimated** by up to 0.16, because sky-lit shadows push
  chromaticity towards blue.

Otsu thresholding and VARI were both tested and are worse here: Otsu returns 0.744
vegetation on a photo of the château (2 % in reality), VARI returns 0.551 on the same
image, its denominator changing sign over blue sky.
