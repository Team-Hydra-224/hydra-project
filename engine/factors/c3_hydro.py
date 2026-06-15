# -*- coding: utf-8 -*-
"""
HYDRA — engine/factors/c3_hydro.py
===================================
C3 — Hydrographie (poids par défaut : 10%).

Source : MERIT Hydro v1.0.1 à 90 m (décision de réanalyse n°3 — remplace
HydroSHEDS 15ACC à 463 m, conforme à la règle d'or résolution vs zone).

Sous-facteurs (pondération interne) :
  - Proximité rivières   50%  (proche = favorable, recharge latérale)
  - Densité de drainage  25%  (réseau dense = nappe active)
  - HAND                 25%  (Height Above Nearest Drainage — bande `hnd`
                              de MERIT : hauteur au-dessus du drain le plus
                              proche. Faible = proche du niveau d'eau =
                              favorable → inversée)

PIÈGE GEE ÉVITÉ (CONTEXTE §6.8) : fastDistanceTransform calcule la
distance vers les pixels = ZÉRO → rivières codées 0 via .Not().

NOTE : les rivières sont détectées sur une zone ÉLARGIE (+2 km) pour
capter les cours d'eau proches situés juste hors de la zone d'analyse.
"""

import ee

from engine.gee_utils import normaliser

# Seuil d'accumulation définissant une "rivière" (km² drainés en amont).
# 0.5 km² ≈ cours d'eau permanents en climat tropical humide guinéen.
SEUIL_RIVIERE_KM2 = 0.5

# Résolution nominale MERIT Hydro (3 arc-secondes à l'équateur)
MERIT_SCALE_M = 92.77


def compute_hydro(zone: ee.Geometry) -> ee.Image:
    """Calcule la couche C3 (hydrographie) normalisée 0-1."""
    zone_large = zone.buffer(2000)   # capter les rivières voisines

    merit = ee.Image("MERIT/Hydro/v1_0_1").clip(zone_large)
    upa = merit.select("upa")        # accumulation (km²)
    hnd = merit.select("hnd")        # height above nearest drainage (m)

    # ── Masque rivières (1 = rivière) sur la zone élargie ───────────
    rivieres = upa.gt(SEUIL_RIVIERE_KM2)

    # ── Distance aux rivières — fix .Not() (rivières = 0) ───────────
    rivieres_zero = rivieres.Not()
    dist_px = rivieres_zero.fastDistanceTransform(
        256, "pixels", "squared_euclidean"
    ).sqrt()
    dist_m = dist_px.multiply(MERIT_SCALE_M).rename("dist_riv").clip(zone)
    # Proximité : distance faible = favorable → inverser
    sc_prox = normaliser(dist_m, "sc_prox", zone, scale=90, inverser=True)

    # ── Densité de drainage (convolution gaussienne du masque) ──────
    densite = rivieres.convolve(
        ee.Kernel.gaussian(radius=400, sigma=150,
                           units="meters", normalize=True)
    ).rename("den_drain").clip(zone)
    sc_dens = normaliser(densite, "sc_dens", zone, scale=90)

    # ── HAND : hauteur au-dessus du drain (faible = favorable) ──────
    sc_hand = normaliser(hnd.clip(zone), "sc_hand", zone,
                         scale=90, inverser=True)

    # ── Combinaison interne ──────────────────────────────────────────
    c3 = (
        sc_prox.multiply(0.50)
        .add(sc_dens.multiply(0.25))
        .add(sc_hand.multiply(0.25))
        .rename("C3")
        .clip(zone)
    )
    return c3


def get_distance_rivieres(zone: ee.Geometry) -> ee.Image:
    """Distance brute aux rivières en mètres (indicateur absolu)."""
    zone_large = zone.buffer(2000)
    upa = ee.Image("MERIT/Hydro/v1_0_1").select("upa").clip(zone_large)
    rivieres_zero = upa.gt(SEUIL_RIVIERE_KM2).Not()
    dist_px = rivieres_zero.fastDistanceTransform(
        256, "pixels", "squared_euclidean"
    ).sqrt()
    return dist_px.multiply(MERIT_SCALE_M).rename("dist_riv").clip(zone)
