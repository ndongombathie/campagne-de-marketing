"""
Le lien entre les 3 tables se fait via :
  - web_logs.user_id      -> crm.client_id   (quand l'utilisateur est identifié)
  - web_logs.campaign_id  -> ads.campaign_id (paramètre UTM de la visite)
"""

import argparse
import random
import uuid
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker("fr_FR")
Faker.seed(42)
random.seed(42)
np.random.seed(42)

PLATEFORMES = ["Google", "Facebook", "LinkedIn", "Instagram", "TikTok","YouTube","twitter"]
PAGES = [
    "/accueil", "/produits", "/produit/detail", "/panier", "/checkout",
    "/confirmation-commande", "/blog", "/contact", "/a-propos", "/promo",
]

CAMPAGNE = [
    "Promo Ramadan",
    "Soldes Été",
    "Back to School",
    "Black Friday",
    "Promo de noel",
    "Nouvelle Collection",
    "Fête de Tabaski",
    "Promo Magal touba",
    "Promo Gamou",
    "Fête de Koritè"
]

DEVICES = ["mobile", "desktop", "tablette"]
SEGMENTS = ["prospect", "client_actif", "client_inactif", "vip"]
STATUTS_INTERACTION = [
    "email ouvert", "email cliqué", "appel commercial", "demande de devis",
    "réclamation", "aucune interaction récente",
]


def generate_campaigns(n_campaigns: int, start_date: datetime, days_span: int) -> pd.DataFrame:
    rows = []
    for i in range(1, n_campaigns + 1):
        campaign_id = f"CMP{i:04d}"
        plateforme = random.choice(PLATEFORMES)
        date_diffusion = start_date + timedelta(days=random.randint(0, days_span))
        budget_alloue = round(random.uniform(200, 5000), 2)
        impressions = random.randint(2000, 200000)
        # le CTR "réel" varie selon la plateforme pour rendre les données réalistes
        ctr_base = {"Google": 0.04, "Facebook": 0.02, "LinkedIn": 0.015,
                    "Instagram": 0.025, "TikTok": 0.03,"YouTube": 0.02,"twitter": 0.035}[plateforme]
        clics = int(impressions * max(0.001, np.random.normal(ctr_base, ctr_base * 0.3)))
        clics = max(clics, 1)
        rows.append({
            "campaign_id": campaign_id,
            "nom_campagne": random.choice(CAMPAGNE),
            "plateforme": plateforme,
            "date_diffusion": date_diffusion.date().isoformat(),
            "budget_alloue": budget_alloue,
            "devise": "CFA",
            "impressions": impressions,
            "clics": clics
        })
    return pd.DataFrame(rows)


def generate_crm(n_clients: int) -> pd.DataFrame:
    rows = []
    for i in range(1, n_clients + 1):
        client_id = f"CLI{i:05d}"
        prenom = fake.first_name()
        nom = fake.last_name()
        rows.append({
            "client_id": client_id,
            "prenom": prenom,
            "nom": nom,
            "email": f"{prenom.lower()}.{nom.lower()}{random.randint(1,999)}@{fake.free_email_domain()}",
            "telephone": fake.phone_number(),
            "ville": fake.city(),
            "date_inscription": fake.date_between(start_date="-3y", end_date="today").isoformat(),
            "historique_interactions": random.choice(STATUTS_INTERACTION),
        })
    return pd.DataFrame(rows)


def generate_web_logs(n_sessions: int, crm_df: pd.DataFrame, ads_df: pd.DataFrame,
                       start_date: datetime, days_span: int) -> pd.DataFrame:
    client_ids = crm_df["client_id"].tolist()
    campaign_ids = ads_df["campaign_id"].tolist()

    rows = []
    for _ in range(n_sessions):
        session_id = str(uuid.uuid4())
        visit_dt = start_date + timedelta(
            days=random.randint(0, days_span),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
       
        campaign_id = random.choice(campaign_ids) if random.random() < 0.6 else None
        
        user_id = random.choice(client_ids) if random.random() < 0.55 else f"ANON{uuid.uuid4().hex[:8]}"
        
        page =f"www.jumia{random.choice(PAGES)}.com"
        duree_visite = max(1, int(np.random.exponential(scale=90)))  # secondes
        # une conversion (achat) est plus probable si la page = checkout/confirmation
        converted = page == "www.jumia/confirmation-commande.com" or (page == "www.jumia/checkout.com" and random.random() < 0.3)
        valeur_conversion = round(random.uniform(15, 300), 2) if converted else 0.0

        rows.append({
            "session_id": session_id,
            "timestamp": visit_dt.isoformat(),
            "user_id": user_id,
            "page_visitee": page,
            "duree_visite_sec": duree_visite,
            "device": random.choice(DEVICES),
            "campaign_id": campaign_id,
            "converted": converted,
            "valeur_conversion": valeur_conversion,
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Génère les 3 jeux de données fictifs du projet.")
    parser.add_argument("--n-clients", type=int, default=500)
    parser.add_argument("--n-sessions", type=int, default=5000)
    parser.add_argument("--n-campaigns", type=int, default=15)
    parser.add_argument("--days-span", type=int, default=60, help="fenêtre temporelle en jours")
    parser.add_argument("--out-dir", type=str, default=".")
    args = parser.parse_args()

    start_date = datetime.now() - timedelta(days=args.days_span)

    crm_df = generate_crm(args.n_clients)
    ads_df = generate_campaigns(args.n_campaigns, start_date, args.days_span)
    web_df = generate_web_logs(args.n_sessions, crm_df, ads_df, start_date, args.days_span)

    crm_df.to_csv(f"{args.out_dir}/crm.csv", index=False)
    ads_df.to_csv(f"{args.out_dir}/publicite.csv", index=False)
    web_df.to_csv(f"{args.out_dir}/web_logs.csv", index=False)


if __name__ == "__main__":
    main()
