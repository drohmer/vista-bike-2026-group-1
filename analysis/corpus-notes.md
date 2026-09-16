# Passation — faits établis sur les 53 photos

Note écrite pour l'agent qui construit la carte du Scandibérique Map Challenge.
Tout ce qui suit a été **mesuré** sur les fichiers, pas supposé.
Données brutes : `doc/donnees/meta_photos.json` (EXIF + scores par photo).

---

## 1. Ce qui décide de la convention de scoring

**Aucune des 53 photos ne contient de `GPSImgDirection`.** Vérifié par dump EXIF brut,
sur les deux appareils. La convention applicable est donc le **disque de 50 m**, jamais
le cône de 60° / 150 m.

Conséquence chiffrée, grille de 50 m :

| | cellules observées |
|---|---|
| les 51 photos uniques | 93 |
| 30 photos (sélection actuelle) | 86 |
| optimum à 30 photos | 91 |

**Soit 0,7 % des 12 221 cellules. 99,3 % de la carte est à inférer.**
Le choix des 30 photos est donc un levier quasi nul — ne pas y passer de temps.

⚠️ **Ambiguïté à lever auprès de Xi** : « disque de 50 m » = rayon ou diamètre ?
Si c'est un diamètre (rayon 25 m), la couverture tombe à 21-24 cellules et
**9 des 30 photos actuelles n'apportent aucune cellule** — là, re-sélectionner
rapporte +14 %.

---

## 2. Pièges de classification (le point le plus utile de cette note)

**L'eau du canal est comptée comme végétation par tout indice vert RGB.**
Mesuré sur Excess Green : la surface du canal passe le seuil, et sur une photo prise
depuis un pont **les arbres et leur reflet sont comptés deux fois**. Comme `water` et
`broadleaf` sont deux des cinq classes et que l'IoU est moyenné, c'est l'erreur la plus
coûteuse possible ici. Un indice couleur seul ne séparera pas water de broadleaf.

Autres mesures faites sur ces photos :

- **Le feuillage à l'ombre est perdu** (jusqu'à −0,16 d'ExG) : le ciel éclaire l'ombre
  à ~15 000 K, la chromaticité verte chute sous le seuil. Sous-bois sous-estimés.
- **Le ciel bleu n'est jamais faussement compté** comme végétation.
- **Tout objet jaune ou ocre passe le seuil** — une borne jaune de trottoir est
  classée végétation à 100 %.
- **Otsu et VARI sont inutilisables ici** : Otsu donne 0,744 de végétation sur la photo
  du château (2 % réels), VARI donne 0,551 sur la même, son dénominateur changeant de
  signe sur le ciel bleu. Le seuil fixe ExG > 0,05 est nettement meilleur.
- ExG normalisé se réduit exactement à `3g − 1` : c'est un seuil sur la chromaticité
  verte à 0,35, rien de plus.

---

## 3. Bug à ne pas reproduire

**32 des 53 photos ont `Orientation = 6`** (portrait iPhone stocké en paysage).
Sans `ImageOps.exif_transpose()` :
- tout drapeau portrait/paysage est faux sur 60 % du corpus ;
- toute grille spatiale (2×2, 4×4, patches) est **tournée de 90°** entre photos
  d'orientations différentes, ce qui rend les comparaisons inter-photos incohérentes.

Appliquer `exif_transpose` avant toute analyse pixel.

---

## 4. Ce que contient le corpus

- **53 fichiers, 51 photos uniques.** Doublons : `IMG_6724` ≡ `IMG_6723`, et
  `IMG_6760 Dd` ≡ `IMG_6760 Damien`. Ce dernier a une taille **identique à l'octet**
  mais un MD5 différent — une déduplication binaire le manque, il faut du perceptuel
  (dHash ≤ 5 bits).
- `IMG_6727 Damien.mov` est une **vidéo**, à exclure.
- **Une seule sortie**, le 15/09/2026 de 15h35 à 18h48. Les deux appareils
  s'entrelacent (15:37:37 puis 15:37:54) — ce ne sont pas deux parcours.
- Boucle de 12,9 km, départ et arrivée à 20 m l'un de l'autre.
- **Six trous de plus de 500 m** sans aucune photo, dont 2 838 m (15h58→16h18) et
  2 501 m sur le retour. 78 % de la longueur du parcours est dans un trou > 300 m.

## Contenu visuel constaté (17 photos examinées)

Château médiéval, canal, écluses et leur machinerie, silos à grain, rue de bourg avec
maisons et jardins, chemin de halage, allée de platanes, sous-bois, moulin, pont,
lentilles d'eau et canards, gravières éventuelles.

➜ Classes présentes : **built, water, broadleaf, open**.
➜ **`conifer` n'a été vu sur aucune des photos examinées.** À vérifier sur les 36
restantes : si aucun conifère n'est photographié, l'IoU de cette classe reposera
entièrement sur le prior, et elle pèse un cinquième du score.

Rappel du PDF : sur leur test à 36 photos, CLIP a rendu 21 built / 8 water / 5 forest /
2 open, et les deux « open » étaient des photographies de tableaux.

---

## 5. Métadonnées utiles disponibles

Par photo, dans `meta_photos.json` : lat, lon, altitude (57 à 111 m — terrain plat),
horodatage, `f35` (focale équivalente 35 mm, **de 13 à 105 mm** — l'Android est un
ultra-grand-angle, l'iPhone monte au télé), vitesse GPS, précision GPS (≈ 4,7 m),
`veg_frac`, netteté, exposition.

`doc/donnees/scores-51-photos.csv` reprend tout à plat, avec la colonne `doublon_de`.

---

## 6. Ce qui a été tenté et qui ne marche pas

- **Estimer les azimuts a posteriori** (SIFT + matrice essentielle + ancrage GPS) :
  9 paires reconstruites sur 117, **2 photos réellement déterminées sur 53**. Un
  bootstrap par paire donne des dispersions de 44 à 113°, soit uniformes sur le cercle.
  Ne pas espérer récupérer les headings par cette voie sans passer à COLMAP avec priors
  GPS, et même là le plafond estimé est de 35-40 photos.
- **Piste non explorée, et la plus prometteuse si le heading devient utile** : le
  **soleil**. Le 15 septembre à 48,24° N entre 15h35 et 18h48, son azimut va de 215° à
  260° et sa hauteur de 39° à 12°. Ombres portées et contre-jours donnent l'azimut
  absolu d'une seule photo, sans appariement.

---

## 7. Avertissement d'intégrité

Trois agents d'audit lancés dans la session d'origine **avaient accès au web**. Ils
l'ont utilisé pour des questions de méthode (COLMAP, indices de végétation,
optimisation sous-modulaire), mais l'un d'eux a identifié le lieu comme le canal du
Loing. Cette identification est plausiblement déduite du contenu des photos, mais
**on ne peut pas garantir qu'aucune carte n'a été consultée**. À arbitrer au regard des
règles, qui interdisent cartes, imagerie satellite, Wikipédia et moteurs de recherche.

---

## 8. Ce qui est déjà sur le disque

Dans `/Users/damien/Dropbox/File requests/2026-retreat-vista-photo/` :

- `selection-30/` — les 30 photos remises (175 Mo). Elles couvrent 92 % des cellules
  atteignables avec un budget de 30. Si l'équilibre des cinq classes devient le critère
  prioritaire, une re-sélection sur cette base reste possible.
- `doc/` — méthodologie, figures, scripts, données.
