import io
import os

import boto3
import pandas as pd
from botocore.client import Config

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "password")
BUCKET_NAME = os.environ.get("MINIO_BUCKET", "marketing-data")


def get_client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket():
    client = get_client()
    existing = [b["Name"] for b in client.list_buckets().get("Buckets", [])]
    if BUCKET_NAME not in existing:
        client.create_bucket(Bucket=BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' créé.")


def upload_dataframe_csv(df: pd.DataFrame, key: str):
    """Écrit un DataFrame en CSV directement sur MinIO."""
    client = get_client()
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    client.put_object(Bucket=BUCKET_NAME, Key=key, Body=buf.getvalue())
    print(f"Uploadé -> s3://{BUCKET_NAME}/{key} ({len(df)} lignes)")


def upload_dataframe_parquet(df: pd.DataFrame, key: str):
    """Écrit un DataFrame en Parquet directement sur MinIO."""
    client = get_client()
    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow")
    buf.seek(0)
    client.put_object(Bucket=BUCKET_NAME, Key=key, Body=buf.getvalue())
    print(f"Uploadé -> s3://{BUCKET_NAME}/{key} ({len(df)} lignes)")


def read_csv_from_minio(key: str) -> pd.DataFrame:
    client = get_client()
    obj = client.get_object(Bucket=BUCKET_NAME, Key=key)
    return pd.read_csv(io.BytesIO(obj["Body"].read()))


def read_parquet_from_minio(key: str) -> pd.DataFrame:
    client = get_client()
    obj = client.get_object(Bucket=BUCKET_NAME, Key=key)
    return pd.read_parquet(io.BytesIO(obj["Body"].read()), engine="pyarrow")
