# -*- coding: utf-8 -*-
"""
HYDRA — engine/gee_utils.py
============================
Utilitaires communs Google Earth Engine, partagés par tous les modules
de facteurs (C1..C6).

Contenu :
  - init_gee()              : initialisation (une seule fois par session)
  - normaliser()            : normalisation robuste percentiles [5,95] + clamp
  - tile_url()              : URL de tuiles pour affichage Folium
  - score_au_point()        : échantillonne une image en un point GPS

Règles du projet (CONTEXTE_HYDRA.md §6) appliquées ici :
  - normalisation par percentiles, jamais min/max bruts
  - toujours maxPixels=1e9 et bestEffort=True dans les reduceRegion
"""

import ee

# Projet Google Cloud lié au compte GEE de l'équipe
GEE_PROJECT = "project-test-499419"

_initialise = False


def init_gee(project: str = GEE_PROJECT) -> None:
    """
    Initialise la connexion Google Earth Engine (une seule fois).

    Premier lancement sur une machine : si l'initialisation échoue,
    lance le flux d'authentification (ouvre le navigateur), puis réessaie.
    """
    global _initialise
    if _initialise:
        return
    try:
        ee.Initialize(project=project)
    except Exception:
        # Pas encore authentifié sur cette machine → flux navigateur
        ee.Authenticate()
        ee.Initialize(project=project)
    _initialise = True


def normaliser(image: ee.Image, band: str, zone: ee.Geometry,
               scale: int, inverser: bool = False) -> ee.Image:
    """
    Normalisation robuste 0-1 par percentiles [5, 95] + clamp.

    Args:
        image    : image GEE mono-bande à normaliser
        band     : nom de la bande (sert aux clés du reduceRegion)
        zone     : géométrie de la zone d'analyse
        scale    : résolution du calcul en mètres
        inverser : True si "valeur faible = favorable"
                   (ex : pente, distance rivière, delta NDVI)

    Returns:
        Image normalisée 0-1 (1 = favorable), même nom de bande.
    """
    image = image.rename(band)
    pct = image.reduceRegion(
        reducer=ee.Reducer.percentile([5, 95]),
        geometry=zone,
        scale=scale,
        maxPixels=int(1e9),
        bestEffort=True,
    )
    lo = ee.Number(pct.get(f"{band}_p5"))
    hi = ee.Number(pct.get(f"{band}_p95"))

    norm = image.subtract(lo).divide(hi.subtract(lo)).clamp(0, 1)
    if inverser:
        norm = ee.Image(1).subtract(norm)
    return norm.rename(band)


def tile_url(image: ee.Image, vis_params: dict) -> str:
    """
    Retourne l'URL de tuiles XYZ d'une image GEE, utilisable
    directement dans folium.TileLayer(tiles=url).
    """
    map_id = image.getMapId(vis_params)
    return map_id["tile_fetcher"].url_format


def score_au_point(image: ee.Image, band: str,
                   lat: float, lon: float,
                   buffer_m: int = 100, scale: int = 10) -> float | None:
    """
    Échantillonne la valeur moyenne d'une image autour d'un point GPS.
    Retourne None si aucune donnée (point masqué, hors zone...).

    NOTE : déclenche un .getInfo() (aller-retour serveur). À utiliser
    pendant la PHASE A uniquement — jamais dans la boucle des sliders.
    """
    point = ee.Geometry.Point([lon, lat]).buffer(buffer_m)
    result = image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=point,
        scale=scale,
        maxPixels=int(1e9),
        bestEffort=True,
    ).getInfo()
    valeur = result.get(band)
    return round(valeur, 4) if valeur is not None else None


# Palette standard HYDRA pour les couches de score (bleu → vert → rouge)
PALETTE_SCORE = [
    "000033", "0a3d62", "1e8449", "f4d03f", "e74c3c", "ff0000",
]
