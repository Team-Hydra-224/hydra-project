# -*- coding: utf-8 -*-
"""
HYDRA — engine/analyzer.py
===========================
Orchestrateur principal du moteur d'analyse hydrogéologique.

ARCHITECTURE 2 PHASES (décision de réanalyse — NE PAS fusionner) :

  PHASE A — compute_layers()  [COÛTEUSE — cachée côté Streamlit]
    Mode GEE : construit les 6 couches de facteurs côté serveur, puis
    ÉCHANTILLONNE UNE GRILLE de ~800 points (un seul gros .getInfo())
    contenant les 6 sous-scores + les indicateurs absolus de chaque point.
    Tous les allers-retours GEE ont lieu ICI.

  PHASE B — combine(poids)    [INSTANTANÉE — appelée à chaque slider]
    Classement 100 % LOCAL de la grille : somme pondérée en pur Python
    + sélection gloutonne espacée des 5 meilleurs sites.
    Ne touche JAMAIS à GEE → sliders en temps réel même avec les
    vrais facteurs.

MODES :
  "mock" : démo hors-ligne (données fictives Donghol Dayebhé).
  "gee"  : pipeline complet réel (Sprint 3) — les 6 facteurs.

Poids V1 par défaut :
  C1 35% · C2 18% · C3 10% · C4 20% · C5 12% · C6 5%
"""

from math import sqrt, cos, radians

# ── Poids par défaut V1 (modifiables via l'UI) ──────────────────────────
POIDS_DEFAUT = {
    "C1": 0.35,   # Linéaments / fractures
    "C2": 0.18,   # Topographie + TWI + courbure
    "C3": 0.10,   # Hydrographie (drainage + distance rivières + HAND)
    "C4": 0.20,   # Végétation (NDVI + NDWI + saisonnalité)
    "C5": 0.12,   # LULC occupation des sols
    "C6": 0.05,   # Pédologie
}

NOMS_FACTEURS = {
    "C1": "Linéaments / fractures",
    "C2": "Topographie + TWI",
    "C3": "Hydrographie",
    "C4": "Végétation (NDVI/NDWI)",
    "C5": "Occupation des sols",
    "C6": "Pédologie",
}

CODES = list(POIDS_DEFAUT.keys())

# Bandes "indicateurs absolus" ajoutées au stack d'échantillonnage
BANDES_INDICATEURS = ["alt", "ndvi", "pente", "dist_riv"]


class HydraAnalyzer:
    """
    Analyseur hydrogéologique HYDRA.

    Usage :
        analyzer = HydraAnalyzer(lat, lon, rayon, mode="gee")
        analyzer.compute_layers()            # Phase A (coûteuse, une fois)
        candidats = analyzer.combine(poids)  # Phase B (instantanée)
        url = analyzer.tile_url("C1")        # overlay d'une couche
        url = analyzer.tile_url_score(poids) # overlay du score final
    """

    def __init__(self, lat: float, lon: float, rayon: int,
                 mode: str = "mock"):
        if mode not in ("mock", "gee"):
            raise ValueError(f"Mode inconnu : {mode}")
        self.lat = lat
        self.lon = lon
        self.rayon = rayon
        self.mode = mode
        self._layers_ready = False
        self._points: list[dict] = []   # grille Phase A (mode gee)
        self._candidats_mock: list[dict] = []
        self._images = {}               # ee.Image par code (mode gee)
        self._mask_eau = None
        self._zone = None
        self.nb_points_grille = 0
        self.sources_scores = {}

    # ──────────────────────────────────────────────────────────────────
    # PHASE A — Calcul des couches (coûteux, à cacher)
    # ──────────────────────────────────────────────────────────────────
    def compute_layers(self) -> None:
        if self.mode == "mock":
            from engine.mock_data import get_mock_candidates
            self._candidats_mock = get_mock_candidates(self.lat, self.lon)
            self.sources_scores = {c: "mock" for c in CODES}
        else:
            self._compute_layers_gee()
            self.sources_scores = {c: "réel GEE" for c in CODES}
        self._layers_ready = True

    def _compute_layers_gee(self) -> None:
        """Construit les 6 couches + échantillonne la grille de points."""
        import ee
        from engine.gee_utils import init_gee
        from engine.factors.c1_lineaments import compute_lineaments
        from engine.factors.c2_topo import compute_topo, get_altitude, \
            get_pente
        from engine.factors.c3_hydro import compute_hydro, \
            get_distance_rivieres
        from engine.factors.c4_vegetation import compute_vegetation, \
            get_ndvi_brut
        from engine.factors.c5_lulc import compute_lulc, water_mask
        from engine.factors.c6_pedology import compute_pedology

        init_gee()
        point = ee.Geometry.Point([self.lon, self.lat])
        self._zone = point.buffer(self.rayon)

        # ── Les 6 couches de facteurs (côté serveur, paresseux) ─────
        self._images = {
            "C1": compute_lineaments(self._zone),
            "C2": compute_topo(self._zone),
            "C3": compute_hydro(self._zone),
            "C4": compute_vegetation(self._zone),
            "C5": compute_lulc(self._zone),
            "C6": compute_pedology(self._zone),
        }
        self._mask_eau = water_mask(self._zone)

        # ── Stack facteurs + indicateurs absolus ────────────────────
        stack = ee.Image.cat([
            self._images["C1"], self._images["C2"], self._images["C3"],
            self._images["C4"], self._images["C5"], self._images["C6"],
            get_altitude(self._zone),
            get_ndvi_brut(self._zone),
            get_pente(self._zone),
            get_distance_rivieres(self._zone),
        ]).updateMask(self._mask_eau)

        # ── Échantillonnage en grille : UN SEUL gros getInfo ────────
        # Pas adaptatif : ~800 points quel que soit le rayon.
        scale = max(30, int(self.rayon / 16))
        echantillon = stack.sample(
            region=self._zone,
            scale=scale,
            geometries=True,
        ).getInfo()

        self._points = []
        for feat in echantillon.get("features", []):
            props = feat.get("properties", {})
            coords = feat.get("geometry", {}).get("coordinates", [None, None])
            # On ne garde que les points où TOUS les facteurs existent
            if any(props.get(c) is None for c in CODES):
                continue
            self._points.append({
                "lon": coords[0],
                "lat": coords[1],
                "scores": {c: props[c] for c in CODES},
                "alt": props.get("alt"),
                "ndvi": props.get("ndvi"),
                "pente": props.get("pente"),
                "dist_riv": props.get("dist_riv"),
            })
        self.nb_points_grille = len(self._points)
        if self.nb_points_grille < 10:
            raise RuntimeError(
                f"Grille trop pauvre ({self.nb_points_grille} points) — "
                "zone presque entièrement masquée (eau ?) ou données "
                "indisponibles sur cette zone."
            )

    # ──────────────────────────────────────────────────────────────────
    # PHASE B — Combinaison pondérée (instantanée, 100 % locale)
    # ──────────────────────────────────────────────────────────────────
    def combine(self, poids: dict | None = None) -> list[dict]:
        if not self._layers_ready:
            raise RuntimeError("Appeler compute_layers() avant combine().")
        poids = poids or POIDS_DEFAUT
        self._verifier_poids(poids)

        if self.mode == "mock":
            return self._combine_mock(poids)

        from engine.scoring.candidates import selectionner_candidats
        espacement = max(100.0, self.rayon * 0.15)
        return selectionner_candidats(
            self._points, poids, self.lat, self.lon,
            n=5, espacement_min_m=espacement,
        )

    def _combine_mock(self, poids: dict) -> list[dict]:
        resultats = []
        for cand in self._candidats_mock:
            score = sum(cand["scores"][c] * poids[c] for c in poids)
            resultats.append({
                **cand,
                "score": round(score, 4),
                "distance_centre_m": int(self._distance_m(
                    self.lat, self.lon, cand["lat"], cand["lon"])),
            })
        resultats.sort(key=lambda c: c["score"], reverse=True)
        for rang, cand in enumerate(resultats, start=1):
            cand["rang"] = rang
        return resultats

    # ──────────────────────────────────────────────────────────────────
    # Overlays carte (mode gee uniquement)
    # ──────────────────────────────────────────────────────────────────
    def tile_url(self, code: str) -> str | None:
        """URL XYZ d'une couche de facteur (C1..C6) pour Folium."""
        if self.mode == "mock" or code not in self._images:
            return None
        from engine.gee_utils import tile_url, PALETTE_SCORE
        return tile_url(
            self._images[code].updateMask(self._mask_eau),
            {"min": 0, "max": 1, "palette": PALETTE_SCORE},
        )

    def tile_url_score(self, poids: dict) -> str | None:
        """
        URL XYZ du SCORE FINAL pondéré. Léger appel réseau (getMapId,
        ~1-2 s) → à déclencher via un bouton, pas à chaque slider.
        """
        if self.mode == "mock":
            return None
        import ee
        from engine.gee_utils import tile_url, PALETTE_SCORE
        self._verifier_poids(poids)
        score = ee.Image(0)
        for code, image in self._images.items():
            score = score.add(image.multiply(poids[code]))
        score = score.rename("score").updateMask(self._mask_eau)
        return tile_url(score, {"min": 0, "max": 1,
                                "palette": PALETTE_SCORE})

    # ──────────────────────────────────────────────────────────────────
    # Utilitaires
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _verifier_poids(poids: dict) -> None:
        attendus = set(POIDS_DEFAUT.keys())
        if set(poids.keys()) != attendus:
            raise ValueError(f"Poids attendus : {sorted(attendus)}, "
                             f"reçus : {sorted(poids.keys())}")
        total = sum(poids.values())
        if not 0.99 <= total <= 1.01:
            raise ValueError(f"La somme des poids doit faire 1.0 "
                             f"(reçu : {total:.3f})")

    @staticmethod
    def _distance_m(lat1, lon1, lat2, lon2) -> float:
        dlat = (lat2 - lat1) * 111_320
        dlon = (lon2 - lon1) * 111_320 * cos(radians(lat1))
        return sqrt(dlat ** 2 + dlon ** 2)


def verdict(score: float) -> str:
    """Verdict lisible pour un score relatif 0-1."""
    if score > 0.70:
        return "🟢 EXCELLENT"
    if score > 0.50:
        return "🟡 BON"
    if score > 0.30:
        return "🟠 MOYEN"
    return "🔴 FAIBLE"
