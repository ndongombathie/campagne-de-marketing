from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def _generate_data(**context):
    import subprocess
    subprocess.run(
        [
            "python3", "/opt/airflow/data_generator/generate_data.py",
            "--out-dir", "/opt/airflow/data_generator/output",
            "--n-clients", "500", "--n-sessions", "5000", "--n-campaigns", "15",
        ],
        check=True,
    )


def _ingest_bronze(**context):
    import sys
    sys.path.append("/opt/airflow/etl")
    from importlib import import_module
    mod = import_module("01_ingest_bronze")
    mod.run(run_date=context["ds"])


def _transform_silver(**context):
    import sys
    sys.path.append("/opt/airflow/etl")
    from importlib import import_module
    mod = import_module("02_transform_silver")
    mod.run(run_date=context["ds"])


def _aggregate_gold(**context):
    import sys
    sys.path.append("/opt/airflow/etl")
    from importlib import import_module
    mod = import_module("03_aggregate_gold")
    mod.run(run_date=context["ds"])


def _notify_success(**context):
    print(f"Pipeline marketing terminé avec succès pour la date {context['ds']}")


with DAG(
    dag_id="campagne_marketing",
    description="Pipeline ETL : logs web + CRM + ads -> KPIs campagnes marketing",
    default_args=default_args,
    schedule_interval="*/1 * * * *",  
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:

    generate_data = PythonOperator(
        task_id="generate_data",
        python_callable=_generate_data,
    )

    ingest_bronze = PythonOperator(
        task_id="ingest_bronze",
        python_callable=_ingest_bronze,
    )

    transform_silver = PythonOperator(
        task_id="transform_silver",
        python_callable=_transform_silver,
    )

    aggregate_gold = PythonOperator(
        task_id="aggregate_gold",
        python_callable=_aggregate_gold,
    )

    notify_success = PythonOperator(
        task_id="notify_success",
        python_callable=_notify_success,
    )

    generate_data >> ingest_bronze >> transform_silver >> aggregate_gold >> notify_success
