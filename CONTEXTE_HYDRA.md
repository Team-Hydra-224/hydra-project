# CONTEXTE PROJET — HYDRA

> **À lire en premier par l'assistant IA (Claude Code / Antigravity).**
> Ce fichier contient tout le contexte nécessaire pour développer le logiciel HYDRA.
> Il résume des semaines de conception : l'idée, la science, les décisions techniques,
> les bugs déjà rencontrés et résolus, l'architecture, et le code de référence validé.
> **Ne pas réinventer ce qui est déjà décidé ici. Respecter les choix verrouillés.**

---

## 1. C'EST QUOI HYDRA

**HYDRA** (*Hydrogeological Data & Research for Africa*) est un logiciel d'aide à la
décision pour **réduire les forages d'eau ratés en Guinée** (puis Afrique de l'Ouest,
puis tout le continent).

**Principe :** à partir de **coordonnées GPS + un rayon**, le logiciel analyse des
données satellites, croise plusieurs facteurs hydrogéologiques, et produit :
- une **carte de probabilité** de présence d'eau souterraine,
- une liste de **points GPS candidats** (Top 5) classés par score,
- un **rapport PDF** exportable.

Ces points candidats sont ensuite confirmés sur le terrain par un **SEV**
(Sondage Électrique Vertical) avant que le foreur ne fore.

**Tagline :** *Trouver l'eau avant de forer.*

### Modèle économique
- Clients : foreurs, particuliers/villages/agriculteurs, ONG/gouvernement.
- Stratégie MVP sans budget : se greffer sur des marchés de forage existants. Le
  partenaire en Guinée propose aux foreurs l'étude de ciblage préalable ; HYDRA cible
  via le logiciel + engage un technicien SEV ponctuel ; récupère les données du forage
  pour valider/améliorer le modèle.
- Vision : Guinée → Afrique de l'Ouest → toute l'Afrique → diversification au-delà de
  l'eau (autres ressources du sous-sol). **PAS d'achat de machines de forage.**

### Équipe
3 personnes : porteur de projet (France), un technique (France), un terrain (Guinée).

---

## 2. CONTEXTE SCIENTIFIQUE (à garder en tête)

On ne « voit » PAS l'eau directement depuis l'espace. On détecte des **indices de
surface** qui trahissent une eau souterraine probable :
- **Fractures de la roche** (l'eau circule dans les failles, surtout en socle cristallin),
- **Zones basses / cuvettes** où l'eau s'accumule par gravité,
- **Végétation verte en saison sèche** (racines alimentées par une nappe),
- **Type de roche et de sol**, zones d'infiltration vs ruissellement.

Le satellite **réduit le champ de recherche**. Le **SEV confirme** avant de forer.
C'est la combinaison qui fait la fiabilité. Limite clé : le satellite ne donne ni la
profondeur exacte, ni le débit, ni la certitude qu'une fracture contient de l'eau.

### Contexte géologique guinéen
La Guinée a 4 grands contextes : Fouta Djalon (dolérite + grès), Basse Guinée
(sédimentaire + granite), Haute Guinée (socle précambrien), Guinée Forestière
(granite + schistes). **Les poids du modèle sont calibrés pour le socle cristallin /
Fouta Djalon.** Appliquer le même modèle ailleurs nécessite une **recalibration**
(concept de « profils de calibration » par pays/région).

---

## 3. CAS D'ÉTUDE FONDATEUR — Donghol Dayebhé (Labé, Guinée)

Village du Fouta Djalon où **2 forages à 120 m ont échoué** à cause de la **dolérite**
(roche magmatique très dure, 6–7 Mohs, quasi-imperméable ; l'eau n'y circule que dans
les fractures). C'est le cas réel qui a tout déclenché et qui sert de validation.

### Coordonnées de référence
```
Forage actuel (ÉCHEC) : latitude 11.255046, longitude -12.281277   (altitude ~1120 m)
Point SEV techniciens : latitude 11.25821,  longitude -12.28593
Rayon d'analyse       : 1000 m
Compte GEE utilisé    : ee-hydrogeologie-guinee
```

### Résultats obtenus (modèle V1 déterministe, score 0–1)
| Point | Score V1 | Verdict |
|---|---|---|
| Forage actuel | **0.393** | 🟠 MOYEN (zone défavorable confirmée) |
| Point SEV techniciens | **0.400** | 🟠 MOYEN (légèrement mieux que le forage) |

**Top 5 candidats GPS extraits automatiquement (rayon 1 km) :**
| # | Latitude | Longitude | Score V1 | Altitude | NDVI | Distance forage |
|---|---|---|---|---|---|---|
| C1 | 11.252305 | -12.284060 | **0.616** | 1076 m | 0.564 | 429 m |
| C2 | 11.249088 | -12.279433 | 0.586 | 1120 m | 0.378 | 689 m |
| C3 | 11.263202 | -12.278540 | 0.575 | 1118 m | 0.478 | 950 m |
| C4 | 11.252828 | -12.280190 | 0.559 | 1109 m | **0.641** | 273 m |
| C5 | 11.253069 | -12.278486 | 0.516 | 1125 m | 0.483 | 375 m |

Recommandation terrain : SEV prioritaire sur **C4** (le plus proche + meilleur NDVI),
puis **C1** (meilleur score global).

---

## 4. LES FACTEURS — DÉCISIONS VERROUILLÉES

### 4.1 Facteurs RETENUS pour la V1 (tous haute résolution, variance locale réelle)

**6 facteurs séparés, un module Python par facteur (architecture modulaire — Option A).**
**(Décision de réanalyse : l'indice de ruissellement a été SUPPRIMÉ pour colinéarité —
il recombinait pente/LULC/sol déjà comptés dans C2, C5, C6. Ses 5% ont été redistribués.)**

| Code | Facteur | Source(s) | Résolution | Poids |
|---|---|---|---|---|
| **C1** | Linéaments / fractures (densité) — **masquer bâti+cultures AVANT détection** | ALOS PALSAR bande L + Sentinel-2 (fusion radar 40% / optique 60%) | 10–25 m | **35%** |
| **C2** | Topographie : altitude + pente + TWI (**MERIT Hydro `upa`**, pas d'approximation) + courbure + géomorphologie | SRTM + MERIT Hydro | 30–90 m | **18%** |
| **C3** | Hydrographie : densité drainage + distance rivières (**MERIT Hydro 90 m**, PAS HydroSHEDS 463 m) | MERIT Hydro v1.0.1 | 90 m | **10%** |
| **C4** | Végétation : NDVI saison sèche + NDWI Gao + Saisonnalité NDVI | Sentinel-2 | 10 m | **20%** |
| **C5** | LULC (occupation des sols) + masque eau (exclusion stricte) | ESA WorldCover 2021 (→ Google Dynamic World en V2) | 10 m | **12%** |
| **C6** | Pédologie (texture sable vs argile) | SoilGrids ISRIC | 250 m | **5%** |

> **Total = 100%.** Les poids doivent être **configurables** (sliders Streamlit), jamais codés en dur.

#### Détails sous-pondérations
- **C1 :** masque anthropique obligatoire avant Sobel : `lulc.neq(50).And(lulc.neq(40))` (élimine routes/bâti/cultures = faux linéaments).
- **C2 :** Altitude 25% (inversée : bas = favorable) · Pente 20% (inversée : faible = favorable) · TWI 25% (via `ee.Image('MERIT/Hydro/v1_0_1').select('upa')`) · Courbure planaire+profilée 20% · Géomorphologie 10%.
- **C3 :** Distance rivières (proche = favorable) + densité de drainage, depuis MERIT Hydro `upa` seuillé. Bug `fastDistanceTransform` à éviter (voir §6 point 8).
- **C4 :** NDVI sèche 40% · NDWI Gao 30% · Saisonnalité NDVI 30%.
- **C5 :** scoring infiltration par classe LULC (voir §6 et §7.6). Eau = masque d'exclusion.
- **C6 :** sable - argile normalisé (sable = perméable = favorable).

#### ⚠️ Décisions de réanalyse (validées, à respecter dans le code)
1. **Scores RELATIFS** : la normalisation par percentiles locaux rend le score relatif
   à la zone analysée, PAS une probabilité absolue. L'UI et le PDF doivent afficher
   « score relatif à la zone » + des **indicateurs absolus** par candidat (NDVI brut,
   pente brute, distance rivière en m). V2 : bornes régionales fixes.
2. **Masque anthropique sur C1** avant détection des linéaments (routes ≠ fractures).
3. **MERIT Hydro** remplace l'approximation gaussienne du TWI ET HydroSHEDS 15ACC
   (463 m → 90 m, conforme à notre règle d'or résolution vs zone).
4. **C6 ruissellement supprimé** (colinéarité) ; poids redistribués C2 18% / C4 20%.
5. **Architecture 2 phases** (voir §5) : couches coûteuses cachées / combinaison instantanée.
6. **Licence GEE** : gratuit en développement/validation (non commercial). L'usage
   commercial (vente d'études) exigera un plan Earth Engine payant via Google Cloud
   (~dizaines de $/mois à notre échelle). À inscrire au business plan.

### 4.2 Facteurs ÉCARTÉS de la V1 (raison MATHÉMATIQUE, pas géologique)

> **Règle d'or :** un facteur dont la résolution (taille de pixel) est ≥ à la zone
> d'étude donne une **valeur constante** sur tous les pixels → **variance nulle** → ne
> discrimine rien ET fait **diviser par zéro** à la normalisation `(val-min)/(max-min)`.
> On n'intègre JAMAIS un tel facteur pour un rayon de 1 km.

| Facteur écarté | Donnée | Résolution | Pourquoi écarté en V1 |
|---|---|---|---|
| Anomalie magnétique | EMAG2 / WDMAM | ~3,7 km/pixel | Constante sur 1 km → variance nulle |
| Géologie de surface | USGS Global Geology | ~1 km/pixel | Trop grossier + classes simplifiées |
| Précipitations | CHIRPS / ERA5 | ~5 km | Pluie quasi-constante à 1 km en Guinée (pays très arrosé) |
| Évapotranspiration | MODIS ET | ~500 m–1 km | Constante à 1 km |
| Gravimétrie | GRACE / GRACE-FO | 300–400 km/pixel | Inutilisable (pire qu'EMAG2) |
| Gravimétrie | BGI | variable | Couverture Guinée trop inégale |

> Ces facteurs **régionaux** pourraient revenir **conditionnellement** si le rayon
> d'analyse devient large (5–10 km). À cette échelle ils retrouvent de la variance.

### 4.3 Roadmap des versions

**V1 — Modèle déterministe (MAINTENANT)**
- 6 familles de facteurs ci-dessus, tous haute résolution, 100% gratuits via GEE.
- Modèle déterministe (règles physiques + pondération fixe), pas d'entraînement.
- Interface simple + extraction GPS + rapport PDF.
- Tests sur 15–30 zones réelles, validées par SEV.

**V2 — Calibration géologique (après obtention carte géologique Guinée)**
- Remplacer USGS global par **carte géologique détaillée BRGM / DNGM Guinée**.
- Ajouter précipitations CHIRPS, évapotranspiration, saisonnalité avancée — utiles à
  l'échelle régionale.
- **Recalibration des poids par région géologique.**
- Possibilité de basculer LULC vers **Google Dynamic World** (quasi temps réel).
- Gain estimé : +15–20% de précision.

**V3 — Modèle ML supervisé (après base de données de forages)**
- Variables cibles : résultats forages (succès/échec), profondeur nappe, débit.
- Features : tous les facteurs V1+V2 + résistivité SEV accumulée + gravimétrie.
- Le modèle **apprend** les poids au lieu qu'on les fixe à la main.
- Produit commercialement solide (probabilité de succès quantifiée).

---

## 5. ARCHITECTURE LOGICIELLE

### 5.1 Vue d'ensemble — 3 couches
```
COUCHE 1 — INTERFACE (Streamlit)        ← ce que l'utilisateur voit
COUCHE 2 — MOTEUR (Python + GEE API)    ← calcule facteurs + scores
COUCHE 3 — DONNÉES (Google Earth Engine) ← calculs lourds + exports
```

### 5.2 Arborescence des fichiers
```
hydra/
├── CONTEXTE_HYDRA.md          ← ce fichier
├── requirements.txt
├── README.md
├── app/
│   ├── main.py                ← point d'entrée Streamlit
│   └── ui/
│       ├── sidebar.py         ← formulaire (lat/lon/rayon + sliders poids)
│       ├── map_view.py        ← carte interactive Folium
│       ├── results_table.py   ← tableau des candidats GPS
│       └── pdf_export.py      ← bouton + génération PDF
├── engine/
│   ├── __init__.py
│   ├── analyzer.py            ← orchestrateur 2 PHASES (classe HydraAnalyzer)
│   ├── mock_data.py           ← données fictives Donghol Dayebhé (Sprint 1)
│   ├── factors/
│   │   ├── __init__.py
│   │   ├── c1_lineaments.py   ← C1 Linéaments masqués anthropique (35%)
│   │   ├── c2_topo.py         ← C2 Topo + TWI MERIT Hydro + courbure (18%)
│   │   ├── c3_hydro.py        ← C3 Drainage + dist. rivières MERIT 90m (10%)
│   │   ├── c4_vegetation.py   ← C4 NDVI + NDWI + saisonnalité (20%)
│   │   ├── c5_lulc.py         ← C5 LULC + masque eau (12%)
│   │   └── c6_pedology.py     ← C6 Pédologie (5%)
│   ├── scoring/
│   │   ├── normalizer.py      ← normalisation percentiles 0–1
│   │   ├── combiner.py        ← score final pondéré
│   │   └── candidates.py      ← extraction Top 5 GPS
│   └── export/
│       ├── map_generator.py   ← carte PNG/GeoTIFF
│       ├── pdf_generator.py   ← rapport PDF
│       └── csv_export.py      ← export coordonnées
└── data/
    └── (cache local éventuel)
```

### 5.3 Stack technique
| Composant | Outil |
|---|---|
| Interface web | **Streamlit** |
| Calcul satellite | **Google Earth Engine Python API** (`earthengine-api`) |
| Carte interactive | **Folium** (+ geemap utile) |
| Génération PDF | **ReportLab** ou **WeasyPrint** |
| Données tabulaires | **Pandas** |
| Géospatial local | **Rasterio**, **Shapely** |
| Base de données | **SQLite** (V1) → **PostgreSQL + PostGIS** (V2) |

### 5.4 Orchestrateur — ARCHITECTURE 2 PHASES (décision de réanalyse, cruciale)

> **Pourquoi :** si les sliders de poids relançaient le calcul GEE, l'app serait
> inutilisable (30-60 s par mouvement). On sépare donc :
> **Stratégie grille (implémentée au Sprint 3)** : en Phase A, on empile les 6
> couches + 4 indicateurs absolus (alt, ndvi, pente, dist_riv) dans un stack
> `ee.Image.cat(...)` masqué eau, puis `stack.sample(region, scale≈rayon/16,
> geometries=True)` → UN SEUL `getInfo()` ramène ~800 points en mémoire locale.
> En Phase B, la combinaison pondérée + sélection des 5 candidats espacés
> (`engine/scoring/candidates.py`, espacement min = max(100 m, rayon×0.15))
> est 100 % locale → instantanée. L'overlay du score final pondéré est généré
> à la demande via un bouton (getMapId ~1-2 s), jamais à chaque slider.
> **Phase A (coûteuse, cachée)** = calcul des couches C1…C6 — dépend uniquement de
> (lat, lon, rayon) → `@st.cache_data` / `@st.cache_resource`.
> **Phase B (instantanée)** = somme pondérée + masque + Top 5 — recalculée à chaque
> mouvement de slider sans retoucher GEE.

```python
# engine/analyzer.py
import ee

class HydraAnalyzer:
    def __init__(self, lat, lon, rayon):
        self.lat, self.lon, self.rayon = lat, lon, rayon
        self.zone = None
        self.layers = {}        # C1..C6 normalisées (images GEE 0-1)
        self.mask_eau = None

    # ── PHASE A — coûteuse, à mettre en cache côté Streamlit ──
    def compute_layers(self):
        self._init_zone()
        from engine.factors.c1_lineaments import compute_lineaments
        from engine.factors.c2_topo       import compute_topo
        from engine.factors.c3_hydro      import compute_hydro
        from engine.factors.c4_vegetation import compute_vegetation
        from engine.factors.c5_lulc       import compute_lulc, water_mask
        from engine.factors.c6_pedology   import compute_pedology
        self.layers['C1'] = compute_lineaments(self.zone)
        self.layers['C2'] = compute_topo(self.zone)
        self.layers['C3'] = compute_hydro(self.zone)
        self.layers['C4'] = compute_vegetation(self.zone)
        self.layers['C5'] = compute_lulc(self.zone)
        self.layers['C6'] = compute_pedology(self.zone)
        self.mask_eau = water_mask(self.zone)
        return self.layers

    # ── PHASE B — instantanée, appelée à chaque changement de poids ──
    def combine(self, poids: dict):
        score = ee.Image(0)
        for code, image in self.layers.items():
            score = score.add(image.multiply(poids[code]))
        score = score.rename('score').updateMask(self.mask_eau)
        from engine.scoring.candidates import extract_top5
        candidats = extract_top5(score, self.zone, self.lat, self.lon)
        return score, candidats

    def _init_zone(self):
        point = ee.Geometry.Point([self.lon, self.lat])
        self.zone = point.buffer(self.rayon)
```

### 5.5 Ordre de développement (sprints)
1. **Sprint 1 — Squelette qui tourne** : `main.py` Streamlit + formulaire + `HydraAnalyzer` qui renvoie des données fictives + carte/tableau affichés.
2. **Sprint 2 — Premier facteur réel** : `c1_lineaments.py` avec vrai code GEE.
3. **Sprint 3 — Tous les facteurs** : C2 → C5 + score final.
4. **Sprint 4 — Export** : PDF + CSV.
5. **Sprint 5 — Polissage** : interface, gestion erreurs, base SQLite.

---

## 6. LEÇONS & BUGS GEE DÉJÀ RÉSOLUS (ne pas refaire ces erreurs)

> Ces erreurs ont coûté du temps en développement JavaScript GEE. Les éviter en Python.

1. **`ee.Feature(...).style()` n'existe pas.** Utiliser `ee.FeatureCollection([...]).style({...})` ou passer le `visParams` à `Map.addLayer`.

2. **Affichage d'une valeur calculée :** un `reduceRegion` renvoie un objet côté serveur. Pour lire le **nombre**, utiliser `.evaluate(callback)` (JS) / `.getInfo()` (Python, à utiliser avec parcimonie).

3. **ALOS PALSAR `JAXA/ALOS/PALSAR/YEARLY/SAR_EPOCH`** : couverture OK en Guinée (14 images sur la zone test) mais bande L parfois peu contrastée sur dolérite homogène → **fusionner avec l'optique Sentinel-2** (radar 40% / optique 60%).

4. **Sentinel-1 filtre orbital :** `.filter(ee.Filter.eq('orbitProperties_pass','DESCENDING'))` peut renvoyer **0 bande** sur certaines zones. Retirer le filtre orbital si la collection est vide.

5. **Normalisation robuste :** utiliser les **percentiles [5,95]** (ou [2,98]) plutôt que min/max bruts, pour éviter que des valeurs extrêmes écrasent tout le contraste. Toujours `.clamp(0,1)` après.

6. **Division par zéro à la normalisation :** si `min == max` (facteur constant sur la zone) → image vide / NaN. **C'est la raison principale d'écarter les facteurs trop grossiers** (EMAG2, USGS, GRACE, CHIRPS) à 1 km.

7. **Eau de surface = MASQUE D'EXCLUSION STRICT, pas un score.** On ne fore jamais dans un lac/fleuve. Classe LULC 80 (et 70 = neige) doivent être **éliminées** via `updateMask()`, jamais notées 0.30.
   ```python
   # c4_lulc.py
   def water_mask(zone):
       lulc = ee.ImageCollection('ESA/WorldCover/v200').first().clip(zone)
       return lulc.neq(80).And(lulc.neq(70))   # 1 = gardé, 0 = exclu
   # puis : score_final = score_final.updateMask(mask_eau)
   ```

8. **`fastDistanceTransform` calcule la distance vers les pixels = ZÉRO.** Donc pour la distance aux rivières, il faut **rivières = 0, terre = 1** :
   ```python
   # ❌ FAUX : rivieres = hydro.gt(500).selfMask()   # rivières=1 → échoue
   # ✅ BON  :
   rivieres_zero = hydro.gt(500).Not()              # rivières=0, terre=1
   dist = rivieres_zero.fastDistanceTransform(neighborhood=256,
                 units='pixels', metric='euclidean').sqrt()
   dist_m = dist.multiply(500)                       # 500 m = résolution HydroSHEDS
   ```

9. **Courbure du terrain :** GEE n'a pas de fonction native. La dériver du MNT par
   double convolution Sobel (dérivées de 1er puis 2e ordre). **Concave (négatif) =
   convergence d'eau = score élevé ; convexe (positif) = score faible** (donc inverser).

10. **Mémoire GEE (saisonnalité NDVI) :** ne JAMAIS traiter les images une par une.
    Réduire chaque collection en **une image composite** (`.median()`) AVANT tout calcul.
    Charger 2 composites (saison sèche jan–mars / humide jul–sep), pas 50 images.

11. **Toujours** passer `maxPixels=1e9` et `bestEffort=True` dans les `reduceRegion`.

12. **`.tif` ne s'ouvre pas dans PowerPoint.** Pour livrables, exporter aussi une
    **visualisation** (`image.visualize({palette,...})`) puis convertir en **PNG**.

---

## 7. CODE GEE DE RÉFÉRENCE VALIDÉ (JavaScript — à porter en Python)

> Ce script JS **fonctionne** et a produit les résultats du §3. Il sert de référence
> pour écrire les modules Python `engine/factors/*.py`. La logique est identique ;
> seule la syntaxe change (`.And()`, `.Not()`, `getInfo()`, snake_case, etc.).

### 7.1 Détection de linéaments (C1) — fonction réutilisable
```javascript
// Détecte les linéaments par Sobel multi-directionnel (+ Laplace optionnel)
function detecterLineaments(image) {
  var lisse = image.focal_median({radius:2, kernelType:'square', units:'pixels'});
  var s0   = lisse.convolve(ee.Kernel.sobel().rotate(0));
  var s90  = lisse.convolve(ee.Kernel.sobel().rotate(90));
  var s45  = lisse.convolve(ee.Kernel.sobel().rotate(45));
  var s135 = lisse.convolve(ee.Kernel.sobel().rotate(135));
  return s0.pow(2).add(s90.pow(2)).add(s45.pow(2)).add(s135.pow(2)).sqrt();
}

// Heatmap densité de fracturation
function heatmap(magnitude, nom) {
  return magnitude.convolve(ee.Kernel.gaussian(
    {radius:200, sigma:80, units:'meters', normalize:true})).rename(nom);
}
```

### 7.2 Normalisation robuste par percentiles
```javascript
function normaliser(image, nom, echelle, zone) {
  image = image.rename(nom);
  var pct = image.reduceRegion({
    reducer: ee.Reducer.percentile([5,95]),
    geometry: zone, scale: echelle, maxPixels: 1e9, bestEffort: true
  });
  var lo = ee.Number(pct.get(nom + '_p5'));
  var hi = ee.Number(pct.get(nom + '_p95'));
  return image.subtract(lo).divide(hi.subtract(lo)).clamp(0,1);
}
```

### 7.3 C1 — Fusion radar + optique
```javascript
var palsar = ee.ImageCollection('JAXA/ALOS/PALSAR/YEARLY/SAR_EPOCH')
  .filterBounds(zone).select('HH').median().clip(zone);
var palsar_db = ee.Image(10).multiply(palsar.log10()).rename('HH_db');

var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(zone)
  .filterDate('2023-01-01','2024-04-30')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',10))
  .select(['B2','B3','B4','B8','B11','B12']).median().clip(zone);

var pan = s2.expression('0.3*B4 + 0.6*B3 + 0.1*B2',
  {B4:s2.select('B4'), B3:s2.select('B3'), B2:s2.select('B2')}).rename('pan');

var den_radar   = normaliser(heatmap(detecterLineaments(palsar_db),'r'),'lin_radar',25,zone);
var den_optique = normaliser(heatmap(detecterLineaments(pan),'o'),'lin_optique',10,zone);
var C1 = den_radar.multiply(0.40).add(den_optique.multiply(0.60)).rename('C1');
```

### 7.4 C2 — Topographie + TWI + distance rivières (avec le fix fastDistanceTransform)
```javascript
var srtm  = ee.Image('USGS/SRTMGL1_003').clip(zone);
var alt   = srtm.select('elevation');
var slope = ee.Terrain.slope(alt).rename('slope');

// TWI
var slope_rad = slope.multiply(Math.PI/180);
var tan_slope = slope_rad.tan().max(0.001);
var flow = alt.convolve(ee.Kernel.gaussian({radius:100,sigma:50,units:'meters',normalize:true}));
var flow_min = ee.Number(flow.reduceRegion({reducer:ee.Reducer.min(),geometry:zone,scale:30,maxPixels:1e9,bestEffort:true}).values().get(0));
var twi = flow.subtract(flow_min).divide(tan_slope).log().rename('twi');

// Scores (altitude basse = favorable ; pente faible = favorable ; TWI élevé = favorable)
var alt_min = ee.Number(alt.reduceRegion({reducer:ee.Reducer.min(),geometry:zone,scale:30,maxPixels:1e9,bestEffort:true}).values().get(0));
var alt_max = ee.Number(alt.reduceRegion({reducer:ee.Reducer.max(),geometry:zone,scale:30,maxPixels:1e9,bestEffort:true}).values().get(0));
var sc_alt   = ee.Image(1).subtract(alt.subtract(alt_min).divide(alt_max.subtract(alt_min))).rename('sc_alt');
var slope_p95= ee.Number(slope.reduceRegion({reducer:ee.Reducer.percentile([95]),geometry:zone,scale:30,maxPixels:1e9,bestEffort:true}).values().get(0));
var sc_slope = ee.Image(1).subtract(slope.divide(slope_p95)).clamp(0,1).rename('sc_slope');
var sc_twi   = normaliser(twi,'twi',30,zone).rename('sc_twi');

// Distance rivières (HydroSHEDS) — FIX : rivières = 0
var hydro = ee.Image('WWF/HydroSHEDS/15ACC').select('b1').clip(zone);
var rivieres_zero = hydro.gt(500).not();
var dist = rivieres_zero.fastDistanceTransform({neighborhood:256,units:'pixels',metric:'euclidean'}).sqrt().multiply(500).rename('dist_riv');
var sc_riv = ee.Image(1).subtract(normaliser(dist,'dist_riv',30,zone)).rename('sc_riv'); // proche = favorable

// C2 (exemple de combinaison)
var C2 = sc_alt.multiply(0.25).add(sc_slope.multiply(0.20))
  .add(sc_twi.multiply(0.25)).add(sc_riv.multiply(0.30)).rename('C2');
// + courbure & géomorphologie à ajouter (voir §6 point 9)
```

### 7.5 C3 — NDVI + NDWI + Saisonnalité (2 composites seulement)
```javascript
function s2compo(m1,m2){
  return ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(zone)
    .filter(ee.Filter.calendarRange(m1,m2,'month'))
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',15))
    .select(['B4','B8','B11']).median().clip(zone);
}
var sec = s2compo(1,3), hum = s2compo(7,9);

var ndvi_sec = sec.normalizedDifference(['B8','B4']).rename('ndvi_sec');
var ndwi_sec = sec.normalizedDifference(['B8','B11']).rename('ndwi_sec');
var ndvi_hum = hum.normalizedDifference(['B8','B4']).rename('ndvi_hum');

// Saisonnalité : delta FAIBLE = nappe proche = score ÉLEVÉ (on inverse)
var delta = ndvi_hum.subtract(ndvi_sec).rename('delta');
var sc_saison = ee.Image(1).subtract(normaliser(delta,'delta',10,zone)).rename('sc_saison');

var C3 = normaliser(ndvi_sec,'ndvi_sec',10,zone).multiply(0.40)
  .add(normaliser(ndwi_sec,'ndwi_sec',10,zone).multiply(0.30))
  .add(sc_saison.multiply(0.30)).rename('C3');
```

### 7.6 C4 — LULC + masque eau (exclusion stricte)
```javascript
var lulc = ee.ImageCollection('ESA/WorldCover/v200').first().clip(zone);
var C4 = lulc.remap(
  [10,  20,  30,  40,  50,  60,  70,  80,  90,  95,  100],
  [0.9, 0.7, 0.6, 0.5, 0.1, 0.4, 0.0, 0.3, 0.8, 0.8, 0.5]).rename('C4');
var mask_eau = lulc.neq(80).and(lulc.neq(70));   // exclusion eau + neige
```

### 7.7 C5 — Pédologie SoilGrids (sable vs argile)
```javascript
var clay = ee.Image('projects/soilgrids-isric/clay_mean').select('clay_0-5cm_mean').clip(zone);
var sand = ee.Image('projects/soilgrids-isric/sand_mean').select('sand_0-5cm_mean').clip(zone);
var sol_diff = sand.subtract(clay).rename('sol_diff');   // sable - argile : + = perméable
var C5 = normaliser(sol_diff,'sol_diff',250,zone).rename('C5');
```

### 7.8 Score final + masque + extraction Top 5
```javascript
var score_v1 = C1.multiply(0.45).add(C2.multiply(0.25)).add(C3.multiply(0.15))
  .add(C4.multiply(0.10)).add(C5.multiply(0.05)).rename('score_v1')
  .updateMask(mask_eau);   // ← exclusion eau APRÈS combinaison

// Seuil top 15% → vectorisation → centroïdes → tri par score
var seuil = ee.Number(score_v1.reduceRegion({reducer:ee.Reducer.percentile([85]),
  geometry:zone, scale:30, maxPixels:1e9, bestEffort:true}).get('score_v1'));
var polys = score_v1.gt(seuil).selfMask().clip(zone)
  .reduceToVectors({geometry:zone, scale:30, maxPixels:1e9, bestEffort:true,
    geometryType:'polygon', eightConnected:true, reducer:ee.Reducer.countEvery()})
  .filter(ee.Filter.gt('count',3));
// → calculer centroïde de chaque polygone, échantillonner score/alt/ndvi/distance,
//   trier par score_v1 décroissant, prendre les 5 premiers (voir transcript).
```

> **Poids V1 définitifs (6 facteurs, configurables via sliders) :**
> C1 0.35 · C2 0.18 · C3 0.10 · C4 0.20 · C5 0.12 · C6 0.05 = 1.00.
> Combinaison : `score = Σ(Ci × poids_i)` puis `.updateMask(mask_eau)`.
> TWI et rivières : utiliser **MERIT Hydro** (`MERIT/Hydro/v1_0_1`, bande `upa`, 90 m)
> et non l'approximation gaussienne ni HydroSHEDS 15ACC (463 m).

---

## 8. AUTHENTIFICATION GEE EN PYTHON (à faire une fois)

```bash
pip install earthengine-api geemap streamlit folium rasterio shapely pandas reportlab
```
```python
import ee
ee.Authenticate()                 # ouvre le navigateur, une seule fois
ee.Initialize(project='ee-hydrogeologie-guinee')
```
> Différent de l'éditeur web code.earthengine.google.com. En Python il faut
> `ee.Authenticate()` puis `ee.Initialize(project=...)` au démarrage de l'app.

---

## 9. PRINCIPES À RESPECTER (résumé pour l'IA développeuse)

1. **Modularité** : un fichier par famille de facteurs, même structure
   (load → detect → heatmap → normalise → fusion → return image GEE 0–1).
2. **Poids configurables** : ne jamais coder les poids en dur ; passer un dict
   depuis l'UI (sliders Streamlit).
3. **Normalisation par percentiles [5,95] + clamp(0,1)** partout.
4. **Eau = updateMask** (exclusion), jamais un score.
5. **Ne jamais intégrer un facteur de résolution ≥ zone** (variance nulle / div par 0).
6. **Réduire les collections en composites** avant calcul (mémoire GEE).
7. **Calculs lourds côté GEE**, ne rapatrier que les résultats finaux.
8. **Tester d'abord sur Donghol Dayebhé** (coordonnées §3) : on connaît les résultats
   attendus → c'est notre cas de non-régression (forage ≈ 0.39, C1/C4 candidats forts).
9. **Géographie V1 = Guinée uniquement** (modèle calibré socle cristallin).
10. **Garder le code lisible et commenté en français** (équipe francophone).

---

*Fin du contexte HYDRA. Bon développement.*
