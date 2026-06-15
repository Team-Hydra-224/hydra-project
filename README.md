# 💧 HYDRA — Sprint 1 (squelette)

Logiciel d'analyse hydrogéologique par satellite. **Trouver l'eau avant de forer.**

> Lire `CONTEXTE_HYDRA.md` pour tout le contexte projet (méthode, facteurs, décisions).

## État actuel — Sprint 1

- ✅ Interface Streamlit complète (formulaire + carte + tableau + sliders de poids)
- ✅ Architecture 2 phases en place (couches cachées / combinaison instantanée)
- ✅ Moteur en mode **MOCK** : données fictives basées sur le cas réel Donghol Dayebhé
- ✅ **Sprint 2 : Google Earth Engine branché — facteur C1 (linéaments) RÉEL**
  - Mode « hybride » : C1 calculé sur GEE (fusion radar+optique, masque anthropique),
    C2–C6 encore fictifs
  - Couche C1 affichée en overlay sur la carte
  - Script de validation `test_gee.py`
- ✅ **Sprint 3 : moteur GEE COMPLET — les 6 facteurs réels**
  - C2 Topographie (SRTM + TWI MERIT Hydro + courbure + TPI)
  - C3 Hydrographie (MERIT Hydro 90 m, distance rivières + drainage + HAND)
  - C4 Végétation (NDVI/NDWI saison sèche + saisonnalité, masquage nuages SCL)
  - C5 LULC (scores d'infiltration + masque eau strict)
  - C6 Pédologie (SoilGrids sable vs argile)
  - Extraction RÉELLE des candidats : grille ~800 points échantillonnée en
    Phase A, combinaison pondérée + sélection espacée 100 % locale en Phase B
    → les sliders restent instantanés même en mode GEE
  - Overlays carte : chaque couche C1..C6 + score final pondéré (à la demande)
- ✅ **Sprint 4 : exports professionnels**
  - Rapport PDF 2 pages : métadonnées, avertissement score relatif, plan de
    situation, miniature satellite du score (mode GEE), tableau candidats,
    détail des facteurs, pondération, méthodologie, recommandation SEV
  - Export CSV des candidats (compatible Excel / QGIS / GPS terrain)
  - Bouton « Générer le rapport » dans l'app → téléchargements PDF + CSV
- ✅ **Sprint 4 : exports professionnels**
  - Rapport PDF 2 pages : métadonnées, avertissement score relatif, plan de
    situation, miniature satellite du score (mode GEE), tableau candidats,
    détail des facteurs, pondération, méthodologie, recommandation SEV
  - Export CSV des candidats (compatible Excel / QGIS / GPS terrain)
  - Bouton « Générer le rapport » dans l'app → téléchargements PDF + CSV
- ✅ **Sprint 5 : confidentialité + exports pro**
  - Sélecteur **Client / Expert** : le rapport Client masque pondération,
    méthodologie et sous-scores C1–C6 (confidentiel) ; l'Expert montre tout
  - **Logo HYDRA** intégré (généré en code, aucun fichier requis)
  - Plan de situation : **orientation cartographique standard** (Ouest←→Est)
  - Deux styles de plan au choix : **schématique** ou **sur image satellite**
  - Export **Excel (.xlsx)** lisible (en-têtes colorés, 2 feuilles en Expert)
    à la place du CSV brut

## Installation (une fois)

```bash
# 1. Se placer dans le dossier du projet
cd hydra

# 2. Créer et activer l'environnement virtuel
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac / Linux

# 3. Installer les dépendances
pip install -r requirements.txt
```

## Lancement

```bash
# Toujours depuis la racine du projet hydra/
streamlit run app/main.py
```

Le navigateur s'ouvre sur `http://localhost:8501`.

## Sprint 2 — Brancher Google Earth Engine (À FAIRE UNE FOIS)

```bash
# 1. Installer la nouvelle dépendance (venv activé)
pip install -r requirements.txt

# 2. Valider l'authentification GEE — OBLIGATOIRE avant l'app
python test_gee.py
```

> **Sprint 3 :** `test_gee.py` teste désormais les 6 facteurs un par un puis
> le pipeline complet (grille + candidats réels). Durée totale : 2 à 5 min.

Au premier lancement de `test_gee.py`, **une page de navigateur s'ouvre** :
connectez-vous avec le compte Google lié au projet `ee-hydrogeologie-guinee`
et autorisez l'accès. Le script vérifie ensuite les datasets et calcule un
vrai score C1 aux points de référence de Donghol Dayebhé (~30-60 s).

Si tout est vert → lancez l'app et choisissez **« GEE réel »** dans la barre
latérale. La couche de fractures s'affiche en overlay sur la carte.

## Tester le Sprint 1

1. Laisser les coordonnées par défaut (Donghol Dayebhé) et cliquer **Lancer l'analyse**.
2. Vérifier : la carte satellite s'affiche avec le cercle de 1 km, le centre rouge
   et 5 candidats en étoiles colorées.
3. Bouger les sliders de pondération → le classement du tableau change
   **instantanément** (c'est la Phase B, sans recalcul satellite).
4. Mettre le total à autre chose que 100 % → le bouton se désactive (garde-fou).

## Structure

```
hydra/
├── CONTEXTE_HYDRA.md      ← contexte complet du projet (à lire en premier)
├── requirements.txt
├── README.md
├── app/
│   └── main.py            ← interface Streamlit (point d'entrée)
└── engine/
    ├── analyzer.py        ← orchestrateur 2 phases (mode mock)
    ├── mock_data.py       ← données fictives Donghol Dayebhé
    ├── factors/           ← (vide — modules C1..C6 au Sprint 2-3)
    ├── scoring/           ← (vide — extraction candidats au Sprint 3)
    └── export/            ← (vide — PDF/CSV au Sprint 4)
```
> Note : Pipeline CI/CD validée avec succès !