# VISTA Bike 2026 — Groupe 1

Les 30 photos remises pour le **Scandibérique Map Challenge**, et l'analyse du corpus
qui va avec.

Balade du **15 septembre 2026**, 15 h 35 → 18 h 48, le long du canal. Boucle de
**12,9 km**, deux appareils (iPhone 16 Pro et un Android), **53 photos prises**,
**51 uniques**, **30 remises**.

![Les 30 photos remises](analysis/contact-sheet.jpg)

---

## Ce qu'il faut savoir avant de construire la carte

Quatre faits mesurés sur les fichiers, qui pèsent plus sur le score que le choix des
photos lui-même.

### 1. Aucune photo ne porte de cap boussole

Vérifié par lecture EXIF brute sur les 53 fichiers, les deux appareils confondus :
`GPSImgDirection` est **absent partout**. La convention de scoring applicable est donc
le **disque de 50 m**, jamais le cône de 60° / 150 m.

Conséquence, sur une grille de cellules de 50 m :

| | cellules observées |
|---|---:|
| les 51 photos uniques | 93 |
| **les 30 remises** | **86** |
| optimum théorique à 30 photos | 91 |

**Soit 0,7 % des 12 221 cellules de la grille.** Autrement dit **99,3 % de la carte
relève du prior**, pas de l'observation. Le choix des 30 photos est un levier quasi
nul ; l'écart entre notre sélection et l'optimum vaut 5 cellules, soit 0,04 % de la
carte.

> ⚠️ **À lever auprès de l'organisation** : « disque de 50 m » désigne-t-il un rayon ou
> un diamètre ? Si c'est un diamètre, la couverture tombe à 21–24 cellules et 9 des 30
> photos n'apportent plus aucune cellule nouvelle.

### 2. Deux des cinq classes sont mal couvertes

Constat visuel sur les 30 photos remises (voir la planche ci-dessus) :

| classe | présence dans le corpus |
|---|---|
| `water` | très forte — le canal est sur presque toutes les photos |
| `built` | forte — bourg, colombages, château, silos, rues |
| `broadleaf` | forte — platanes et feuillus de berge |
| `open` | **faible** — quasiment aucun champ cadré |
| `conifer` | **absente** — aucun conifère repéré sur les 30 |

L'IoU étant moyenné sur les cinq classes, `conifer` et `open` valent chacune un
cinquième du score et reposeront presque entièrement sur le prior. C'est exactement
l'écueil annoncé dans les slides (« personne ne pointe un appareil vers un champ »).

### 3. L'eau du canal se fait passer pour de la végétation

Mesuré, pas supposé : sur l'indice *Excess Green*, la surface du canal franchit le
seuil de chromaticité verte, et sur une photo prise depuis un pont **les arbres et
leur reflet sont comptés deux fois**. Tout classifieur fondé sur un indice couleur RGB
confondra `water` et `broadleaf` — les deux classes les plus représentées ici.

Également mesuré sur ce corpus :

- le feuillage à l'ombre est **sous-estimé** (jusqu'à −0,16) : le ciel éclaire l'ombre
  à ~15 000 K, la chromaticité verte chute sous le seuil ;
- le ciel bleu n'est **jamais** faussement compté comme végétation ;
- tout objet jaune ou ocre franchit le seuil (une borne de trottoir sort à 100 %) ;
- **Otsu et VARI sont inutilisables ici** : Otsu donne 0,744 de végétation sur la photo
  du château (2 % réels), VARI donne 0,551 sur la même, son dénominateur changeant de
  signe sur le ciel bleu.

### 4. 32 photos sur 53 sont en orientation EXIF 6

Portrait iPhone stocké en paysage. Sans `ImageOps.exif_transpose()`, tout découpage
spatial (grille, patches) se retrouve **tourné de 90°** entre photos d'orientations
différentes, et les comparaisons inter-photos deviennent incohérentes.

---

## La sélection des 30

Les 30 photos ont été choisies par **programmation dynamique exacte** sur la séquence
ordonnée, en minimisant l'erreur de simplification de la polyligne du parcours sous
contrainte dure, à végétation maximale.

| | erreur du tracé | couverture < 150 m | végétation |
|---|---:|---:|---:|
| les 51 photos | 0,0 m | 55,0 % | 0,306 |
| **les 30 remises** | **8,2 m** | **53,2 %** | 0,329 |

```
python3 scripts/choose_v4.py 30 500 10
```

---

## Contenu du dépôt

```
photos/                  les 30 originaux, EXIF intact
data/
  selection-30.txt       la liste
  photo_metadata.json    EXIF + mesures, les 53 photos
  photo_scores.csv       tout à plat, avec la colonne doublon_de
analysis/
  contact-sheet.jpg      la planche ci-dessus
  methodologie.html      méthode complète, à ouvrir dans un navigateur
  corpus-notes.md        notes détaillées sur le corpus
  figures/               tracé GPS, champs de vue, azimuts
scripts/
  extract_meta.py        EXIF + mesures  →  photo_metadata.json
  choose_v4.py           sélection par DP exacte
  compare.py             métriques et front de Pareto
  azimuth.py, synth.py   estimation des azimuts, et sa validation
```

Les photos sont les **originaux**, EXIF préservé — les applications de messagerie et
les copies « optimisées » suppriment la balise GPS, qui est ici la seule information
de position.

---

## Le corpus

- **53 fichiers, 51 photos uniques.** Doublons écartés : `IMG_6724` ≡ `IMG_6723`, et
  `IMG_6760 Dd` ≡ `IMG_6760 Damien`. Ce second cas a une taille **identique à l'octet**
  mais un MD5 différent : une déduplication binaire le manque, il faut du perceptuel
  (dHash, distance de Hamming ≤ 5).
- `IMG_6727 Damien.mov` est une vidéo, exclue.
- **Une seule sortie** : les horodatages des deux appareils s'entrelacent
  (15:37:37 puis 15:37:54).
- Boucle refermée — départ et arrivée à 20 m l'un de l'autre.
- **Six trous de plus de 500 m** sans aucune photo, dont 2 838 m entre 15 h 58 et
  16 h 18, et 2 501 m sur le retour. 78 % de la longueur du parcours se trouve dans un
  trou de plus de 300 m.
- Terrain plat : altitudes de 57 à 111 m.
- Focales équivalentes de **13 à 105 mm** — l'Android est un ultra-grand-angle,
  l'iPhone monte au téléobjectif.
- Précision GPS annoncée ≈ **4,7 m**.

---

## Récupérer les caps : tenté, non concluant

Estimation *a posteriori* par appariement SIFT, matrice essentielle et ancrage sur les
positions GPS : **9 paires reconstruites sur 117, et 2 photos réellement déterminées
sur 53**. Un bootstrap par paire donne des dispersions de 44 à 113°, soit uniformes sur
le cercle.

La cause est structurelle : les paires qui s'apparient le mieux sont à baseline nulle,
donc dégénérées pour la translation, tandis que les paires à longue baseline — les
seules capables d'ancrer un azimut — ne s'apparient qu'à 15 %.

Une voie non explorée, sans appariement : **le soleil**. Le 15 septembre à 48,24° N
entre 15 h 35 et 18 h 48, son azimut passe de 215° à 260° et sa hauteur de 39° à 12°.
Ombres portées et contre-jours donnent l'azimut absolu d'une seule photo. Plusieurs
photos du corpus montrent le soleil directement dans le cadre.

`scripts/synth.py` valide la chaîne géométrique sur données synthétiques à vérité
terrain connue.
