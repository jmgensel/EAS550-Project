-- Apply once to an empty PostgreSQL database.
BEGIN;

CREATE TABLE public.customers (
    customer_id TEXT PRIMARY KEY CHECK (customer_id ~ '^[0-9a-f]{32}$'),
    customer_unique_id TEXT NOT NULL CHECK (customer_unique_id ~ '^[0-9a-f]{32}$'),
    customer_state TEXT NOT NULL CHECK (customer_state ~ '^[A-Z]{2}$')
);

CREATE TABLE public.sellers (
    seller_id TEXT PRIMARY KEY CHECK (seller_id ~ '^[0-9a-f]{32}$'),
    seller_state TEXT NOT NULL CHECK (seller_state ~ '^[A-Z]{2}$')
);

CREATE TABLE public.products (
    product_id TEXT PRIMARY KEY CHECK (product_id ~ '^[0-9a-f]{32}$'),
    product_category_name TEXT CHECK (btrim(product_category_name) <> '')
);

CREATE TABLE public.orders (
    order_id TEXT PRIMARY KEY CHECK (order_id ~ '^[0-9a-f]{32}$'),
    customer_id TEXT NOT NULL UNIQUE REFERENCES public.customers (customer_id),
    order_status TEXT NOT NULL CHECK (
        order_status IN ('approved', 'canceled', 'created', 'delivered',
                         'invoiced', 'processing', 'shipped', 'unavailable')
    ),
    order_purchase_timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    order_approved_at TIMESTAMP WITHOUT TIME ZONE,
    order_delivered_carrier_date TIMESTAMP WITHOUT TIME ZONE,
    order_delivered_customer_date TIMESTAMP WITHOUT TIME ZONE,
    order_estimated_delivery_date TIMESTAMP WITHOUT TIME ZONE NOT NULL
);

CREATE TABLE public.order_items (
    order_id TEXT NOT NULL REFERENCES public.orders (order_id),
    order_item_id INTEGER NOT NULL CHECK (order_item_id > 0),
    product_id TEXT NOT NULL REFERENCES public.products (product_id),
    seller_id TEXT NOT NULL REFERENCES public.sellers (seller_id),
    shipping_limit_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    price NUMERIC(12,2) NOT NULL CHECK (price >= 0 AND price <> 'NaN'::NUMERIC),
    freight_value NUMERIC(12,2) NOT NULL
        CHECK (freight_value >= 0 AND freight_value <> 'NaN'::NUMERIC),
    PRIMARY KEY (order_id, order_item_id)
);

COMMIT;
