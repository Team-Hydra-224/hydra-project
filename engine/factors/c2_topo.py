# -*- coding: utf-8 -*-
"""
HYDRA — engine/factors/c2_topo.py
==================================
C2 — Topographie (poids par défaut : 18%).

Sous-facteurs (pondération interne) :
  - Altitude relative      25%  (bas = favorable → inversée)
  - Pente                  20%  (faible = favorable → inversée)
  - TWI                    25%  (élevé = favorable) — via MERIT Hydro `upa`
                                (décision de réanalyse n°3 : accumulation de
                                flux RÉELLE à 90 m, pas d'approximation)
  - Courbure (laplacien)   20%  (laplacien positif = cuvette = favorable)
  - Géomorphologie (TPI)   10%  (TPI négatif = en contrebas = favorable)
"""

import math

import ee

from engine.gee_utils import normaliser


def compute_topo(zone: ee.Geometry) -> ee.Image:
    """Calcule la couche C2 (topographie) normalisée 0-1."""
    srtm = ee.Image("USGS/SRTMGL1_003").clip(zone)
    alt = srtm.select("elevation")
    slope = ee.Terrain.slope(alt).rename("slope")

    # ── Altitude (inversée : bas = favorable) ───────────────────────
    sc_alt = normaliser(alt, "sc_alt", zone, scale=30, inverser=True)

    # ── Pente (inversée : faible = favorable) ───────────────────────
    sc_pente = normaliser(slope, "sc_pente", zone, scale=30, inverser=True)

    # ── TWI via MERIT Hydro (accumulation de flux réelle, 90 m) ─────
    # TWI = ln( aire drainée / tan(pente) ). Les constantes d'unités
    # sont absorbées par la normalisation percentile (index relatif).
    upa = ee.Image("MERIT/Hydro/v1_0_1").select("upa").clip(zone)  # km²
    tan_slope = slope.multiply(math.pi / 180).tan().max(0.001)
    twi = (
        upa.multiply(1e6)             # km² → m²
        .divide(tan_slope)
        .add(1)                        # évite log(0)
        .log()
        .rename("twi")
    )
    sc_twi = normaliser(twi, "sc_twi", zone, scale=90)

    # ── Courbure : laplacien du MNT lissé ───────────────────────────
    # Convention mathématique : au FOND d'une cuvette (minimum local),
    # le laplacien est POSITIF → cuvette = accumulation = favorable.
    # On normalise donc SANS inverser.
    mnt_lisse = alt.convolve(
        ee.Kernel.gaussian(radius=2, sigma=1, units="pixels")
    )
    courbure = mnt_lisse.convolve(ee.Kernel.laplacian8()).rename("courb")
    sc_courb = normaliser(courbure, "sc_courb", zone, scale=30)

    # ── Géomorphologie : TPI (Topographic Position Index) ───────────
    # TPI = altitude - moyenne du voisinage (300 m).
    # TPI négatif = point en contrebas (vallée) = favorable → inverser.
    voisinage = alt.focal_mean(radius=300, kernelType="circle",
                               units="meters")
    tpi = alt.subtract(voisinage).rename("tpi")
    sc_tpi = normaliser(tpi, "sc_tpi", zone, scale=30, inverser=True)

    # ── Combinaison interne ──────────────────────────────────────────
    c2 = (
        sc_alt.multiply(0.25)
        .add(sc_pente.multiply(0.20))
        .add(sc_twi.multiply(0.25))
        .add(sc_courb.multiply(0.20))
        .add(sc_tpi.multiply(0.10))
        .rename("C2")
        .clip(zone)
    )
    return c2


def get_altitude(zone: ee.Geometry) -> ee.Image:
    """Altitude brute SRTM (indicateur absolu pour le tableau)."""
    return ee.Image("USGS/SRTMGL1_003").select("elevation") \
        .clip(zone).rename("alt")


def get_pente(zone: ee.Geometry) -> ee.Image:
    """Pente brute en degrés (indicateur absolu pour le tableau)."""
    alt = ee.Image("USGS/SRTMGL1_003").select("elevation").clip(zone)
    return ee.Terrain.slope(alt).rename("pente")
