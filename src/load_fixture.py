import csv
import os
from pathlib import Path
import psycopg2

# Determine project directories.
ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = ROOT / "fixtures"
SCHEMA_FILE = ROOT / "sql" / "schema.sql"

# Tables must be loaded in foreign-key dependency order.
TABLES = [
    "customers",
    "sellers",
    "products",
    "orders",
    "order_items"
]

CSV_COLUMNS = {
    "customers": [
        "customer_id",
        "customer_unique_id",
        "customer_state"
    ],
    "sellers": [
        "seller_id",
        "seller_state"
    ],
    "products": [
        "product_id",
        "product_category_name"
    ],
    "orders": [
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date"
    ],
    "order_items": [
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "shipping_limit_date",
        "price",
        "freight_value"
    ]
}

"""Connect to the PostgreSQL database."""
def get_connection():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        dbname=os.environ["DB_NAME"]
    )

"""Create the five database tables."""
def create_schema(cursor):
    with open(SCHEMA_FILE, "r", encoding="utf-8") as file:
        cursor.execute(file.read())
    print("Schema created successfully.")

"""Load a CSV file into its corresponding database table."""
def load_csv(cursor, table_name):
    csv_path = FIXTURE_DIR / f"{table_name}.csv"
    print(f"Loading {csv_path.name}...")
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing fixture: {csv_path}")

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no headers: {csv_path.name}")

        columns = CSV_COLUMNS[table_name]
        missing_columns = [
            c for c in columns
            if c not in reader.fieldnames
        ]

        if missing_columns: raise ValueError(
            f"{table_name}.csv is missing required columns: "
            f"{missing_columns}"
        )

        rows = list(reader)
        if not rows:
            raise ValueError(f"CSV contains no records: {csv_path.name}")

        column_names = ", ".join(f'"{column}"' for column in columns)
        placeholders = ", ".join(["%s"] * len(columns))
        query = (
            f'INSERT INTO public."{table_name}" '
            f'({column_names}) VALUES ({placeholders})'
        )

        # Insert each CSV record.
        for row in rows:
            values = [
                row[column] if row[column] != "" else None
                for column in columns
            ]
            cursor.execute(query, values)
    print(f"  Inserted {len(rows)} records into {table_name}.")

"""Verify that all five tables contain records."""
def verify_data(cursor):
    for table_name in TABLES:
        cursor.execute(f'SELECT COUNT(*) FROM public."{table_name}"')
        count = cursor.fetchone()[0]
        if count == 0:
            raise ValueError(f"Table {table_name} is empty!")
        print(f"  {table_name}: {count} records")

"""Load the fixture into PostgreSQL."""
def main():
    connection = None

    try:
        connection = get_connection()
        with connection:
            with connection.cursor() as cursor:
                create_schema(cursor)
                for table_name in TABLES:
                    load_csv(cursor, table_name)
                verify_data(cursor)
        print("\nFixture loaded successfully!")

    except Exception as error:
        print(f"\nFixture loading failed: {error}")
        raise

    finally:
        if connection is not None:
            connection.close()

main()