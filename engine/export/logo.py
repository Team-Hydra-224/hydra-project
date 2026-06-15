# -*- coding: utf-8 -*-
"""
HYDRA — engine/export/logo.py
==============================
Logo HYDRA généré en code (aucun fichier externe requis) : une goutte
d'eau stylisée sur pastille teal, cohérente avec les présentations.

Mise en cache module-level : le PNG n'est dessiné qu'une fois par session.
Si un vrai fichier logo est fourni plus tard, remplacer logo_png() par
une simple lecture de fichier.
"""

from __future__ import annotations

import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, PathPatch
from matplotlib.path import Path

_CACHE: bytes | None = None


def logo_png() -> bytes:
    """Retourne le logo HYDRA (PNG bytes, fond transparent)."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    fig, ax = plt.subplots(figsize=(1.2, 1.2), dpi=200)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.axis("off")

    # Pastille ronde teal
    ax.add_patch(Circle((50, 50), 46, color="#1C7293", zorder=1))

    # Goutte d'eau (forme fermée par courbes de Bézier)
    verts = [
        (50, 80),    # pointe haute
        (30, 50), (35, 28), (50, 25),   # côté gauche descendant
        (65, 28), (70, 50), (50, 80),   # côté droit remontant
    ]
    codes = [Path.MOVETO, Path.CURVE3, Path.CURVE3, Path.CURVE3,
             Path.CURVE3, Path.CURVE3, Path.CURVE3]
    goutte = PathPatch(Path(verts, codes), facecolor="#7FD0E8",
                       edgecolor="white", linewidth=1.2, zorder=2)
    ax.add_patch(goutte)

    # Petit reflet
    ax.add_patch(Circle((44, 45), 5, color="white", alpha=0.7, zorder=3))

    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True, bbox_inches="tight",
                pad_inches=0)
    plt.close(fig)
    _CACHE = buf.getvalue()
    return _CACHE
