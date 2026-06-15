# -*- coding: utf-8 -*-
"""
HYDRA — engine/scoring/normalizer.py
=======================================
Normalisation robuste par percentiles.

Méthode : percentiles [5, 95] puis clamp(0, 1).
Évite que des valeurs extrêmes écrasent le contraste.

Formule :
  normalisé = (valeur - p5) / (p95 - p5)
  normalisé = clamp(normalisé, 0, 1)

⚠️ Si p5 == p95 (facteur constant sur la zone) → division par zéro.
   C'est la raison principale d'écarter les facteurs trop grossiers
   (EMAG2, USGS, GRACE, CHIRPS) à 1 km de rayon.

À implémenter au Sprint 3.
"""


def normaliser(image, nom, echelle, zone):
    """
    Normalise une image GEE par percentiles [5, 95] + clamp(0, 1).

    Args:
        image: ee.Image — image à normaliser
        nom: str — nom de la bande (pour les clés du reduceRegion)
        echelle: int — résolution en mètres (scale du reduceRegion)
        zone: ee.Geometry — zone d'analyse

    Returns:
        ee.Image — image normalisée 0-1
    """
    raise NotImplementedError(
        "normaliser : à implémenter au Sprint 3 "
        "(reduceRegion percentile [5,95] + clamp)."
    )
