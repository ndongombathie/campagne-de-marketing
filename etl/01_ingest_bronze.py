import sys
from datetime import datetime

sys.path.append("/opt/airflow/etl")  # pour Airflow (voir dags/)
sys.path.append(".")

import pandas as pd
from minio_utils import ensure_bucket, upload_dataframe_csv


def run(run_date: str = None, source_dir: str = "/opt/airflow/data_generator/output"):
    run_date = run_date or datetime.now().strftime("%Y-%m-%d")
    ensure_bucket()

    for name in ["crm", "publicite", "web_logs"]:
        df = pd.read_csv(f"{source_dir}/{name}.csv")
        upload_dataframe_csv(df, key=f"bronze/{run_date}/{name}.csv")

    print(f"Ingestion bronze terminée pour la date {run_date}")


if __name__ == "__main__":
    run()
