"""Check the loaded Phase 1 tables or record a clean-database replay."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from sqlalchemy import text

from .config import make_engine


CHECKS_SQL = Path(__file__).resolve().parents[1] / "sql" / "verify.sql"
PRIMARY_KEY_SORTS = {
    "customers": 'customer_id COLLATE "C"',
    "sellers": 'seller_id COLLATE "C"',
    "products": 'product_id COLLATE "C"',
    "orders": 'order_id COLLATE "C"',
    "order_items": 'order_id COLLATE "C", order_item_id',
}


def snapshot(engine):
    """Read counts, measures, and every stored value from one DB snapshot."""
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn:
        with conn.begin():
            conn.execute(text("SET TRANSACTION READ ONLY"))
            postgres_version = conn.execute(text("SHOW server_version")).scalar_one()
            counts = {"row_count": {}, "violation_count": {}, "relationship_count": {}}
            for kind, check_name, result in conn.execute(text(CHECKS_SQL.read_text(encoding="utf-8"))):
                counts[kind][check_name] = result

            fingerprints = {}
            for table, key in PRIMARY_KEY_SORTS.items():
                digest = sha256()
                statement = text(f"SELECT row_to_json(t)::text FROM public.{table} AS t ORDER BY {key}")
                with conn.execute(statement.execution_options(stream_results=True)) as rows:
                    for row_json in rows.scalars():
                        digest.update(row_json.encode("utf-8") + b"\n")
                fingerprints[table] = digest.hexdigest()

            measures = conn.execute(text("""
                SELECT sum(price)::text AS total_item_price_brl,
                       sum(freight_value)::text AS total_item_freight_brl
                FROM public.order_items
            """)).mappings().one()

    return {
        "postgres_server_version": postgres_version,
        "row_counts": counts["row_count"],
        "violations": counts["violation_count"],
        "relationship_counts": counts["relationship_count"],
        "measure_totals": dict(measures),
        "table_sha256": fingerprints,
    }


def find_problems(result):
    problems = [f"{name} returned {count} violations." for name, count in result["violations"].items() if count]
    if result["row_counts"]["orders"] == 0:
        problems.append("No orders loaded.")
    if result["relationship_counts"]["items_linked_to_all_parents"] != result["row_counts"]["order_items"]:
        problems.append("The number of fully linked items differs from the number of stored items.")
    return problems


def replay(engine, data_dir, order_limit):
    """Load unchanged inputs twice and compare both resulting database states."""
    from .ingest import load

    initial_counts = snapshot(engine)["row_counts"]
    report = {"mode": "replay", "initial_row_counts": initial_counts, "runs": [], "problems": []}
    if any(initial_counts.values()):
        report["problems"].append("Replay requires all five Phase 1 tables to start empty.")
        return report

    for run in (1, 2):
        audit = load(engine, data_dir, order_limit)
        result = snapshot(engine)
        report["runs"].append({"run": run, "ingestion": audit, "verification": result})
        for problem in find_problems(result):
            report["problems"].append(f"Run {run}. {problem}")
        if audit["tables"] != result["row_counts"]:
            report["problems"].append(f"Ingestion and PostgreSQL disagree on row counts in run {run}.")

    first_run, second_run = report["runs"]
    first = first_run["verification"]
    second = second_run["verification"]
    first_sources, second_sources = [
        {table: source["sha256"] for table, source in run["ingestion"]["files"].items()}
        for run in (first_run, second_run)
    ]
    source_sha256_equal = first_sources == second_sources
    database_comparisons = {
        "row_counts_equal": first["row_counts"] == second["row_counts"],
        "measure_totals_equal": first["measure_totals"] == second["measure_totals"],
        "all_table_sha256_equal": first["table_sha256"] == second["table_sha256"],
    }
    report["comparison"] = {"source_sha256_equal": source_sha256_equal, **database_comparisons}
    if not source_sha256_equal:
        report["problems"].append("The source file checksums differed between runs.")
    if not all(database_comparisons.values()):
        report["problems"].append("The two loads produced different PostgreSQL data.")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", action="store_true", help="Load the same CSV subset twice into an empty schema.")
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="CSV directory for --replay.")
    parser.add_argument("--order-limit", type=int, default=10000, help="Number of orders selected per replay load.")
    parser.add_argument("--output", type=Path, help="Also save the verification report as JSON.")
    args = parser.parse_args()
    if args.order_limit < 1:
        parser.error("--order-limit must be positive")

    engine = make_engine()
    try:
        if args.replay:
            report = replay(engine, args.data_dir, args.order_limit)
        else:
            result = snapshot(engine)
            report = {"mode": "verify", "verification": result, "problems": find_problems(result)}
    finally:
        engine.dispose()
    report["status"] = "failed" if report["problems"] else "passed"

    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    return int(bool(report["problems"]))


if __name__ == "__main__":
    raise SystemExit(main())
