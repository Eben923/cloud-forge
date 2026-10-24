import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Load local environment variables from .env file if present
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

# 2. AWS SSM Parameter Store Integration (Fallback to local .env if unset or error)
ssm_param_name = os.getenv("SSM_DB_PASSWORD_PARAM")
if ssm_param_name:
    try:
        import boto3
        region = os.getenv("AWS_REGION", "ap-southeast-2")
        ssm = boto3.client("ssm", region_name=region)
        response = ssm.get_parameter(Name=ssm_param_name, WithDecryption=True)
        db_password = response["Parameter"]["Value"]
        db_user = os.getenv("DB_USER", "cloudforge")
        db_host = os.getenv("DB_HOST", "127.0.0.1")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "cloudforge")
        DATABASE_URL = f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    except Exception as exc:
        import logging
        logging.getLogger("cloudforge").error(
            f"Failed to fetch SSM parameter '{ssm_param_name}': {exc}"
        )
        if not DATABASE_URL:
            raise RuntimeError(
                f"Failed to retrieve database credentials from SSM Parameter Store ('{ssm_param_name}'): {exc}"
            ) from exc

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Configure it before starting Cloud Forge."
    )

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()
