"""Open a PostgreSQL connection using environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, make_url
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env.local")
load_dotenv(PROJECT_ROOT / ".env")


def make_engine() -> Engine:
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        url = make_url(database_url)
        if url.drivername in ("postgres", "postgresql"):
            url = url.set(drivername="postgresql+psycopg")
        return create_engine(url, hide_parameters=True)

    required = ("DB_HOST", "DB_NAME", "DB_USER")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise ValueError("Set these environment variables: " + ", ".join(missing))
    return create_engine(
        URL.create(
            "postgresql+psycopg",
            username=os.environ["DB_USER"],
            password=os.environ.get("DB_PASSWORD"),
            host=os.environ["DB_HOST"],
            port=int(os.environ.get("DB_PORT") or "5432"),
            database=os.environ["DB_NAME"],
        ),
        hide_parameters=True,
    )
