import sys
from datetime import datetime

sys.path.append("/opt/airflow/etl")
sys.path.append(".")

import pandas as pd
from minio_utils import ensure_bucket, read_csv_from_minio, upload_dataframe_parquet


def clean_crm(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset="client_id").copy()
    df["email"] = df["email"].str.lower().str.strip()
    df["nom"] = df["nom"].str.strip().str.title()
    df["prenom"] = df["prenom"].str.strip().str.title()
    df["date_inscription"] = pd.to_datetime(df["date_inscription"], errors="coerce")
    return df


def clean_ads(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset="campaign_id").copy()
    df["date_diffusion"] = pd.to_datetime(df["date_diffusion"], errors="coerce")
    df["clics"] = df[["clics", "impressions"]].min(axis=1)
    df = df[(df["budget_alloue"] > 0) & (df["impressions"] > 0)]
    return df


def clean_web_logs(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset="session_id").copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df["duree_visite_sec"] = df["duree_visite_sec"].clip(lower=0)
    df["converted"] = df["converted"].astype(bool)
    df["campaign_id"] = df["campaign_id"].fillna("ORGANIQUE")
    return df


def run(run_date: str = None):
    run_date = run_date or datetime.now().strftime("%Y-%m-%d")
    ensure_bucket()

    crm_raw = read_csv_from_minio(f"bronze/{run_date}/crm.csv")
    ads_raw = read_csv_from_minio(f"bronze/{run_date}/publicite.csv")
    web_raw = read_csv_from_minio(f"bronze/{run_date}/web_logs.csv")

    crm = clean_crm(crm_raw)
    ads = clean_ads(ads_raw)
    web = clean_web_logs(web_raw)

    sessions_enriched = (
        web.merge(crm, how="left", left_on="user_id", right_on="client_id", suffixes=("", "_crm"))
           .merge(ads, how="left", on="campaign_id", suffixes=("", "_ads"))
    )
    sessions_enriched["est_client_identifie"] = sessions_enriched["client_id"].notna()

    upload_dataframe_parquet(crm, key=f"silver/{run_date}/crm_clean.parquet")
    upload_dataframe_parquet(ads, key=f"silver/{run_date}/publicite_clean.parquet")
    upload_dataframe_parquet(web, key=f"silver/{run_date}/web_logs_clean.parquet")
    upload_dataframe_parquet(sessions_enriched, key=f"silver/{run_date}/sessions_enriched.parquet")

    print(f"Transformation silver terminée pour la date {run_date}")
    print(f"   - {len(crm)} clients, {len(ads)} campagnes, {len(web)} sessions nettoyées")


if __name__ == "__main__":
    run()
