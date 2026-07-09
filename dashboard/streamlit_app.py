"""
Dashboard Streamlit - Performance des campagnes marketing

Lit les données agrégées (zone gold) depuis MinIO et affiche :
  - une vue d'ensemble (KPIs globaux)
  - le détail par campagne / plateforme
  - des graphiques d'aide à la décision (ROI, CPA, CTR, budget vs revenu)
"""

import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "etl"))
from minio_utils import read_parquet_from_minio  # noqa: E402

st.set_page_config(page_title="Performance Campagnes Marketing", layout="wide")

st.title("Dashboard — Performance des campagnes marketing")
st.caption("Données issues du pipeline ETL (bronze → silver → gold) orchestré par Airflow")


@st.cache_data(ttl=300)
def load_gold_data():
    kpis = read_parquet_from_minio("gold/latest/kpis_campagnes.parquet")
    resume = read_parquet_from_minio("gold/latest/resume_global.parquet")
    return kpis, resume


try:
    kpis, resume = load_gold_data()
except Exception as e:
    st.error(
        "Impossible de charger les données depuis MinIO. "
        "Vérifie que le pipeline Airflow a bien été exécuté au moins une fois.\n\n"
        f"Détail technique : {e}"
    )
    st.stop()

# ---------- Filtres ----------
plateformes = ["Toutes"] + sorted(kpis["plateforme"].unique().tolist())
plateforme_choisie = st.sidebar.selectbox("Filtrer par plateforme", plateformes)

df = kpis if plateforme_choisie == "Toutes" else kpis[kpis["plateforme"] == plateforme_choisie]

# ---------- KPIs globaux ----------
st.subheader("Vue d'ensemble")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Budget total", f"{df['budget_alloue'].sum():,.0f} €")
c2.metric("Impressions", f"{df['impressions'].sum():,.0f}")
c3.metric("Clics", f"{df['clics'].sum():,.0f}")
c4.metric("Conversions", f"{int(df['conversions'].sum()):,}")
roi_moyen = df["roi"].mean()
c5.metric("ROI moyen", f"{roi_moyen:.1%}" if pd.notna(roi_moyen) else "N/A")

st.divider()

# ---------- Graphiques ----------
col1, col2 = st.columns(2)

with col1:
    st.markdown("**ROI par campagne**")
    fig_roi = px.bar(
        df.sort_values("roi", ascending=False),
        x="campaign_id", y="roi", color="plateforme",
        labels={"roi": "ROI", "campaign_id": "Campagne"},
    )
    fig_roi.add_hline(y=0, line_dash="dash", line_color="red")
    st.plotly_chart(fig_roi, use_container_width=True)

with col2:
    st.markdown("**Coût par acquisition (CPA) par campagne**")
    fig_cpa = px.bar(
        df.sort_values("cpa"),
        x="campaign_id", y="cpa", color="plateforme",
        labels={"cpa": "CPA (€)", "campaign_id": "Campagne"},
    )
    st.plotly_chart(fig_cpa, use_container_width=True)

col3, col4 = st.columns(2)

with col3:
    st.markdown("**Taux de conversion vs CTR**")
    fig_scatter = px.scatter(
        df, x="ctr", y="taux_conversion", size="budget_alloue", color="plateforme",
        hover_name="campaign_id",
        labels={"ctr": "CTR (taux de clic)", "taux_conversion": "Taux de conversion"},
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with col4:
    st.markdown("**Budget alloué vs revenu généré**")
    df_melt = df.melt(
        id_vars="campaign_id", value_vars=["budget_alloue", "revenu_genere"],
        var_name="type", value_name="montant",
    )
    fig_budget = px.bar(
        df_melt, x="campaign_id", y="montant", color="type", barmode="group",
        labels={"montant": "Montant (€)", "campaign_id": "Campagne"},
    )
    st.plotly_chart(fig_budget, use_container_width=True)

st.divider()

# ---------- Répartition par plateforme ----------
st.markdown("**Répartition du budget par plateforme**")
fig_pie = px.pie(df, names="plateforme", values="budget_alloue", hole=0.4)
st.plotly_chart(fig_pie, use_container_width=True)

# ---------- Tableau détaillé ----------
st.subheader("Détail par campagne")
colonnes_affichees = [
    "campaign_id", "nom_campagne", "plateforme", "date_diffusion", "budget_alloue",
    "impressions", "clics", "ctr", "reach", "conversions", "taux_conversion",
    "cpc", "cpa", "revenu_genere", "roi",
]
st.dataframe(df[colonnes_affichees], use_container_width=True)

st.caption("Source : bucket MinIO `marketing-data` — dernière exécution du DAG Airflow `marketing_campaign_etl`")
