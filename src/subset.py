"""Select the earliest orders and keep the rows that connect to them."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pandas as pd

from .validate import ID_PATTERN, ORDER_STATUSES, STATE_PATTERN, RowChecks


SOURCE_COLUMNS = {
    "customers": ("customer_id", "customer_unique_id", "customer_state"),
    "sellers": ("seller_id", "seller_state"),
    "products": ("product_id", "product_category_name"),
    "orders": (
        "order_id", "customer_id", "order_status", "order_purchase_timestamp",
        "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ),
    "order_items": (
        "order_id", "order_item_id", "product_id", "seller_id",
        "shipping_limit_date", "price", "freight_value",
    ),
}


def read_sources(data_dir: Path) -> tuple[dict, dict]:
    frames = {}
    files = {}
    for table, fields in SOURCE_COLUMNS.items():
        path = data_dir / f"olist_{table}_dataset.csv"
        raw = path.read_bytes()
        if b"\x00" in raw:
            raise ValueError(f"Unexpected NUL byte in {path.name}")
        frame = pd.read_csv(
            BytesIO(raw), usecols=list(fields), dtype="string",
            keep_default_na=False, encoding="utf-8-sig",
        ).fillna("")
        trimmed = frame.apply(lambda column: column.str.strip())
        frames[table] = trimmed[list(fields)]
        files[table] = {
            "file": path.name,
            "sha256": sha256(raw).hexdigest(),
            "rows_read": len(frame),
            "rows_trimmed": int(frame.ne(trimmed).any(axis=1).sum()),
        }
    return frames, files


def parent_rows(
    source: pd.DataFrame, child: pd.DataFrame, key: str,
) -> RowChecks:
    checks = RowChecks(source.loc[source[key].isin(child[key])].copy())
    checks.require_pattern(key, ID_PATTERN)
    checks.require_unique(key)
    return checks


def prepare_subset(data_dir: Path, order_limit: int) -> tuple[dict, dict]:
    if order_limit < 1:
        raise ValueError("The order limit must be positive.")
    source, files = read_sources(data_dir)

    # Read all orders to establish the sample. Reject ambiguous order IDs before sorting.
    order_selection = RowChecks(source["orders"])
    order_selection.require_pattern("order_id", ID_PATTERN)
    order_selection.require_unique("order_id")
    order_selection.parse_timestamp("order_purchase_timestamp")
    eligible = order_selection.accepted()
    sample = eligible.sort_values(["order_purchase_timestamp", "order_id"]).head(order_limit)

    orders = RowChecks(sample.copy())
    orders.require_pattern("customer_id", ID_PATTERN)
    orders.require_unique("customer_id")
    orders.reject("invalid_or_missing_order_status", ~orders.frame["order_status"].isin(ORDER_STATUSES))
    orders.parse_timestamp("order_estimated_delivery_date")
    for column in (
        "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date",
    ):
        orders.parse_timestamp(column, optional=True)

    customers = parent_rows(source["customers"], orders.accepted(), "customer_id")
    customers.require_pattern("customer_unique_id", ID_PATTERN)
    customers.require_pattern("customer_state", STATE_PATTERN)
    orders.require_reference("customer_id", customers.accepted()["customer_id"])
    order_rows = orders.accepted()
    if order_rows.empty:
        raise ValueError("No valid sampled orders remain. The database was left intact.")

    # Keep items of sampled orders, so an item of a rejected order is counted as rejected.
    raw_items = source["order_items"]
    items = RowChecks(raw_items.loc[raw_items["order_id"].isin(sample["order_id"])].copy())
    items.parse_item_number()
    items.require_unique("order_id", "order_item_id")
    for column in ("product_id", "seller_id"):
        items.require_pattern(column, ID_PATTERN)
    items.parse_timestamp("shipping_limit_date")
    items.parse_money("price")
    items.parse_money("freight_value")
    items.require_reference("order_id", order_rows["order_id"])

    products = parent_rows(source["products"], items.accepted(), "product_id")
    categories = products.frame["product_category_name"]
    products.frame["product_category_name"] = categories.mask(categories.eq(""))
    sellers = parent_rows(source["sellers"], items.accepted(), "seller_id")
    sellers.require_pattern("seller_state", STATE_PATTERN)
    items.require_reference("product_id", products.accepted()["product_id"])
    items.require_reference("seller_id", sellers.accepted()["seller_id"])
    item_rows = items.accepted()

    tables = {
        "customers": customers.accepted().loc[lambda frame: frame["customer_id"].isin(order_rows["customer_id"])],
        "sellers": sellers.accepted().loc[lambda frame: frame["seller_id"].isin(item_rows["seller_id"])],
        "products": products.accepted().loc[lambda frame: frame["product_id"].isin(item_rows["product_id"])],
        "orders": order_rows,
        "order_items": item_rows,
    }
    checks_by_table = {
        "customers": customers, "sellers": sellers, "products": products,
        "orders": orders, "order_items": items,
    }
    validation = {}
    for table, checks in checks_by_table.items():
        validation[table] = checks.report(len(tables[table]))
        if table != "orders":
            validation[table]["rows_outside_scope"] = files[table]["rows_read"] - len(checks.frame)

    return tables, {
        "files": files,
        "order_selection": {
            "requested": order_limit,
            "sampled": len(sample),
            "rows_rejected_before_sampling": int(order_selection.invalid.sum()),
            "rejection_reasons": order_selection.reasons,
            "eligible_orders_outside_sample": len(eligible) - len(sample),
            "first_sampled_purchase": sample["order_purchase_timestamp"].min().isoformat(sep=" "),
            "last_sampled_purchase": sample["order_purchase_timestamp"].max().isoformat(sep=" "),
        },
        "validation": validation,
    }
