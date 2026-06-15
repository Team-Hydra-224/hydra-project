# -*- coding: utf-8 -*-
"""
HYDRA — engine/factors/c1_lineaments.py
========================================
C1 — Linéaments / fractures géologiques (poids par défaut : 35%).

Méthode (validée, voir CONTEXTE_HYDRA.md §4 et §7.3) :
  1. Deux sources complémentaires :
       - Radar  : ALOS PALSAR bande L (pénètre la végétation)   → 40%
       - Optique: Sentinel-2 saison sèche (fin contraste 10 m)  → 60%
  2. MASQUE ANTHROPIQUE (décision de réanalyse n°2) : on retire le bâti
     (classe LULC 50) et les cultures (classe 40) AVANT la détection —
     sinon les routes, toits et limites de parcelles deviennent de faux
     "linéaments" et polluent 35% du score.
  3. Détection de contours par gradient de Sobel + renfort Laplacien.
  4. Heatmap de densité de fracturation (convolution gaussienne 200 m).
  5. Normalisation percentiles [5,95] par source, puis fusion pondérée.

Note technique : dans GEE, ee.Kernel.rotate(n) tourne le noyau de n × 90°
(et non n degrés). Le gradient 2D sqrt(Gx² + Gy²) capte mathématiquement
toutes les orientations de linéaments (y compris diagonales) — les 4
"directions" du prototype JS étaient redondantes. On utilise donc le
gradient Sobel standard, plus propre et plus rapide.
"""

import ee

from engine.gee_utils import normaliser

# Pondération interne de la fusion radar / optique
POIDS_RADAR = 0.40
POIDS_OPTIQUE = 0.60

# Marge anti effet de bord : les convolutions (Sobel, gaussienne 200 m)
# sont calculées sur une zone ÉLARGIE puis découpées à la zone d'analyse,
# sinon les voisinages tronqués au bord créent de faux gradients.
MARGE_BORD_M = 300


def compute_lineaments(zone: ee.Geometry) -> ee.Image:
    """
    Calcule la couche C1 (densité de linéaments) normalisée 0-1.

    Args:
        zone : géométrie GEE de la zone d'analyse (cercle bufferisé).

    Returns:
        ee.Image mono-bande 'C1', valeurs 0-1 (1 = nœud de fractures).
    """
    zone_calc = zone.buffer(MARGE_BORD_M)   # zone élargie pour les calculs
    masque_naturel = _masque_anthropique(zone_calc)

    # ── Source 1 : radar ALOS PALSAR bande L ────────────────────────
    palsar_db = _charger_palsar(zone_calc).updateMask(masque_naturel)
    den_radar = _densite_lineaments(palsar_db)
    # Normalisation sur la VRAIE zone (les percentiles doivent refléter
    # la zone d'analyse, pas la marge technique)
    den_radar = normaliser(den_radar, "lin_radar", zone, scale=25)

    # ── Source 2 : optique Sentinel-2 (panchromatique synthétique) ──
    pan = _charger_s2_pan(zone_calc).updateMask(masque_naturel)
    den_optique = _densite_lineaments(pan)
    den_optique = normaliser(den_optique, "lin_optique", zone, scale=10)

    # ── Fusion radar 40% + optique 60% ──────────────────────────────
    c1 = (
        den_radar.multiply(POIDS_RADAR)
        .add(den_optique.multiply(POIDS_OPTIQUE))
        .rename("C1")
        .clip(zone)
    )
    return c1


# ════════════════════════════════════════════════════════════════════
# Sous-fonctions
# ════════════════════════════════════════════════════════════════════

def _masque_anthropique(zone: ee.Geometry) -> ee.Image:
    """
    Masque des surfaces NATURELLES : exclut bâti (50) et cultures (40)
    pour éviter de détecter routes/toits/parcelles comme des fractures.
    1 = pixel naturel gardé, masqué sinon.
    """
    lulc = ee.ImageCollection("ESA/WorldCover/v200").first().clip(zone)
    return lulc.neq(50).And(lulc.neq(40))


def _charger_palsar(zone: ee.Geometry) -> ee.Image:
    """ALOS PALSAR bande L (HH), médiane des époques, en décibels."""
    palsar = (
        ee.ImageCollection("JAXA/ALOS/PALSAR/YEARLY/SAR_EPOCH")
        .filterBounds(zone)
        .select("HH")
        .median()
        .clip(zone)
    )
    # Conversion en dB pour une dynamique exploitable par le gradient
    return ee.Image(10).multiply(palsar.log10()).rename("HH_db")


def _charger_s2_pan(zone: ee.Geometry) -> ee.Image:
    """
    Sentinel-2 saison sèche (janvier-avril), médiane sans nuages,
    réduite à une bande panchromatique synthétique (mélange visible).
    """
    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(zone)
        .filter(ee.Filter.calendarRange(1, 4, "month"))
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 15))
        .select(["B2", "B3", "B4"])
        .median()
        .clip(zone)
    )
    return s2.expression(
        "0.3*B4 + 0.6*B3 + 0.1*B2",
        {"B4": s2.select("B4"), "B3": s2.select("B3"), "B2": s2.select("B2")},
    ).rename("pan")


def _densite_lineaments(image: ee.Image) -> ee.Image:
    """
    Détection de linéaments puis heatmap de densité.

    1. Lissage médian anti-bruit (speckle radar / texture optique)
    2. Gradient de Sobel 2D : magnitude = sqrt(Gx² + Gy²)
       (capte toutes les orientations, diagonales comprises)
    3. + 30% de |Laplacien| pour renforcer les contours nets
    4. Convolution gaussienne 200 m → densité de fracturation
    """
    lisse = image.focal_median(radius=2, kernelType="square", units="pixels")

    kernel_x = ee.Kernel.sobel()              # gradient horizontal
    kernel_y = ee.Kernel.sobel().rotate(1)    # 1 × 90° → gradient vertical

    gx = lisse.convolve(kernel_x)
    gy = lisse.convolve(kernel_y)
    laplace = lisse.convolve(ee.Kernel.laplacian8())

    magnitude = (
        gx.pow(2).add(gy.pow(2)).sqrt()
        .add(laplace.abs().multiply(0.3))
    )

    return magnitude.convolve(
        ee.Kernel.gaussian(
            radius=200, sigma=80, units="meters", normalize=True
        )
    )
