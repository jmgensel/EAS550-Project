"""Open a PostgreSQL connection using environment variables."""

import os

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine


def make_engine() -> Engine:
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
