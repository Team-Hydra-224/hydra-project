# -*- coding: utf-8 -*-
"""
HYDRA — engine/scoring/combiner.py
=====================================
Combinaison pondérée des couches C1..C6.

Formule : score = Σ(Ci × poids_i) puis updateMask(mask_eau)

Phase B de l'architecture 2 phases : cette opération est INSTANTANÉE
et ne touche pas à GEE. Elle est appelée à chaque mouvement de slider.

À implémenter au Sprint 3 (actuellement la logique est dans analyzer.py).
"""


def combine_layers(layers, poids, mask_eau):
    """
    Combine les couches normalisées avec les poids donnés.

    Args:
        layers: dict[str, ee.Image] — couches C1..C6 normalisées 0-1
        poids: dict[str, float] — poids par facteur (somme = 1.0)
        mask_eau: ee.Image — masque d'exclusion eau/neige

    Returns:
        ee.Image — score final 0-1, masqué
    """
    raise NotImplementedError(
        "combine_layers : à implémenter au Sprint 3 "
        "(somme pondérée + masque eau)."
    )
