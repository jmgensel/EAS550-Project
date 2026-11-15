-- Run with psql -f sql/verify.sql. Every violation count should be zero.
WITH checks (kind, check_name, result) AS (
    SELECT 'row_count', 'customers', count(*) FROM public.customers
    UNION ALL
    SELECT 'row_count', 'sellers', count(*) FROM public.sellers
    UNION ALL
    SELECT 'row_count', 'products', count(*) FROM public.products
    UNION ALL
    SELECT 'row_count', 'orders', count(*) FROM public.orders
    UNION ALL
    SELECT 'row_count', 'order_items', count(*) FROM public.order_items
    UNION ALL
    SELECT 'violation_count', 'duplicate_customer_keys', count(*)
    FROM (SELECT customer_id FROM public.customers GROUP BY customer_id HAVING count(*) > 1) AS duplicates
    UNION ALL
    SELECT 'violation_count', 'duplicate_seller_keys', count(*)
    FROM (SELECT seller_id FROM public.sellers GROUP BY seller_id HAVING count(*) > 1) AS duplicates
    UNION ALL
    SELECT 'violation_count', 'duplicate_product_keys', count(*)
    FROM (SELECT product_id FROM public.products GROUP BY product_id HAVING count(*) > 1) AS duplicates
    UNION ALL
    SELECT 'violation_count', 'duplicate_order_keys', count(*)
    FROM (SELECT order_id FROM public.orders GROUP BY order_id HAVING count(*) > 1) AS duplicates
    UNION ALL
    SELECT 'violation_count', 'duplicate_order_customer_keys', count(*)
    FROM (SELECT customer_id FROM public.orders GROUP BY customer_id HAVING count(*) > 1) AS duplicates
    UNION ALL
    SELECT 'violation_count', 'duplicate_item_keys', count(*)
    FROM (
        SELECT order_id, order_item_id
        FROM public.order_items
        GROUP BY order_id, order_item_id
        HAVING count(*) > 1
    ) AS duplicates
    UNION ALL
    SELECT 'violation_count', 'orders_missing_customer', count(*)
    FROM public.orders AS o
    LEFT JOIN public.customers AS c ON c.customer_id = o.customer_id
    WHERE c.customer_id IS NULL
    UNION ALL
    SELECT 'violation_count', 'items_missing_order', count(*)
    FROM public.order_items AS i
    LEFT JOIN public.orders AS o ON o.order_id = i.order_id
    WHERE o.order_id IS NULL
    UNION ALL
    SELECT 'violation_count', 'items_missing_product', count(*)
    FROM public.order_items AS i
    LEFT JOIN public.products AS p ON p.product_id = i.product_id
    WHERE p.product_id IS NULL
    UNION ALL
    SELECT 'violation_count', 'items_missing_seller', count(*)
    FROM public.order_items AS i
    LEFT JOIN public.sellers AS s ON s.seller_id = i.seller_id
    WHERE s.seller_id IS NULL
    UNION ALL
    SELECT 'violation_count', 'items_with_invalid_price_or_freight', count(*)
    FROM public.order_items
    WHERE price IS NULL OR price < 0 OR price = 'NaN'::numeric
       OR freight_value IS NULL OR freight_value < 0 OR freight_value = 'NaN'::numeric
    UNION ALL
    SELECT 'violation_count', 'items_with_invalid_line_number', count(*)
    FROM public.order_items
    WHERE order_item_id IS NULL OR order_item_id <= 0
    UNION ALL
    SELECT 'relationship_count', 'items_linked_to_all_parents', count(*)
    FROM public.order_items AS i
    JOIN public.orders AS o ON o.order_id = i.order_id
    JOIN public.customers AS c ON c.customer_id = o.customer_id
    JOIN public.products AS p ON p.product_id = i.product_id
    JOIN public.sellers AS s ON s.seller_id = i.seller_id
    UNION ALL
    SELECT 'relationship_count', 'orders_without_items', count(*)
    FROM public.orders AS o
    WHERE NOT EXISTS (SELECT 1 FROM public.order_items AS i WHERE i.order_id = o.order_id)
)
SELECT kind, check_name, result
FROM checks
ORDER BY kind, check_name;
