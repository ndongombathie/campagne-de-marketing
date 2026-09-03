# Projet 3 — Campagnes Marketing

Pipeline data engineering complet : ingestion multi-source, ETL, orchestration
Airflow, stockage MinIO (architecture medallion bronze/silver/gold) et
dashboard Streamlit.

## Architecture

```
 ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
 │  CRM (csv)   │   │ Ads (csv)    │   │ Web logs(csv)│   <- data_generator/generate_data.py
 └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
        └──────────────────┼───────────────────┘
                            ▼
                  Airflow DAG (quotidien)
                            ▼
                 ┌────────────────────┐
                 │  MinIO — bronze/   │  CSV bruts, tels quels
                 └─────────┬──────────┘
                            ▼  nettoyage + normalisation + jointure
                 ┌────────────────────┐
                 │  MinIO — silver/   │  Parquet, table "sessions_enriched"
                 └─────────┬──────────┘
                            ▼  calcul des KPIs par campagne
                 ┌────────────────────┐
                 │  MinIO — gold/     │  Parquet, KPIs prêts à consommer
                 └─────────┬──────────┘
                            ▼
                 ┌────────────────────┐
                 │  Streamlit          │  Dashboard interactif
                 └────────────────────┘
```

## Structure du projet

```
marketing-campaigns-project/
├── data_generator/
│   └── generate_data.py       # génère crm.csv, ads.csv, web_logs.csv (Faker)
├── etl/
│   ├── minio_utils.py         # client S3/MinIO partagé
│   ├── 01_ingest_bronze.py    # CSV bruts -> MinIO bronze
│   ├── 02_transform_silver.py # nettoyage + jointure -> MinIO silver
│   └── 03_aggregate_gold.py   # calcul des KPIs -> MinIO gold
├── dags/
│   └── marketing_campaign_dag.py  # DAG Airflow orchestrant les 3 étapes ETL
├── dashboard/
│   └── streamlit_app.py       # dashboard de visualisation
├── docker/
│   └── Dockerfile.streamlit
├── docker-compose.yml         # Airflow + Postgres + MinIO + Streamlit
└── requirements.txt
```

## Modèle de données et clés de jointure

| Table         | Clé primaire   | Clé étrangère                       |
|---------------|----------------|--------------------------------------|
| `crm.csv`     | `client_id`    | —                                    |
| `publicites.csv`     | `campaign_id`  | —                                    |
| `web_logs.csv`| `session_id`   | `user_id` -> crm.client_id (si connu)<br>`campaign_id` -> ads.campaign_id (si trafic payant) |

Environ 55 % des sessions web sont liées à un client CRM identifié, le reste
sont des visiteurs anonymes (réalisme). Environ 60 % des sessions proviennent
d'une campagne publicitaire (UTM), le reste est du trafic organique.

## KPIs calculés (zone gold)

| KPI | Formule | Signification |
|---|---|---|
| CTR | clics / impressions | taux de clic sur la publicité |
| Taux de conversion | conversions / clics | efficacité du tunnel de conversion |
| Reach | nb d'utilisateurs uniques touchés | portée réelle de la campagne |
| CPC | budget / clics | coût par clic |
| CPA | budget / conversions | coût par acquisition d'un client |
| ROI | (revenu généré − budget) / budget | retour sur investissement |

## Lancer le projet

```bash
docker compose up -d --build
```

Puis :
1. **Airflow UI** : http://localhost:8080 (admin/admin) → activer et déclencher le DAG `marketing_campaign_etl`
2. **Console MinIO** : http://localhost:9001 (minioadmin/minioadmin) → vérifier les buckets `bronze/`, `silver/`, `gold/`
3. **Dashboard Streamlit** : http://localhost:8501

## Exécution manuelle (sans Airflow, pour développer/tester)

```bash
pip install -r requirements.txt

# 1. Générer les données
python data_generator/generate_data.py --out-dir data_generator/output

# 2. Lancer le pipeline ETL localement (nécessite MinIO démarré : docker compose up -d minio)
cd etl
python etl/01_ingest_bronze.py
python etl/02_transform_silver.py
python etl/03_aggregate_gold.py

# 3. Lancer le dashboard
streamlit run ../dashboard/streamlit_app.py
```

## Pistes d'amélioration (bonus pour aller plus loin)

- Ajouter du **data quality testing** (Great Expectations) entre silver et gold
- Ajouter un **SCD (slowly changing dimension)** sur la table CRM
- Passer les KPIs gold dans **PostgreSQL** en plus de MinIO pour des requêtes SQL rapides
- Ajouter des **alertes Airflow** (email/Slack) en cas d'échec de tâche
- Ajouter un **DAG de backfill** pour recalculer l'historique
