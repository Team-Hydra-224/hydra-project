# -*- coding: utf-8 -*-
"""
HYDRA — engine/export/map_generator.py
=======================================
Visuels pour le rapport PDF.

  - plan_situation()   : plan schématique matplotlib (hors-ligne).
                         ORIENTATION CARTOGRAPHIQUE STANDARD :
                         Ouest à gauche, Est à droite, Nord en haut.
  - plan_sur_satellite(): plan des candidats superposé à la vraie image
                         satellite de la zone (mode gee, nécessite réseau).
  - thumbnail_score()  : miniature du score final pondéré (mode gee).
"""

from __future__ import annotations

import io
from math import cos, radians

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

COULEURS = ["#1E8449", "#065A82", "#7D3C98", "#C8860D", "#21295C"]


def _xy_metres(c_lat, c_lon, lat, lon):
    """Décalage (est+, nord+) en mètres d'un point par rapport au centre."""
    dx = (c_lon - lon) * 111_320 * cos(radians(lat))   # +est
    dy = (c_lat - lat) * 111_320                        # +nord
    return dx, dy


def plan_situation(candidats, lat, lon, rayon) -> bytes:
    """
    Plan schématique (PNG bytes). Orientation cartographique standard.
    """
    fig, ax = plt.subplots(figsize=(6.2, 6.2), dpi=150)

    ax.add_patch(Circle((0, 0), rayon, fill=False, color="#1C7293",
                        linewidth=2, linestyle="--",
                        label=f"Zone d'analyse ({rayon} m)"))
    ax.plot(0, 0, marker="P", markersize=14, color="#B23A48",
            linestyle="none", label="Centre de la zone")

    for c in candidats:
        dx, dy = _xy_metres(c["lat"], c["lon"], lat, lon)
        coul = COULEURS[(c["rang"] - 1) % len(COULEURS)]
        ax.plot(dx, dy, marker="*", markersize=20, color=coul,
                linestyle="none")
        ax.annotate(f"#{c['rang']}\n{c['score']:.3f}", (dx, dy),
                    textcoords="offset points", xytext=(10, 8),
                    fontsize=9, fontweight="bold", color=coul)

    marge = rayon * 1.18
    ax.set_xlim(-marge, marge)       # Ouest (-) à gauche, Est (+) à droite
    ax.set_ylim(-marge, marge)       # Sud (-) en bas, Nord (+) en haut
    ax.set_aspect("equal")
    ax.set_xlabel("Ouest  ←   →  Est  (mètres)", fontsize=9)
    ax.set_ylabel("Sud  ←   →  Nord  (mètres)", fontsize=9)
    ax.set_title("Plan de situation des candidats", fontsize=12,
                 fontweight="bold", color="#13315C")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower left", fontsize=8)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def plan_sur_satellite(analyzer, candidats, lat, lon, rayon,
                       dimension_px: int = 900) -> bytes | None:
    """
    Plan des candidats superposé à la vraie image satellite (mode gee).
    Récupère une vignette Sentinel-2 vraies couleurs de la zone via GEE,
    puis dessine cercle + centre + candidats par-dessus.
    Retourne None en mock ou si la récupération échoue.
    """
    if analyzer.mode != "gee":
        return None
    try:
        import ee
        import urllib.request
        import matplotlib.image as mpimg

        zone = analyzer._zone

        # Composite Sentinel-2 vraies couleurs (saison sèche, sans nuages)
        s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
              .filterBounds(zone)
              .filter(ee.Filter.calendarRange(1, 4, "month"))
              .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
              .select(["B4", "B3", "B2"])
              .median())

        url = s2.getThumbURL({
            "region": zone,
            "dimensions": dimension_px,
            "format": "png",
            "min": 0, "max": 3000,
        })
        with urllib.request.urlopen(url, timeout=60) as rep:
            img_bytes = rep.read()

        img = mpimg.imread(io.BytesIO(img_bytes), format="png")

        # Étendue de l'image en mètres (la vignette couvre le bounding box
        # de la zone, soit ± rayon dans chaque direction)
        ext = rayon
        fig, ax = plt.subplots(figsize=(6.2, 6.2), dpi=150)
        # extent : Ouest à gauche → on mappe [-ext, ext] en X (est+ à droite)
        ax.imshow(img, extent=[-ext, ext, -ext, ext], origin="upper")

        ax.add_patch(Circle((0, 0), rayon, fill=False, color="white",
                            linewidth=2, linestyle="--"))
        ax.plot(0, 0, marker="P", markersize=14, color="#FF3B3B",
                linestyle="none")

        for c in candidats:
            dx, dy = _xy_metres(c["lat"], c["lon"], lat, lon)
            coul = COULEURS[(c["rang"] - 1) % len(COULEURS)]
            ax.plot(dx, dy, marker="*", markersize=20, color=coul,
                    markeredgecolor="white", markeredgewidth=0.8,
                    linestyle="none")
            ax.annotate(f"#{c['rang']}", (dx, dy),
                        textcoords="offset points", xytext=(9, 7),
                        fontsize=10, fontweight="bold", color="white")

        ax.set_xlim(-ext, ext)
        ax.set_ylim(-ext, ext)
        ax.set_aspect("equal")
        ax.set_xlabel("Ouest  ←   →  Est  (mètres)", fontsize=9)
        ax.set_ylabel("Sud  ←   →  Nord  (mètres)", fontsize=9)
        ax.set_title("Candidats sur image satellite", fontsize=12,
                     fontweight="bold", color="#13315C")

        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        return buf.getvalue()
    except Exception:
        return None


def thumbnail_score(analyzer, poids, dimension_px: int = 640) -> bytes | None:
    """Miniature PNG du score final pondéré (mode gee) ou None."""
    if analyzer.mode != "gee":
        return None
    try:
        import ee
        import urllib.request
        from engine.gee_utils import PALETTE_SCORE

        score = ee.Image(0)
        for code, image in analyzer._images.items():
            score = score.add(image.multiply(poids[code]))
        score = score.rename("score").updateMask(analyzer._mask_eau)

        url = score.getThumbURL({
            "region": analyzer._zone,
            "dimensions": dimension_px,
            "format": "png",
            "min": 0, "max": 1,
            "palette": PALETTE_SCORE,
        })
        with urllib.request.urlopen(url, timeout=60) as rep:
            return rep.read()
    except Exception:
        return None
