# -*- coding: utf-8 -*-
"""
HYDRA — engine/factors/c5_lulc.py
==================================
C5 — Occupation des sols / LULC (poids par défaut : 12%).

Source : ESA WorldCover v200 (2021), 10 m.
(V2 : bascule possible vers Google Dynamic World, quasi temps réel.)

Score d'infiltration par classe (valeurs ABSOLUES — PAS de normalisation
percentile ici, contrairement aux autres facteurs : chaque classe a un
sens physique fixe) :

  10 forêt 0.90 · 20 arbustes 0.70 · 30 herbacé 0.60 · 40 cultures 0.50
  50 bâti 0.10 · 60 sol nu 0.40 · 90 zones humides 0.80 · 95 mangrove 0.80
  100 mousses 0.50

RÈGLE D'OR (CONTEXTE §6.7) : l'eau de surface (80) et la neige (70) ne
reçoivent PAS de score — elles sont EXCLUES par masque strict
(water_mask), on ne fore jamais dans un lac.
"""

import ee


def _lulc(zone: ee.Geometry) -> ee.Image:
    return ee.ImageCollection("ESA/WorldCover/v200").first().clip(zone)


def compute_lulc(zone: ee.Geometry) -> ee.Image:
    """Calcule la couche C5 (infiltration LULC) 0-1, valeurs absolues."""
    lulc = _lulc(zone)
    # remap exige des entiers → scores ×100 puis division
    c5 = (
        lulc.remap(
            [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100],
            [90, 70, 60, 50, 10, 40,  0,  0, 80, 80,  50],
        )
        .divide(100)
        .rename("C5")
        .clip(zone)
    )
    return c5


def water_mask(zone: ee.Geometry) -> ee.Image:
    """
    Masque d'EXCLUSION STRICTE : eau de surface (80) et neige (70).
    1 = pixel analysable, 0 = exclu. À appliquer via updateMask()
    sur le score final ET sur le stack d'échantillonnage.
    """
    lulc = _lulc(zone)
    return lulc.neq(80).And(lulc.neq(70))
