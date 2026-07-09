"""
KPIs calculés :
  - reach            : nb de personnes uniques touchées (sessions liées à la campagne)
  - sessions         : nb total de sessions générées par la campagne
  - ctr               : taux de clic = clics / impressions
  - taux_conversion   : conversions / clics
  - conversions       : nb de sessions ayant abouti à une conversion
  - revenu_genere     : somme des valeurs de conversion
  - cpc               : coût par clic = budget / clics
  - cpa               : coût par acquisition = budget / conversions
  - roi               : (revenu_genere - budget) / budget
"""

import sys
from datetime import datetime

sys.path.append("/opt/airflow/etl")
sys.path.append(".")

import numpy as np
import pandas as pd
from minio_utils import ensure_bucket, read_parquet_from_minio, upload_dataframe_parquet


def run(run_date: str = None):
    run_date = run_date or datetime.now().strftime("%Y-%m-%d")
    ensure_bucket()

    ads = read_parquet_from_minio(f"silver/{run_date}/publicite_clean.parquet")
    sessions = read_parquet_from_minio(f"silver/{run_date}/sessions_enriched.parquet")

    sessions_ads = sessions[sessions["campaign_id"] != "ORGANIQUE"]

    agg = sessions_ads.groupby("campaign_id").agg(
        sessions=("session_id", "count"),
        reach=("user_id", "nunique"),
        conversions=("converted", "sum"),
        revenu_genere=("valeur_conversion", "sum"),
        duree_moyenne_visite_sec=("duree_visite_sec", "mean"),
    ).reset_index()

    kpis = ads.merge(agg, how="left", on="campaign_id")
    for col in ["sessions", "reach", "conversions", "revenu_genere", "duree_moyenne_visite_sec"]:
        kpis[col] = kpis[col].fillna(0)

    kpis["ctr"] = (kpis["clics"] / kpis["impressions"]).round(4)
    kpis["taux_conversion"] = np.where(kpis["clics"] > 0, kpis["conversions"] / kpis["clics"], 0).round(4)
    kpis["cpc"] = np.where(kpis["clics"] > 0, kpis["budget_alloue"] / kpis["clics"], np.nan).round(2)
    kpis["cpa"] = np.where(kpis["conversions"] > 0, kpis["budget_alloue"] / kpis["conversions"], np.nan).round(2)
    kpis["roi"] = np.where(
        kpis["budget_alloue"] > 0,
        (kpis["revenu_genere"] - kpis["budget_alloue"]) / kpis["budget_alloue"],
        np.nan,
    ).round(3)

    resume_global = pd.DataFrame([{
        "date_calcul": run_date,
        "budget_total": kpis["budget_alloue"].sum(),
        "impressions_totales": kpis["impressions"].sum(),
        "clics_totaux": kpis["clics"].sum(),
        "conversions_totales": kpis["conversions"].sum(),
        "revenu_total": kpis["revenu_genere"].sum(),
        "ctr_moyen": kpis["ctr"].mean().round(4),
        "taux_conversion_moyen": kpis["taux_conversion"].mean().round(4),
        "roi_moyen": kpis["roi"].mean().round(3),
    }])

    upload_dataframe_parquet(kpis, key=f"gold/{run_date}/kpis_campagnes.parquet")
    upload_dataframe_parquet(resume_global, key=f"gold/{run_date}/resume_global.parquet")
    upload_dataframe_parquet(kpis, key="gold/latest/kpis_campagnes.parquet")
    upload_dataframe_parquet(resume_global, key="gold/latest/resume_global.parquet")

    print(f"Agrégation gold terminée pour la date {run_date}")
    print(kpis[["campaign_id", "plateforme", "ctr", "taux_conversion", "cpa", "roi"]])


if __name__ == "__main__":
    run()
