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
of the EXIF is **intact** — `make`, `model` and `datetime` are present on all of them
(`software` is missing on 26 files of the whole corpus, which is a camera-brand
difference, not a stripping artefact).
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
single outing, not several. Full span **15:34:43 → 18:54:23**, a **12,959 m** loop whose start and finish are
19.6 m apart (geodesic distances, WGS84).

The GPS track has **six gaps longer than 500 m** — 2,855 m (15:58→16:18), 2,515 m
(18:40→18:48), 1,045 m, 1,002 m, 674 m and 579 m. **78.5 % of the route length falls
inside a gap longer than 300 m** — which is why interpolating positions for the 385 GPS-less
photos degrades sharply on those stretches.

## Vegetation measurement: a caveat

Vegetation was scored with a normalised Excess Green index, which reduces exactly to
`3g - 1` — a threshold on green chromaticity at 0.35. It ranks images sensibly, but has two failure modes that matter on a canal route
(both reproducible from the photos in this repository):

- **canal water clears the threshold** and counts as vegetation: the water half of
  `IMG_6711` scores 0.80, `IMG_6725` 0.46. From a bridge, trees and their reflection
  are both counted;
- **foliage in shade is underestimated**, because sky-lit shadows push chromaticity
  towards blue.

Otsu thresholding and VARI were both tested and are worse here. On `IMG_6749`, a photo
of the castle with 1.6 % actual vegetation, Otsu returns **0.745** — it forces a bimodal
split onto a unimodal histogram — and VARI returns **0.553** at the same threshold.
The fixed threshold is clearly the better choice on this corpus.
