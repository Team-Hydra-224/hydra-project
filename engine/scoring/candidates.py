# -*- coding: utf-8 -*-
"""
HYDRA — engine/scoring/candidates.py
=====================================
Sélection des meilleurs candidats à partir de la grille de points
échantillonnée en Phase A.

100 % LOCAL (aucun appel GEE) — fait partie de la Phase B instantanée.

Algorithme : tri par score décroissant + sélection GLOUTONNE avec
espacement minimal entre candidats (évite 5 étoiles collées sur le
même nœud de fractures — on veut 5 SITES distincts à proposer au SEV).
"""

from math import sqrt, cos, radians


def _distance_m(lat1, lon1, lat2, lon2) -> float:
    """Distance plane approchée en mètres (suffisant < 10 km)."""
    dlat = (lat2 - lat1) * 111_320
    dlon = (lon2 - lon1) * 111_320 * cos(radians(lat1))
    return sqrt(dlat ** 2 + dlon ** 2)


def selectionner_candidats(points: list[dict], poids: dict,
                           lat_centre: float, lon_centre: float,
                           n: int = 5,
                           espacement_min_m: float = 150.0) -> list[dict]:
    """
    Classe les points de la grille et retourne les n meilleurs,
    espacés d'au moins `espacement_min_m` les uns des autres.

    Args:
        points : grille Phase A — chaque point contient au minimum
                 {lat, lon, scores: {C1..C6}, alt, ndvi, pente, dist_riv}
        poids  : dict des poids {C1: 0.35, ...} sommant à 1.0

    Returns:
        Liste de candidats au format standard HYDRA :
        rang, score, lat, lon, scores, altitude_m, ndvi, pente_deg,
        dist_riviere_m, distance_centre_m
    """
    # 1. Score pondéré de chaque point (instantané, pur Python)
    notes = []
    for p in points:
        score = sum(p["scores"][c] * poids[c] for c in poids)
        notes.append((score, p))
    notes.sort(key=lambda t: t[0], reverse=True)

    # 2. Sélection gloutonne avec espacement minimal
    retenus: list[dict] = []
    for score, p in notes:
        if len(retenus) >= n:
            break
        trop_proche = any(
            _distance_m(p["lat"], p["lon"], r["lat"], r["lon"])
            < espacement_min_m
            for r in retenus
        )
        if trop_proche:
            continue
        retenus.append({
            "rang": len(retenus) + 1,
            "score": round(score, 4),
            "lat": round(p["lat"], 6),
            "lon": round(p["lon"], 6),
            "scores": {c: round(p["scores"][c], 4) for c in poids},
            "altitude_m": int(p["alt"]) if p.get("alt") is not None else None,
            "ndvi": round(p["ndvi"], 3) if p.get("ndvi") is not None else None,
            "pente_deg": round(p["pente"], 1)
                if p.get("pente") is not None else None,
            "dist_riviere_m": int(p["dist_riv"])
                if p.get("dist_riv") is not None else None,
            "distance_centre_m": int(_distance_m(
                lat_centre, lon_centre, p["lat"], p["lon"])),
        })
    return retenus
