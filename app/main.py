# -*- coding: utf-8 -*-
"""
HYDRA — app/main.py
====================
Interface utilisateur Streamlit — Sprint 3 (moteur GEE complet).

Lancement (depuis la racine du projet hydra/) :
    streamlit run app/main.py

MODES :
  - Démo (mock) : données fictives, aucune connexion requise.
  - GEE réel    : les 6 facteurs calculés sur Google Earth Engine,
                  candidats extraits d'une vraie grille de ~800 points.

ARCHITECTURE 2 PHASES :
  - Phase A (compute_layers, cachée) : couches GEE + grille échantillonnée.
  - Phase B (combine, instantanée)   : pondération 100 % locale → les
    sliders réagissent en temps réel, même en mode GEE.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

from engine.analyzer import (
    HydraAnalyzer, POIDS_DEFAUT, NOMS_FACTEURS, verdict,
)

# ════════════════════════════════════════════════════════════════════
# CONFIGURATION DE LA PAGE
# ════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="HYDRA — Analyse hydrogéologique",
    page_icon="💧",
    layout="wide",
)

st.title("💧 HYDRA — Analyse hydrogéologique par satellite")
st.caption(
    "Trouver l'eau avant de forer · **Sprint 3 — moteur GEE complet** "
    "(6 facteurs réels, extraction des candidats sur grille)"
)

# ════════════════════════════════════════════════════════════════════
# PHASE A (cachée) — création de l'analyseur + calcul des couches
# Ne se relance QUE si (lat, lon, rayon, mode) changent.
# ════════════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner="Calcul des couches satellitaires… "
                                "(1 à 3 min en mode GEE)")
def charger_analyseur(lat: float, lon: float, rayon: int,
                      mode: str) -> HydraAnalyzer:
    analyzer = HydraAnalyzer(lat=lat, lon=lon, rayon=rayon, mode=mode)
    analyzer.compute_layers()
    return analyzer

# ════════════════════════════════════════════════════════════════════
# BARRE LATÉRALE — formulaire d'entrée
# ════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ Moteur d'analyse")
    mode = st.radio(
        "Source des données",
        options=["mock", "gee"],
        format_func=lambda m: {
            "mock": "🎭 Démo (données fictives)",
            "gee": "🛰️ GEE réel — 6 facteurs (Sprint 3)",
        }[m],
        help=(
            "Démo : aucune connexion requise. "
            "GEE réel : calcule les 6 couches sur Google Earth Engine "
            "— nécessite l'authentification (python test_gee.py)."
        ),
    )

    st.divider()
    st.header("📍 Zone d'analyse")

    lat = st.number_input(
        "Latitude", min_value=-90.0, max_value=90.0,
        value=11.255046, format="%.6f",
        help="Latitude du centre de la zone (degrés décimaux).",
    )
    lon = st.number_input(
        "Longitude", min_value=-180.0, max_value=180.0,
        value=-12.281277, format="%.6f",
        help="Longitude du centre (négative à l'ouest de Greenwich).",
    )
    rayon = st.select_slider(
        "Rayon d'analyse (m)",
        options=[500, 1000, 1500, 2000, 3000, 5000],
        value=1000,
    )

    st.divider()
    st.header("⚖️ Pondération des facteurs")
    st.caption("La somme doit faire 100 %. Ajustez selon le contexte géologique.")

    poids_pct = {}
    for code, defaut in POIDS_DEFAUT.items():
        poids_pct[code] = st.slider(
            f"{code} — {NOMS_FACTEURS[code]}",
            min_value=0, max_value=60,
            value=int(round(defaut * 100)),
            step=1,
        )

    total_pct = sum(poids_pct.values())
    if total_pct == 100:
        st.success(f"Total : {total_pct} % ✓")
    else:
        st.error(f"Total : {total_pct} % — ajustez pour atteindre 100 %")

    st.divider()
    lancer = st.button("🔍 Lancer l'analyse", type="primary",
                       use_container_width=True,
                       disabled=(total_pct != 100))

# ════════════════════════════════════════════════════════════════════
# CORPS PRINCIPAL
# ════════════════════════════════════════════════════════════════════
if "analyse_faite" not in st.session_state:
    st.session_state.analyse_faite = False

if lancer:
    st.session_state.analyse_faite = True
    # Nouvelle analyse → on oublie l'overlay précédent
    st.session_state.pop("overlay_url", None)
    st.session_state.pop("overlay_label", None)

if not st.session_state.analyse_faite:
    st.info(
        "👈 Renseignez les coordonnées et le rayon dans la barre latérale, "
        "puis cliquez sur **Lancer l'analyse**.\n\n"
        "Les coordonnées par défaut correspondent au cas d'étude "
        "**Donghol Dayebhé** (Labé, Guinée)."
    )
    st.stop()

# ── Phase A (cachée) puis Phase B (instantanée) ─────────────────────
try:
    analyzer = charger_analyseur(lat, lon, rayon, mode)
except Exception as e:
    st.error(
        f"❌ Erreur lors du calcul des couches : `{e}`\n\n"
        "Si vous êtes en mode **GEE réel**, vérifiez l'authentification "
        "Earth Engine : lancez d'abord `python test_gee.py`. "
        "En attendant, le mode **Démo** fonctionne sans connexion."
    )
    st.stop()

poids = {code: v / 100 for code, v in poids_pct.items()}
candidats = analyzer.combine(poids)

# ── Bandeau d'avertissement score relatif ────────────────────────────
st.warning(
    "⚠️ **Les scores sont RELATIFS à la zone analysée** — ils classent les "
    "points entre eux mais ne sont pas une probabilité absolue de trouver "
    "de l'eau. Consultez aussi les indicateurs absolus (NDVI, pente, "
    "distance rivière) et confirmez toujours par un SEV avant de forer."
)

col_carte, col_resultats = st.columns([3, 2], gap="medium")

# ════════════════════════════════════════════════════════════════════
# COLONNE GAUCHE — Carte interactive + gestion des overlays
# ════════════════════════════════════════════════════════════════════
with col_carte:
    st.subheader("🗺️ Carte des candidats")

    # ── Choix de l'overlay (mode GEE uniquement) ────────────────────
    if analyzer.mode == "gee":
        c_sel, c_btn = st.columns([3, 1], vertical_alignment="bottom")
        with c_sel:
            choix_overlay = st.selectbox(
                "Couche à superposer",
                options=["aucune", "score", "C1", "C2", "C3",
                         "C4", "C5", "C6"],
                format_func=lambda c: {
                    "aucune": "Aucune (fond satellite seul)",
                    "score": "⭐ Score final pondéré",
                    **{k: f"{k} — {NOMS_FACTEURS[k]}"
                       for k in NOMS_FACTEURS},
                }[c],
            )
        with c_btn:
            generer = st.button("🔄 Afficher", use_container_width=True)

        if generer:
            with st.spinner("Génération des tuiles…"):
                if choix_overlay == "aucune":
                    st.session_state.pop("overlay_url", None)
                    st.session_state.pop("overlay_label", None)
                elif choix_overlay == "score":
                    st.session_state["overlay_url"] = \
                        analyzer.tile_url_score(poids)
                    st.session_state["overlay_label"] = \
                        "Score final pondéré"
                else:
                    st.session_state["overlay_url"] = \
                        analyzer.tile_url(choix_overlay)
                    st.session_state["overlay_label"] = (
                        f"{choix_overlay} — "
                        f"{NOMS_FACTEURS[choix_overlay]}"
                    )
        st.caption(
            "💡 L'overlay *Score final* est figé avec les poids du moment "
            "où vous cliquez — re-cliquez après avoir bougé les sliders."
        )

    # ── Construction de la carte ────────────────────────────────────
    carte = folium.Map(
        location=[lat, lon],
        zoom_start=14,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/"
              "World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
    )

    folium.Circle(
        location=[lat, lon], radius=rayon,
        color="white", weight=2, fill=False,
        dash_array="6", tooltip=f"Zone d'analyse — rayon {rayon} m",
    ).add_to(carte)

    url_overlay = st.session_state.get("overlay_url")
    if url_overlay:
        folium.TileLayer(
            tiles=url_overlay,
            attr="Google Earth Engine",
            name=st.session_state.get("overlay_label", "Couche HYDRA"),
            overlay=True,
            opacity=0.65,
        ).add_to(carte)
        folium.LayerControl(collapsed=False).add_to(carte)

    folium.Marker(
        [lat, lon],
        tooltip="Centre de la zone",
        icon=folium.Icon(color="red", icon="screenshot", prefix="glyphicon"),
    ).add_to(carte)

    couleurs = ["green", "blue", "purple", "orange", "cadetblue"]
    for cand in candidats:
        coul = couleurs[(cand["rang"] - 1) % len(couleurs)]
        folium.Marker(
            [cand["lat"], cand["lon"]],
            tooltip=(
                f"Candidat {cand['rang']} — score {cand['score']:.3f} "
                f"({verdict(cand['score'])})"
            ),
            popup=folium.Popup(
                f"<b>Candidat {cand['rang']}</b><br>"
                f"Score : {cand['score']:.3f}<br>"
                f"Lat : {cand['lat']:.6f}<br>"
                f"Lon : {cand['lon']:.6f}<br>"
                f"Altitude : {cand['altitude_m']} m<br>"
                f"NDVI : {cand['ndvi']}<br>"
                f"Distance centre : {cand['distance_centre_m']} m",
                max_width=250,
            ),
            icon=folium.Icon(color=coul, icon="star", prefix="glyphicon"),
        ).add_to(carte)

    st_folium(carte, height=520, use_container_width=True)

    if url_overlay:
        st.caption(
            "Palette : 🔵 sombre = défavorable → 🟢 vert → 🟡 jaune → "
            "🔴 rouge = très favorable. L'eau de surface est exclue (masquée)."
        )

# ════════════════════════════════════════════════════════════════════
# COLONNE DROITE — Tableau des résultats
# ════════════════════════════════════════════════════════════════════
with col_resultats:
    st.subheader("🎯 Top candidats")

    if analyzer.mode == "gee":
        st.info(
            f"📡 **6 facteurs réels GEE** — candidats extraits d'une "
            f"grille de **{analyzer.nb_points_grille} points** "
            f"échantillonnés sur la zone (eau exclue)."
        )
    else:
        st.info("🎭 Mode démo — données fictives (cas Donghol Dayebhé).")

    df = pd.DataFrame([
        {
            "Rang": c["rang"],
            "Score": c["score"],
            "Verdict": verdict(c["score"]),
            "Latitude": round(c["lat"], 6),
            "Longitude": round(c["lon"], 6),
            "Altitude (m)": c["altitude_m"],
            "NDVI": c["ndvi"],
            "Pente (°)": c["pente_deg"],
            "Dist. rivière (m)": c["dist_riviere_m"],
            "Dist. centre (m)": c["distance_centre_m"],
        }
        for c in candidats
    ])
    st.dataframe(df, hide_index=True, use_container_width=True)

    meilleur = candidats[0]
    with st.expander(
        f"🔬 Détail des facteurs — Candidat {meilleur['rang']} "
        f"(score {meilleur['score']:.3f})",
        expanded=True,
    ):
        detail = pd.DataFrame([
            {
                "Facteur": f"{code} — {NOMS_FACTEURS[code]}",
                "Sous-score": meilleur["scores"][code],
                "Poids": f"{poids_pct[code]} %",
                "Contribution": round(
                    meilleur["scores"][code] * poids[code], 4
                ),
            }
            for code in POIDS_DEFAUT
        ])
        st.dataframe(detail, hide_index=True, use_container_width=True)

    st.caption(
        "💡 Bougez les sliders : le classement se met à jour "
        "instantanément — la grille de points est déjà en mémoire locale "
        "(architecture 2 phases)."
    )

    # ════════════════════════════════════════════════════════════════
    # EXPORT — Rapport PDF + Excel (Sprint 5)
    # ════════════════════════════════════════════════════════════════
    st.divider()
    st.subheader("📄 Export")

    c_opt1, c_opt2 = st.columns(2)
    with c_opt1:
        type_rapport = st.radio(
            "Type de rapport",
            options=["client", "expert"],
            format_func=lambda t: {
                "client": "👤 Client (confidentiel)",
                "expert": "🔧 Expert (interne complet)",
            }[t],
            help="Client : masque pondération, méthodologie et sous-scores. "
                 "Expert : tout visible (usage interne HYDRA).",
        )
    with c_opt2:
        style_plan = st.radio(
            "Plan de situation",
            options=["schema", "satellite"],
            format_func=lambda s: {
                "schema": "📐 Schématique",
                "satellite": "🛰️ Sur image satellite",
            }[s],
            help="Schématique : plan épuré (toujours dispo). "
                 "Satellite : candidats sur vraie image (mode GEE).",
        )

    if style_plan == "satellite" and analyzer.mode != "gee":
        st.caption("ℹ️ Le plan satellite nécessite le mode GEE réel — "
                   "le plan schématique sera utilisé.")

    if st.button("🧾 Générer le rapport", use_container_width=True):
        with st.spinner("Génération du rapport et de l'export Excel…"):
            from engine.export.map_generator import (
                plan_situation, plan_sur_satellite, thumbnail_score,
            )
            from engine.export.pdf_generator import generer_pdf
            from engine.export.excel_export import generer_excel

            meta = {
                "lat": lat, "lon": lon, "rayon": rayon,
                "mode": analyzer.mode,
                "nb_points": (analyzer.nb_points_grille
                              if analyzer.mode == "gee" else "démo"),
            }

            # Choix du plan
            plan_png = None
            if style_plan == "satellite":
                plan_png = plan_sur_satellite(
                    analyzer, candidats, lat, lon, rayon
                )
            if plan_png is None:   # fallback schématique
                plan_png = plan_situation(candidats, lat, lon, rayon)

            # Miniature score (seulement si plan schématique, pour éviter
            # deux images satellite redondantes)
            carte_png = None
            if style_plan == "schema":
                carte_png = thumbnail_score(analyzer, poids)

            st.session_state["pdf_bytes"] = generer_pdf(
                candidats, meta, poids, plan_png, carte_png,
                confidentiel=type_rapport,
            )
            st.session_state["xlsx_bytes"] = generer_excel(
                candidats, meta, poids, confidentiel=type_rapport,
            )
            st.session_state["export_type"] = type_rapport
        st.success("Rapport prêt — téléchargez ci-dessous.")

    if "pdf_bytes" in st.session_state:
        suffixe = st.session_state.get("export_type", "client")
        horodatage = f"{lat:.4f}_{lon:.4f}".replace(".", "p")
        c_pdf, c_xls = st.columns(2)
        with c_pdf:
            st.download_button(
                "⬇️ Rapport PDF",
                data=st.session_state["pdf_bytes"],
                file_name=f"HYDRA_rapport_{suffixe}_{horodatage}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with c_xls:
            st.download_button(
                "⬇️ Candidats Excel",
                data=st.session_state["xlsx_bytes"],
                file_name=f"HYDRA_candidats_{suffixe}_{horodatage}.xlsx",
                mime="application/vnd.openxmlformats-officedocument."
                     "spreadsheetml.sheet",
                use_container_width=True,
            )
        st.caption(
            f"Rapport **{suffixe}** figé avec les poids du moment de la "
            "génération — re-générez après modification des sliders."
        )
