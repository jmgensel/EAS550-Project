# Phase 1 design note

## What the database stores

The five Olist tables store:
- Customers and their locations
- Sellers and their locations
- Products and the category they belong to
- Individual orders, including the buyer, the order status, and timestamps for when the order was placed, approved, shipped, and delivered.
- The items within an individual order, as well as their seller and price.

## Why the tables are in third normal form (3NF)

Important dependencies in the database:
- `customers.customer_id` determines the customer state and can be used to identify repeat buyers.
- `sellers.seller_id` determines seller state. `products.product_id` determines product category.
- `orders.order_id` determines the state of an individual order, including its buyer, status, and order dates. `orders.customer_id` is another candidate key for `orders`.
- The pair `(order_id, order_item_id)` determines the product, seller, shipping deadline, price, and freight for a line. The order ID identifies the order, and the line number identifies a position within that order. Different orders can include the same product, and an order can include the same product more than once. `order_items` resolves this many-to-many relationship and captures the seller assigned to each line.

Each field holds one value, satisfying 1NF. A line's non-key fields depend on its whole two-column key, and the entity tables have single-column keys, which satisfies 2NF. Customer state, product category, seller state, and order dates live with the records that determine them. Copying those attributes onto a line would make them depend indirectly on the line key through a foreign key. In the tables as designed, every documented determinant of a non-key attribute is a key for its own table. Therefore, 3NF is fully satisfied.

## What PostgreSQL enforces

Primary keys identify records, required foreign keys link them, and a unique constraint prevents reuse of an order-specific customer ID on another order. The following formats are enforced:
- IDs must be a 32-character hexadecimal string.
- State codes must be a string of two uppercase letters
- Status must be one of the eight source statuses defined in the schema. 
- Item numbers must be positive integers. 
- Exact decimal columns store price and freight to two places and require finite, nonnegative values. Zero freight is valid.

All fields are required, with the following exceptions allowing null values:
- Product: category
- Order: the timestamps for order approval and delivery to the carrier and destination (since the order will exist before it is approved, shipped, and delivered)

## What the loader and checks do

The loader starts creating the sample by collecting the earliest 10,000 candidate orders ranked by parsed purchase timestamp, with `order_id` breaking ties. It then collects customers, products, and sellers that are referenced by those orders. Then, it validates data formats and types, required fields, identifiers, keys, and references before writing to the database. Invalid required parents cause rejection of their dependent rows, and selected duplicate keys are rejected. The loader reports rejection reasons and preserves valid optional null values. Since rejections are performed after the initial sampling, they can lead to the sample being less than 10,000 orders. It's also important to note that this sample may not be representative of the full dataset, since it uses just the earliest orders.

After validation, one PostgreSQL transaction refreshes the five source tables. `TRUNCATE RESTRICT` clears their existing rows and stops if an outside foreign key prevents it. The loader writes customers, products, and sellers before orders and writes orders before item lines. Replacements are rolled back if they throw an error. With identical input, two runs should yield the same data. Verification compares row counts, key and foreign-key checks, exact monetary totals, and fingerprints of the stored rows in order to ensure all rows are present and unchanged.