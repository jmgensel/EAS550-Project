import csv
import random
import pathlib

NUM_ORDERS = 750
SEED = 42

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data"
FIXTURE_PATH = ROOT / "fixtures/large"
DATA_FILES = {
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv"
}

def readCSV(fn):
    p = DATA_PATH / fn
    with open(p, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        h = r.fieldnames
        rows = list(r)
    return h, rows

def writeCSV(fn, h, r):
    path = FIXTURE_PATH / fn

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=h)
        writer.writeheader()
        writer.writerows(r)

def getRandomOrders(n):
    _, orders = readCSV(DATA_FILES["orders"])
    obc = {}
    for o in orders:
        cid = o["customer_id"]
        obc.setdefault(cid, []).append(o)
    rng = random.Random(SEED)
    cids = list(obc.keys())
    customers = rng.sample(cids, min(n, len(cids)))
    orders = [rng.choice(obc[cid]) for cid in customers]
    return orders

def main():
    FIXTURE_PATH.mkdir(parents=True, exist_ok=True)
    o = getRandomOrders(NUM_ORDERS)
    orderHeaders = list(o[0].keys())
    oid = {order["order_id"] for order in o}
    cid = {order["customer_id"] for order in o}

    customerHeaders, allCustomers = readCSV(DATA_FILES["customers"])
    c = [c for c in allCustomers if c["customer_id"] in cid]

    itemHeaders, allItems = readCSV(DATA_FILES["order_items"])
    oi = [i for i in allItems if i["order_id"] in oid]

    pid = {i["product_id"] for i in oi}
    sid = {i["seller_id"] for i in oi}

    productHeaders, allProducts = readCSV(DATA_FILES["products"])
    p = [p for p in allProducts if p["product_id"] in pid]

    sellerHeaders, allSellers = readCSV(DATA_FILES["sellers"])
    s = [s for s in allSellers if s["seller_id"] in sid]

    writeCSV("customers.csv", customerHeaders, c)
    writeCSV("sellers.csv", sellerHeaders, s)
    writeCSV("products.csv", productHeaders, p)
    writeCSV("orders.csv", orderHeaders, o)
    writeCSV("order_items.csv", itemHeaders, oi)

main()