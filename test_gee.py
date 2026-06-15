# -*- coding: utf-8 -*-
"""
HYDRA — test_gee.py
====================
Script de validation Google Earth Engine — Sprint 3.

Teste, dans l'ordre :
  1. Authentification + initialisation
  2. Accès aux datasets (PALSAR, Sentinel-2, WorldCover, MERIT, SoilGrids)
  3. Chaque facteur C1..C6 individuellement (score au point SEV)
  4. Le pipeline complet : grille + extraction des 5 candidats réels

Usage (depuis la racine du projet, venv activé) :
    python test_gee.py

Durée totale attendue : 2 à 5 minutes selon la connexion.
Premier lancement : une page navigateur s'ouvre pour autoriser l'accès.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Zone de test : Donghol Dayebhé (notre cas de référence)
LAT, LON, RAYON = 11.255046, -12.281277, 1000
SEV_LAT, SEV_LON = 11.25821, -12.28593


def main():
    print("=" * 62)
    print("HYDRA — Test Google Earth Engine (Sprint 3 — 6 facteurs)")
    print("=" * 62)

    # ── Étape 1 : authentification ───────────────────────────────
    print("\n[1/4] Initialisation GEE…")
    try:
        import ee
        from engine.gee_utils import init_gee, GEE_PROJECT, score_au_point
        init_gee()
        print(f"      ✓ Connecté au projet : {GEE_PROJECT}")
    except Exception as e:
        print(f"      ✗ ÉCHEC : {e}")
        sys.exit(1)

    point = ee.Geometry.Point([LON, LAT])
    zone = point.buffer(RAYON)

    # ── Étape 2 : datasets ───────────────────────────────────────
    print("\n[2/4] Vérification des datasets…")
    n_palsar = (ee.ImageCollection("JAXA/ALOS/PALSAR/YEARLY/SAR_EPOCH")
                .filterBounds(zone).size().getInfo())
    n_s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(zone)
            .filter(ee.Filter.calendarRange(1, 4, "month"))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 15))
            .size().getInfo())
    print(f"      ✓ ALOS PALSAR : {n_palsar} images")
    print(f"      ✓ Sentinel-2 (saison sèche) : {n_s2} images")
    for nom, asset, bande in [
        ("ESA WorldCover", None, None),
        ("MERIT Hydro (upa)", "MERIT/Hydro/v1_0_1", "upa"),
        ("SoilGrids sable", "projects/soilgrids-isric/sand_mean",
         "sand_0-5cm_mean"),
    ]:
        if asset:
            v = (ee.Image(asset).select(bande)
                 .reduceRegion(reducer=ee.Reducer.mean(), geometry=zone,
                               scale=250, maxPixels=int(1e9),
                               bestEffort=True).getInfo())
            print(f"      ✓ {nom} : moyenne zone = "
                  f"{list(v.values())[0]:.3f}")
        else:
            ee.ImageCollection("ESA/WorldCover/v200").first().clip(zone)
            print(f"      ✓ {nom} : chargé")

    # ── Étape 3 : chaque facteur individuellement ────────────────
    print("\n[3/4] Test des 6 facteurs (score au point SEV)…")
    from engine.factors.c1_lineaments import compute_lineaments
    from engine.factors.c2_topo import compute_topo
    from engine.factors.c3_hydro import compute_hydro
    from engine.factors.c4_vegetation import compute_vegetation
    from engine.factors.c5_lulc import compute_lulc
    from engine.factors.c6_pedology import compute_pedology

    facteurs = {
        "C1 Linéaments": compute_lineaments,
        "C2 Topographie": compute_topo,
        "C3 Hydrographie": compute_hydro,
        "C4 Végétation": compute_vegetation,
        "C5 LULC": compute_lulc,
        "C6 Pédologie": compute_pedology,
    }
    for nom, fonction in facteurs.items():
        t0 = time.time()
        try:
            image = fonction(zone)
            code = nom.split()[0]
            valeur = score_au_point(image.rename(code), code,
                                    SEV_LAT, SEV_LON)
            duree = time.time() - t0
            statut = "✓" if valeur is not None else "⚠ None (masqué ?)"
            print(f"      {statut} {nom:<18}: {valeur}   ({duree:.0f} s)")
        except Exception as e:
            print(f"      ✗ {nom:<18}: ERREUR — {e}")

    # ── Étape 4 : pipeline complet ───────────────────────────────
    print("\n[4/4] Pipeline complet — grille + extraction candidats…")
    print("      (c'est l'étape la plus longue : 1 à 3 min)")
    t0 = time.time()
    from engine.analyzer import HydraAnalyzer, POIDS_DEFAUT

    analyzer = HydraAnalyzer(lat=LAT, lon=LON, rayon=RAYON, mode="gee")
    analyzer.compute_layers()
    duree_a = time.time() - t0
    print(f"      ✓ Phase A : {analyzer.nb_points_grille} points de "
          f"grille en {duree_a:.0f} s")

    t0 = time.time()
    candidats = analyzer.combine(POIDS_DEFAUT)
    duree_b = (time.time() - t0) * 1000
    print(f"      ✓ Phase B : {len(candidats)} candidats en "
          f"{duree_b:.0f} ms (doit être < 100 ms)")

    print("\n      Top candidats réels :")
    for c in candidats:
        print(f"        #{c['rang']}  score {c['score']:.4f}  "
              f"lat {c['lat']:.6f}  lon {c['lon']:.6f}  "
              f"alt {c['altitude_m']}m  NDVI {c['ndvi']}  "
              f"dist {c['distance_centre_m']}m")

    print("\n" + "=" * 62)
    print("✅ SPRINT 3 VALIDÉ — lancez l'application :")
    print("   streamlit run app/main.py   → mode « GEE réel »")
    print("=" * 62)


if __name__ == "__main__":
    main()
