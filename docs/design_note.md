# Phase 1 design note

## What the database stores

The five Olist tables support questions such as how item value varies by product category and month or how freight charges vary by seller. `orders` holds purchase status and dates. Each row in `order_items` represents one numbered line in an order, with its product, seller, item price, and freight charge. Customers and sellers retain state, and products retain category. The Phase 1 schema omits ZIP, city, and other product attributes because state and category cover the questions above. Price and freight are separate amounts in Brazilian reais (BRL).

## Why the tables are in third normal form (3NF)

A functional dependency means knowing one value determines another. These are the important dependencies in this model.

- `customers.customer_id` determines the repeat-buyer identifier and customer state for that order's customer record.
- `sellers.seller_id` determines seller state. `products.product_id` determines product category.
- `orders.order_id` determines the customer record, status, and order dates. `orders.customer_id` is another candidate key for `orders`. Olist assigns a distinct customer record to each order and supplies `customer_unique_id` to identify repeat buyers. A buyer can order from different locations, so the customer state depends on the order-specific customer record. [Olist Customers Dataset](https://www.kaggle.com/olistbr/brazilian-ecommerce/home/)
- The pair `(order_id, order_item_id)` determines the product, seller, shipping deadline, price, and freight for a line. The order ID identifies the order, and the line number identifies a position within that order. Different orders can include the same product, and an order can include the same product more than once. `order_items` resolves this many-to-many relationship and captures the seller assigned to each line.

Each field holds one value (1NF). A line's non-key fields depend on its whole two-column key, and the entity tables have single-column keys (2NF). Customer state, product category, seller state, and order dates live with the records that determine them. Copying those attributes onto a line would make them depend indirectly on the line key through a foreign key. In the tables as designed, every documented determinant of a non-key attribute is a key for its own table (3NF).

## What PostgreSQL enforces

Primary keys identify records, required foreign keys link them, and a unique constraint prevents reuse of an order-specific customer ID on another order. IDs are text with a 32-character lowercase hexadecimal format. State codes have two uppercase letters, status must be one of the eight source statuses, and item numbers are positive integers. Exact decimal columns store price and freight to two places and require finite, nonnegative values. Zero freight is valid. Source timestamps have no timezone, so the database preserves them as written.

Purchase time, estimated delivery time, and item shipping deadline are required. Approval time, carrier handoff, and delivery to the customer can be unknown. A missing product category is also valid. The loader preserves those blanks as SQL `NULL`. An order can exist without item lines. The database allows repeated products, repeat buyers, and incomplete order lifecycles because all three fit the source model.

## What the loader and checks do

The sample starts with the earliest 10,000 candidate orders ranked by parsed purchase timestamp, with `order_id` breaking ties. The loader gathers their item lines and the referenced customers, products, and sellers. It validates types, required fields, identifiers, keys, and references before writing. Invalid required parents cause rejection of their dependent rows, and selected duplicate keys are rejected. The loader reports rejection reasons and preserves valid optional blanks. Rejections after selection leave a smaller sample. The chronological slice describes the first part of the historical dataset and may differ from later months.

After validation, one PostgreSQL transaction refreshes the five source tables. `TRUNCATE RESTRICT` clears their existing rows and stops if an outside foreign key prevents it. The loader writes customers, products, and sellers before orders and writes orders before item lines. An error rolls the replacement back. With identical input, two runs should yield the same data. Verification compares counts, key and foreign-key checks, measure quality, exact monetary totals, and fingerprints of the stored rows so a changed value is visible even when counts match.
