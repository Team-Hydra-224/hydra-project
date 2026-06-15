# -*- coding: utf-8 -*-
"""
HYDRA — engine/mock_data.py
============================
Données fictives pour le Sprint 1 (squelette sans GEE).

Ce module fournit de FAUSSES données de candidats, basées sur les VRAIS
résultats de l'étude Donghol Dayebhé (Labé, Guinée) — notre cas de référence.

Les sous-scores C1..C6 de chaque candidat sont réels (issus de l'analyse GEE
de novembre), ce qui permet de tester la combinaison pondérée (Phase B)
avec des données crédibles AVANT d'avoir branché GEE.

Au Sprint 2, ce module sera remplacé progressivement par les vrais modules
engine/factors/*.py — mais il restera utile comme mode démo hors-ligne.
"""

# ── Points de référence du cas Donghol Dayebhé ──────────────────────────
FORAGE_REF = {
    "nom": "Forage actuel (ÉCHEC — dolérite)",
    "lat": 11.255046,
    "lon": -12.281277,
    "altitude_m": 1120,
}

SEV_REF = {
    "nom": "Point SEV techniciens",
    "lat": 11.25821,
    "lon": -12.28593,
}

# ── Candidats mock ───────────────────────────────────────────────────────
# Sous-scores RÉELS de l'étude Donghol Dayebhé (rayon 1 km).
# Mapping anciens codes → nouveaux codes V1 (6 facteurs) :
#   C1_lin → C1 (linéaments)  | C2_topo → C2 (topographie)
#   [C3 hydro : pas mesuré à l'époque → valeur plausible simulée]
#   C3_veg → C4 (végétation)  | C4_lulc → C5 (LULC) | C5_sol → C6 (pédologie)
#
# offset_lat / offset_lon : position RELATIVE au centre d'analyse.
# Le mock translate les candidats autour du point demandé par l'utilisateur,
# pour que la démo fonctionne avec n'importe quelles coordonnées.

_CANDIDATS_BASE = [
    {
        "id": "A",
        "offset_lat": 11.252305 - FORAGE_REF["lat"],   # -0.002741
        "offset_lon": -12.284060 - FORAGE_REF["lon"],  # -0.002783
        "scores": {"C1": 0.5631, "C2": 0.6074, "C3": 0.55,
                   "C4": 0.6975, "C5": 0.8169, "C6": 0.3433},
        "altitude_m": 1076, "ndvi": 0.564, "pente_deg": 3.2,
        "dist_riviere_m": 410,
    },
    {
        "id": "B",
        "offset_lat": 11.249088 - FORAGE_REF["lat"],
        "offset_lon": -12.279433 - FORAGE_REF["lon"],
        "scores": {"C1": 0.5365, "C2": 0.6502, "C3": 0.62,
                   "C4": 0.5230, "C5": 0.7759, "C6": 0.7737},
        "altitude_m": 1120, "ndvi": 0.378, "pente_deg": 2.1,
        "dist_riviere_m": 320,
    },
    {
        "id": "C",
        "offset_lat": 11.263202 - FORAGE_REF["lat"],
        "offset_lon": -12.278540 - FORAGE_REF["lon"],
        "scores": {"C1": 0.6831, "C2": 0.4638, "C3": 0.41,
                   "C4": 0.6107, "C5": 0.8109, "C6": 0.3404},
        "altitude_m": 1118, "ndvi": 0.478, "pente_deg": 5.8,
        "dist_riviere_m": 780,
    },
    {
        "id": "D",
        "offset_lat": 11.252828 - FORAGE_REF["lat"],
        "offset_lon": -12.280190 - FORAGE_REF["lon"],
        "scores": {"C1": 0.3825, "C2": 0.5811, "C3": 0.68,
                   "C4": 0.7680, "C5": 0.8596, "C6": 0.7234},
        "altitude_m": 1109, "ndvi": 0.641, "pente_deg": 2.7,
        "dist_riviere_m": 250,
    },
    {
        "id": "E",
        "offset_lat": 11.253069 - FORAGE_REF["lat"],
        "offset_lon": -12.278486 - FORAGE_REF["lon"],
        "scores": {"C1": 0.4368, "C2": 0.5441, "C3": 0.47,
                   "C4": 0.6209, "C5": 0.7284, "C6": 0.4255},
        "altitude_m": 1125, "ndvi": 0.483, "pente_deg": 4.4,
        "dist_riviere_m": 560,
    },
]


def get_mock_candidates(lat_centre: float, lon_centre: float) -> list[dict]:
    """
    Retourne les candidats mock, translatés autour du centre demandé.

    Chaque candidat contient :
      - lat, lon          : coordonnées absolues (centre + offset)
      - scores            : dict des 6 sous-scores C1..C6 (0-1)
      - altitude_m, ndvi, pente_deg, dist_riviere_m : indicateurs ABSOLUS
        (décision de réanalyse n°1 : toujours fournir des indicateurs absolus
         à côté du score relatif)
    """
    candidats = []
    for base in _CANDIDATS_BASE:
        candidats.append({
            "id": base["id"],
            "lat": lat_centre + base["offset_lat"],
            "lon": lon_centre + base["offset_lon"],
            "scores": dict(base["scores"]),
            "altitude_m": base["altitude_m"],
            "ndvi": base["ndvi"],
            "pente_deg": base["pente_deg"],
            "dist_riviere_m": base["dist_riviere_m"],
        })
    return candidats
