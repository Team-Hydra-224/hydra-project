# -*- coding: utf-8 -*-
"""
HYDRA — engine/export/pdf_generator.py
=======================================
Rapport PDF d'analyse hydrogéologique (ReportLab).

DEUX MODES (paramètre `confidentiel`) :
  - "client"  : rapport public. Masque la pondération, la méthodologie
                détaillée et le tableau des sous-scores C1..C6. Méthode
                résumée en une phrase générique. → à remettre aux clients.
  - "expert"  : rapport interne complet. Affiche tout (poids, sous-scores,
                méthodologie détaillée). → pour l'équipe HYDRA.

Logo HYDRA généré en code (engine/export/logo.py), aucun fichier requis.
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
    TableStyle,
)

from engine.analyzer import NOMS_FACTEURS, verdict
from engine.export.logo import logo_png

BLEU_NUIT = colors.HexColor("#13315C")
BLEU = colors.HexColor("#065A82")
TEAL = colors.HexColor("#1C7293")
ROUGE = colors.HexColor("#B23A48")
GRIS_DOUX = colors.HexColor("#E8F0F8")
BORDURE = colors.HexColor("#D4DEEA")


def generer_pdf(candidats, meta, poids, plan_png,
                carte_png=None, confidentiel="client") -> bytes:
    """
    Génère le rapport PDF (bytes).

    Args:
        candidats    : sortie de analyzer.combine()
        meta         : {lat, lon, rayon, mode, nb_points}
        poids        : poids utilisés {C1: 0.35, ...}
        plan_png     : plan de situation (bytes PNG) — schématique ou satellite
        carte_png    : miniature score pondéré (bytes PNG) ou None
        confidentiel : "client" (masque modèle) | "expert" (tout visible)
    """
    expert = (confidentiel == "expert")
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm,
        topMargin=1.2 * cm, bottomMargin=1.6 * cm,
        title="HYDRA — Rapport d'analyse hydrogéologique",
    )

    styles = getSampleStyleSheet()
    st_titre = ParagraphStyle("titre", parent=styles["Title"], fontSize=24,
                              textColor=BLEU_NUIT, spaceAfter=0,
                              alignment=TA_LEFT, leftIndent=4)
    st_soustitre = ParagraphStyle("sous", parent=styles["Normal"],
                                  fontSize=9.5, textColor=TEAL,
                                  alignment=TA_LEFT, leftIndent=6)
    st_h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13,
                           textColor=BLEU, spaceBefore=12, spaceAfter=6)
    st_normal = ParagraphStyle("norm", parent=styles["Normal"],
                               fontSize=9.5, leading=13)
    st_avert = ParagraphStyle("avert", parent=styles["Normal"], fontSize=9,
                              leading=12, textColor=ROUGE)
    st_pied = ParagraphStyle("pied", parent=styles["Normal"], fontSize=7.5,
                             textColor=colors.grey, alignment=TA_CENTER)
    st_badge = ParagraphStyle("badge", parent=styles["Normal"], fontSize=8,
                              textColor=colors.grey, alignment=TA_CENTER)

    el = []

    # ── En-tête : logo + titre côte à côte ───────────────────────
    logo_img = Image(io.BytesIO(logo_png()))
    logo_img._restrictSize(2.0 * cm, 2.0 * cm)
    bloc_titre = [
        Paragraph("HYDRA", st_titre),
        Paragraph("Hydrogeological Data &amp; Research for Africa — "
                  "Trouver l'eau avant de forer", st_soustitre),
    ]
    entete = Table([[logo_img, bloc_titre]], colWidths=[2.3 * cm, 14 * cm])
    entete.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
    ]))
    el.append(entete)
    el.append(Spacer(1, 4))
    el.append(Table([[""]], colWidths=[16.8 * cm], rowHeights=[2],
                    style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), TEAL)])))
    el.append(Spacer(1, 10))

    # ── Métadonnées ──────────────────────────────────────────────
    mode_txt = ("Satellite réel (Google Earth Engine)"
                if meta["mode"] == "gee" else "Démonstration")
    meta_data = [
        ["Date de l'analyse", f"{datetime.now():%d/%m/%Y %H:%M}"],
        ["Centre de la zone", f"{meta['lat']:.6f}, {meta['lon']:.6f}"],
        ["Rayon d'analyse", f"{meta['rayon']} m"],
        ["Moteur", mode_txt],
        ["Points évalués", str(meta.get("nb_points", "—"))],
    ]
    t_meta = Table(meta_data, colWidths=[5 * cm, 11 * cm])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), GRIS_DOUX),
        ("TEXTCOLOR", (0, 0), (0, -1), BLEU_NUIT),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDURE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    el.append(t_meta)
    el.append(Spacer(1, 8))

    el.append(Paragraph(
        "<b>⚠ AVERTISSEMENT IMPORTANT :</b> les scores de ce rapport sont "
        "<b>RELATIFS à la zone analysée</b> — ils classent les emplacements "
        "entre eux mais ne constituent pas une probabilité absolue de "
        "trouver de l'eau. HYDRA recommande de <b>ne jamais forer sans "
        "confirmation préalable par Sondage Électrique Vertical (SEV)</b> "
        "sur les points candidats.", st_avert))
    el.append(Spacer(1, 10))

    if carte_png:
        el.append(Paragraph("Carte du score (satellite)", st_h2))
        ic = Image(io.BytesIO(carte_png))
        ic._restrictSize(16 * cm, 8.2 * cm)
        el.append(ic)
        el.append(Paragraph("Palette : sombre = défavorable → vert → jaune "
                            "→ rouge = très favorable. Eau exclue.", st_normal))
        el.append(Spacer(1, 6))

    el.append(Paragraph("Plan de situation", st_h2))
    ip = Image(io.BytesIO(plan_png))
    taille = (9.5 * cm) if carte_png else (12.5 * cm)
    ip._restrictSize(taille, taille)
    el.append(ip)

    el.append(PageBreak())

    # ════════════════════════════════════════════════════════════
    # PAGE 2 — Résultats
    # ════════════════════════════════════════════════════════════
    el.append(Paragraph("Candidats recommandés", st_h2))
    entetes = ["Rang", "Score", "Verdict", "Latitude", "Longitude",
               "Alt. (m)", "NDVI", "Pente (°)", "Riv. (m)", "Centre (m)"]
    lignes = [entetes]
    for c in candidats:
        lignes.append([
            f"#{c['rang']}", f"{c['score']:.3f}",
            verdict(c["score"]).split(" ", 1)[-1],
            f"{c['lat']:.6f}", f"{c['lon']:.6f}", str(c["altitude_m"]),
            str(c["ndvi"]), str(c["pente_deg"]),
            str(c["dist_riviere_m"]), str(c["distance_centre_m"]),
        ])
    t_cand = Table(lignes, repeatRows=1)
    t_cand.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLEU_NUIT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDURE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_DOUX]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    el.append(t_cand)
    el.append(Paragraph(
        "<i>NDVI &gt; 0,4 en saison sèche suggère une végétation alimentée "
        "par une nappe. Une faible pente et la proximité d'une rivière "
        "favorisent la recharge.</i>", st_normal))

    # ── Sections CONFIDENTIELLES (mode expert uniquement) ────────
    if expert:
        el.append(Paragraph("Détail des facteurs par candidat "
                            "(interne)", st_h2))
        codes = sorted(poids.keys())
        l2 = [["Rang"] + codes]
        for c in candidats:
            l2.append([f"#{c['rang']}"] +
                      [f"{c['scores'][code]:.3f}" for code in codes])
        t2 = Table(l2, repeatRows=1)
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), TEAL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDURE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_DOUX]),
        ]))
        el.append(t2)
        el.append(Spacer(1, 6))

        el.append(Paragraph("Pondération des facteurs (interne)", st_h2))
        l3 = [["Code", "Facteur", "Poids"]]
        for code in codes:
            l3.append([code, NOMS_FACTEURS[code],
                       f"{int(round(poids[code] * 100))} %"])
        t3 = Table(l3, colWidths=[1.6 * cm, 9 * cm, 2.4 * cm])
        t3.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLEU),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDURE),
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ]))
        el.append(t3)
        el.append(Spacer(1, 8))

        el.append(Paragraph("Méthodologie (interne)", st_h2))
        el.append(Paragraph(
            "L'analyse croise six familles de facteurs satellitaires : "
            "densité de linéaments (fusion radar ALOS PALSAR / optique "
            "Sentinel-2, masquage anthropique), topographie et TWI (SRTM, "
            "MERIT Hydro), hydrographie (distance rivières, drainage, HAND "
            "— MERIT Hydro), végétation en saison sèche (NDVI/NDWI Sentinel-2 "
            "et saisonnalité), occupation des sols (ESA WorldCover, eau "
            "exclue) et texture des sols (SoilGrids). Normalisation par "
            "percentiles [5,95] sur la zone, puis combinaison pondérée. "
            "Candidats espacés pour couvrir des cibles distinctes.",
            st_normal))
        el.append(Spacer(1, 6))
    else:
        # Version CLIENT : méthode générique, sans révéler le modèle
        el.append(Paragraph("Méthode", st_h2))
        el.append(Paragraph(
            "Les emplacements sont évalués par analyse multicritère de "
            "données satellitaires (structure géologique, topographie, "
            "hydrographie, végétation, occupation et nature des sols). "
            "Les points les plus favorables, suffisamment espacés, sont "
            "retenus comme cibles prioritaires à confirmer sur le terrain.",
            st_normal))
        el.append(Spacer(1, 6))

    # ── Recommandation (les deux modes) ──────────────────────────
    deux = ", ".join(f"#{c['rang']} ({c['lat']:.6f}, {c['lon']:.6f})"
                     for c in candidats[:2])
    el.append(Paragraph("Recommandation", st_h2))
    el.append(Paragraph(
        f"<b>Réaliser un SEV en priorité sur les candidats {deux}.</b> "
        "Ne forer qu'après confirmation géophysique de la présence et de "
        "la profondeur de l'aquifère.", st_normal))

    el.append(Spacer(1, 14))
    badge = ("RAPPORT INTERNE — usage HYDRA"
             if expert else "Document remis au client")
    el.append(Paragraph(badge, st_badge))
    el.append(Paragraph(
        f"HYDRA — Rapport généré le {datetime.now():%d/%m/%Y à %H:%M}. "
        "Document indicatif — ne remplace pas une étude géophysique de "
        "terrain.", st_pied))

    doc.build(el)
    return buffer.getvalue()
