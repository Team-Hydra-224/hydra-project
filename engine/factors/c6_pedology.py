# -*- coding: utf-8 -*-
"""
HYDRA — engine/factors/c6_pedology.py
======================================
C6 — Pédologie / texture du sol (poids par défaut : 5%).

Source : SoilGrids ISRIC, 250 m, couche superficielle 0-5 cm.
(Résolution 250 m sur rayon 1 km ≈ 8×8 pixels → variance suffisante,
conforme à la règle d'or — contrairement à HWSD 1 km écarté.)

Principe : sable = infiltration rapide = favorable ;
           argile = imperméable/ruissellement = défavorable.
Score = (sable − argile) normalisé percentiles.
"""

import ee

from engine.gee_utils import normaliser


def compute_pedology(zone: ee.Geometry) -> ee.Image:
    """Calcule la couche C6 (pédologie) normalisée 0-1."""
    clay = (
        ee.Image("projects/soilgrids-isric/clay_mean")
        .select("clay_0-5cm_mean")
        .clip(zone)
    )
    sand = (
        ee.Image("projects/soilgrids-isric/sand_mean")
        .select("sand_0-5cm_mean")
        .clip(zone)
    )
    sol_diff = sand.subtract(clay).rename("sol_diff")
    return normaliser(sol_diff, "C6", zone, scale=250).rename("C6") \
        .clip(zone)
