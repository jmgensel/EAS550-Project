# EAS 550 Phase 1 | Olist database and repeatable load

## What this contribution adds

The starter project had table definitions and a Python script that cleared the tables. This update completes the load. It takes the first 10,000 Olist orders by purchase time, finds the item lines and parent records they need, validates the data, and loads it into five linked PostgreSQL tables. The verifier runs the load twice and compares the actual contents of every table.

**For a team meeting:** “I worked on getting the Olist files into PostgreSQL. Each order can have several item lines, and each line links to a product and a seller. The loader checks those links and loads the parent records first. I can show two runs with the same rows and the same item-price and freight totals.”

- [ERD](docs/erd.md) shows how to join the five tables.
- [Design note](docs/design_note.md) explains the keys, third normal form, and allowed exceptions.
- [Schema](sql/schema.sql) installs the tables and constraints. [SQL checks](sql/verify.sql) show counts, duplicate keys, missing references, and invalid item values.
- [JSON evidence](evidence/phase1.json) records both runs and the comparison.

## Get the data and database ready

Use Python 3.13 and an empty PostgreSQL database dedicated to this project. The tested versions are Python 3.13.13 and PostgreSQL 18.6. Install the PostgreSQL client tools, including `psql` and `libpq`, and make them available on your PATH. The examples use PowerShell 7.2 or later. Open a terminal at the repository root and run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

On macOS or Linux, use `.venv/bin/python` in place of the Windows interpreter path. In Bash or Zsh, set variables with `export DB_HOST=127.0.0.1` and reference them as `"$DB_HOST"`. Set the password in your environment or through an interactive prompt.

Download the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Olist publishes the data under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). The contribution filters the data to a chronological subset and selects the columns used by the database. [Source manifest](docs/source_manifest.json) records the snapshot date, raw counts, and SHA-256 checksums for the exact five files used. Put these files in `data/`, or use `--data-dir` to point to another folder.

- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_customers_dataset.csv`
- `olist_products_dataset.csv`
- `olist_sellers_dataset.csv`

Set the following in your terminal for your PostgreSQL server. The connecting role needs permission to create the five tables in `public` and write to them. The password prompt keeps the password out of command history. Python reads the shell environment. [`.env.example`](.env.example) lists the variable names.

```powershell
$env:DB_HOST = '127.0.0.1'
$env:DB_PORT = '5432'
$env:DB_NAME = 'olist_phase1' # Create this empty database first.
$env:DB_USER = 'your_postgres_user'
$env:DB_PASSWORD = Read-Host 'Database password' -MaskInput
$env:PGPASSWORD = $env:DB_PASSWORD
```

## Reproduce Phase 1

Create the schema once. Then run the replay on the initially empty schema. It loads the data twice and exits with an error if the checks fail or the resulting contents differ.

```powershell
psql -X -v ON_ERROR_STOP=1 -h $env:DB_HOST -p $env:DB_PORT -U $env:DB_USER -d $env:DB_NAME -f sql/schema.sql
.\.venv\Scripts\python.exe -m src.verify --replay --data-dir data --output evidence/reproduced.json
```

Use these commands to load once or to check a database that has already been loaded.

```powershell
.\.venv\Scripts\python.exe -m src.ingest --data-dir data
.\.venv\Scripts\python.exe -m src.verify
```

Each load validates the files before writing. It then clears and repopulates the five source tables in one transaction. A database error rolls the refresh back. Use a project database where refreshing those tables is expected. To try a small run, use `--order-limit 10` in a separate empty project database.

## What to show teammates

1. Start at `orders`. One row describes one purchase and points to its customer record.
2. Follow `order_id` into `order_items`. This shows the numbered item lines, including which product and seller belong to each line.
3. Open [the replay evidence](evidence/phase1.json). It starts with five empty tables and reports each load, each database check, and the comparison. A fingerprint changes if a key or value changes even when the row count stays the same.

For a live example, this query connects all five tables at the **item-line** level.

```sql
SELECT o.order_id, i.order_item_id, c.customer_state, p.product_category_name,
       s.seller_state, i.price, i.freight_value
FROM public.orders AS o
JOIN public.customers AS c USING (customer_id)
JOIN public.order_items AS i USING (order_id)
JOIN public.products AS p USING (product_id)
JOIN public.sellers AS s USING (seller_id)
ORDER BY o.order_id, i.order_item_id
LIMIT 5;
```

For the source snapshot tested here, each run loads 10,000 orders, 10,000 customer records, 11,192 item lines, 5,253 products, and 890 sellers. The item prices total BRL 1,420,857.13 and freight totals BRL 216,858.65. There are 153 orders with zero item lines. The 10,000-order sample spans September 4, 2016 through May 17, 2017.

The ingestion audit reports both data corrections and exceptions. It counts rows where surrounding whitespace was trimmed, rejected rows, and the reason counts. A rejected row can have several reasons. Blank optional timestamps and categories are stored as SQL `NULL`. The two full-snapshot runs trimmed zero rows and rejected zero rows. Rows outside the chronological sample and its references are reported separately by the loader.

A 10-order smoke test also passed on a fresh PostgreSQL database. In a separate check using modified CSVs, validation rejected a negative item price, an item with a missing seller, and both copies of a duplicate item key. It trimmed one amount and kept its valid zero freight.

## Integrate and submit

Apply the contribution on a branch of the team repository. It was prepared against the team archive at `13a1106add3b3fd8d55f73b9216fbfd1f761af45`. If you have the accompanying patch, run `git apply --check <path-to-patch>` from the repository root, then run `git apply <path-to-patch>`. Review the diff and commit the Phase 1 files, including `.env.example` and `evidence/phase1.json`. Keep local passwords and local dataset copies out of new commits. Submit the team repository URL and the integrated commit hash through Brightspace.

Codex assisted with translating the Phase 1 rubric into implementation, drafting the schema and loader, and checking the rerun evidence. This README links the artifacts and verification an author can review before submission.
