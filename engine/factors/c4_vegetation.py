# -*- coding: utf-8 -*-
"""
HYDRA — engine/factors/c4_vegetation.py
========================================
C4 — Végétation & humidité (poids par défaut : 20%).

Sous-facteurs (pondération interne) :
  - NDVI saison sèche     40%  (végétation verte en saison sèche = nappe)
  - NDWI Gao saison sèche 30%  (teneur en eau de la végétation)
  - Saisonnalité NDVI     30%  (delta humide-sec FAIBLE = nappe peu
                               profonde = favorable → inversée)

RÈGLE MÉMOIRE GEE (CONTEXTE §6.10) : on réduit chaque saison en UNE
image composite (.median()) AVANT tout calcul — jamais image par image.

Saisons guinéennes :
  - Sèche  : janvier → mars   (nuages < 15 %)
  - Humide : juillet → sept.  (nuages < 40 % — très nuageux, on élargit)
"""

import ee

from engine.gee_utils import normaliser


def _composite(zone: ee.Geometry, mois_debut: int, mois_fin: int,
               nuages_max: int) -> ee.Image:
    """Composite médian Sentinel-2 pour une plage de mois (toutes années)."""
    return (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(zone)
        .filterDate("2021-01-01", "2025-12-31")
        .filter(ee.Filter.calendarRange(mois_debut, mois_fin, "month"))
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", nuages_max))
        .select(["B3", "B4", "B8", "B11"])
        .median()
        .clip(zone)
    )


def compute_vegetation(zone: ee.Geometry) -> ee.Image:
    """Calcule la couche C4 (végétation/humidité) normalisée 0-1."""
    sec = _composite(zone, 1, 3, nuages_max=15)
    humide = _composite(zone, 7, 9, nuages_max=40)

    # ── NDVI saison sèche (élevé = favorable) ───────────────────────
    ndvi_sec = sec.normalizedDifference(["B8", "B4"]).rename("ndvi_sec")
    sc_ndvi = normaliser(ndvi_sec, "sc_ndvi", zone, scale=10)

    # ── NDWI Gao saison sèche (humidité végétation, élevé = favorable)
    ndwi_sec = sec.normalizedDifference(["B8", "B11"]).rename("ndwi_sec")
    sc_ndwi = normaliser(ndwi_sec, "sc_ndwi", zone, scale=10)

    # ── Saisonnalité : delta NDVI humide - sec ───────────────────────
    # Delta FAIBLE = la végétation reste verte en saison sèche
    #             = racines alimentées par une nappe → favorable → inverser
    ndvi_hum = humide.normalizedDifference(["B8", "B4"]).rename("ndvi_hum")
    delta = ndvi_hum.subtract(ndvi_sec).rename("delta")
    sc_saison = normaliser(delta, "sc_saison", zone, scale=10,
                           inverser=True)

    # ── Combinaison interne ──────────────────────────────────────────
    c4 = (
        sc_ndvi.multiply(0.40)
        .add(sc_ndwi.multiply(0.30))
        .add(sc_saison.multiply(0.30))
        .rename("C4")
        .clip(zone)
    )
    return c4


def get_ndvi_brut(zone: ee.Geometry) -> ee.Image:
    """NDVI brut saison sèche (indicateur absolu pour le tableau).
    Repère terrain Afrique de l'Ouest : > 0.25 en saison sèche = bon signe."""
    sec = _composite(zone, 1, 3, nuages_max=15)
    return sec.normalizedDifference(["B8", "B4"]).rename("ndvi")
