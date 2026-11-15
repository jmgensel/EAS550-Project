"""Refresh the five Olist source tables from the selected CSV subset."""

import argparse
import json
from pathlib import Path

from sqlalchemy import MetaData, Table, text
from sqlalchemy.engine import Engine

from .config import make_engine
from .subset import prepare_subset


def load(engine: Engine, data_dir: Path, order_limit: int = 10_000) -> dict:
    tables, audit = prepare_subset(data_dir, order_limit)
    metadata = MetaData()

    with engine.begin() as conn:
        conn.execute(text("""
            TRUNCATE TABLE public.order_items, public.orders, public.products,
                           public.sellers, public.customers
            RESTRICT
        """))
        for name, frame in tables.items():
            if frame.empty:
                continue
            table = Table(name, metadata, schema="public", autoload_with=conn)
            # Send native ints, Decimals and datetimes through the typed SQLAlchemy table.
            # Object dtype lets pandas replace both NaT and pd.NA with SQL NULL.
            records = frame.astype(object).where(frame.notna(), None).to_dict("records")
            for start in range(0, len(records), 1_000):
                conn.execute(table.insert(), records[start:start + 1_000])

    return {"tables": {name: len(frame) for name, frame in tables.items()}, **audit}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--order-limit", type=int, default=10_000)
    args = parser.parse_args()

    engine = make_engine()
    try:
        audit = load(engine, args.data_dir, args.order_limit)
        print(json.dumps(audit, indent=2))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
