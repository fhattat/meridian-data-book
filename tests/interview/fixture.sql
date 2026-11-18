-- Ek C SQL alıştırmaları için küçük test verisi (sentetik).
-- Kanonik şemanın yalnızca alıştırmaların kullandığı sütunları var.
-- Her tuzak en az bir satırla temsil ediliyor; beklenen cevaplar test_interview_solutions.py'de.

CREATE TABLE silver.bz_orders (
    order_id VARCHAR, customer_id VARCHAR, order_local_date DATE, status_code VARCHAR,
    currency VARCHAR, order_total_original DECIMAL(12,2), is_test BOOLEAN, source_company VARCHAR
);
INSERT INTO silver.bz_orders VALUES
    ('O1', 'BZ-U-1', '2027-03-02', 'delivered', 'USD', 30.00, FALSE, 'BZ'),
    ('O2', 'BZ-U-2', '2027-03-15', 'cancelled', 'USD', 20.00, FALSE, 'BZ'),
    ('O3', 'BZ-U-1', '2027-03-20', 'delivered', 'EUR', 50.00, FALSE, 'BZ'),  -- başlık 50, kalemler 45
    ('O4', 'BZ-U-3', '2027-03-31', 'shipped',   'USD', 10.00, FALSE, 'BZ'),  -- kalemi yok
    ('O5', 'BZ-U-2', '2027-04-01', 'delivered', 'USD', 15.00, FALSE, 'BZ'),  -- Mart dışı
    ('O6', 'BZ-U-9', '2027-03-10', 'delivered', 'USD',  5.00, TRUE,  'BZ'),  -- test, kalemi yok
    ('O7', 'BZ-U-3', '2027-03-12', 'delivered', 'USD', 12.00, FALSE, 'BZ');  -- kuruş farkı (tolerans içinde)

CREATE TABLE silver.bz_order_items (
    order_item_id VARCHAR, order_id VARCHAR, qty INTEGER, amount_original DECIMAL(12,2), is_test BOOLEAN
);
INSERT INTO silver.bz_order_items VALUES
    ('I1', 'O1', 1, 10.00, FALSE), ('I2', 'O1', 2, 20.00, FALSE),
    ('I3', 'O2', 1, 20.00, FALSE),
    ('I4', 'O3', 1, 25.00, FALSE), ('I5', 'O3', 1, 20.00, FALSE),
    ('I6', 'O5', 1, 15.00, FALSE),
    ('I7', 'O7', 1, 6.00, FALSE),  ('I8', 'O7', 1, 5.99, FALSE);

CREATE TABLE gold.dim_customer (
    customer_key VARCHAR, customer_id VARCHAR, valid_from DATE, valid_to DATE, is_current BOOLEAN
);
INSERT INTO gold.dim_customer VALUES
    ('K1a', 'MM-M-1', '2025-01-01', '2026-06-30', FALSE),
    ('K1b', 'MM-M-1', '2026-07-01', '9999-12-31', TRUE),
    ('K2',  'BZ-U-1', '2025-03-01', '9999-12-31', TRUE);

CREATE TABLE gold.dim_store (store_key VARCHAR, store_id VARCHAR, store_name VARCHAR, region VARCHAR);
INSERT INTO gold.dim_store VALUES
    ('S1',  'MM-001', 'Boston Back Bay',  'Northeast'),
    ('S2',  'MM-031', 'Seattle Downtown', 'West'),
    ('S99', 'BZ-ONLINE', 'Bazaarly Online', NULL);

CREATE TABLE gold.dim_date (date_key INTEGER, date DATE, year INTEGER, month INTEGER, year_month VARCHAR);
INSERT INTO gold.dim_date VALUES
    (20260115, '2026-01-15', 2026, 1, '2026-01'),
    (20260620, '2026-06-20', 2026, 6, '2026-06'),
    (20270110, '2027-01-10', 2027, 1, '2027-01');

CREATE TABLE gold.dim_product (product_key VARCHAR, product_id VARCHAR, category VARCHAR);
INSERT INTO gold.dim_product VALUES
    ('P1', 'MM-PRD-00001', 'Electronics'), ('P2', 'MM-PRD-00002', 'Home'),
    ('P3', 'MM-PRD-00003', 'Personal Care'), ('P4', 'MM-PRD-00004', 'Toys');

CREATE TABLE gold.fact_sales (
    sales_line_id VARCHAR, date_key INTEGER, product_key VARCHAR, store_key VARCHAR,
    order_id VARCHAR, source_company VARCHAR, quantity INTEGER, amount_usd DECIMAL(12,2)
);
INSERT INTO gold.fact_sales VALUES
    ('L1',  20260115, 'P1', 'S1',  'R1', 'MM',  1, 100.00),
    ('L2',  20260115, 'P2', 'S1',  'R1', 'MM',  1,  50.00),
    ('L3',  20260620, 'P3', 'S1',  'R2', 'MM',  1,  30.00),
    ('L4',  20260620, 'P4', 'S1',  'R2', 'MM',  1,  10.00),
    ('L5',  20260620, 'P1', 'S1',  'R3', 'MM', -1, -20.00),  -- iade
    ('L6',  20260115, 'P2', 'S2',  'R4', 'MM',  1,  80.00),
    ('L7',  20260115, 'P1', 'S2',  'R4', 'MM',  1,  80.00),  -- S2'de eşitlik
    ('L8',  20260620, 'P3', 'S2',  'R5', 'MM',  1,   5.00),
    ('L9',  20260620, 'P1', 'S99', 'O1', 'BZ',  1,  40.00),
    ('L10', 20270110, 'P4', 'S1',  'R6', 'MM',  1, 999.00);  -- 2027, Soru 3'e girmez

CREATE TABLE silver.customers (
    customer_id VARCHAR, customer_type VARCHAR, email_norm VARCHAR, is_test BOOLEAN, source_company VARCHAR
);
INSERT INTO silver.customers VALUES
    ('MM-M-1', 'member', 'ayla@example.com',  FALSE, 'MM'),
    ('BZ-U-1', 'user',   'ayla@example.com',  FALSE, 'BZ'),
    ('MM-M-2', 'member', 'ben@example.com',   FALSE, 'MM'),
    ('BZ-U-3', 'user',   'cem@example.com',   FALSE, 'BZ'),
    ('MM-M-4', 'member', 'dora@example.com',  FALSE, 'MM'),
    ('MM-A-4', 'account','dora@example.com',  FALSE, 'MM'),
    ('BZ-U-4', 'user',   'dora@example.com',  FALSE, 'BZ'),
    ('MM-M-999','member','test@example.com',  TRUE,  'MM'),
    ('BZ-U-9', 'user',   'test@example.com',  TRUE,  'BZ');

CREATE TABLE silver.customer_xref (
    email_norm VARCHAR, mm_member_id VARCHAR, mm_account_id VARCHAR, bz_user_id VARCHAR, source_count INTEGER
);
INSERT INTO silver.customer_xref VALUES
    ('ayla@example.com', 'MM-M-1',   NULL,     'BZ-U-1', 2),
    ('ben@example.com',  'MM-M-2',   NULL,     NULL,     1),
    ('cem@example.com',  NULL,       NULL,     'BZ-U-3', 1),
    ('dora@example.com', 'MM-M-4',   'MM-A-4', 'BZ-U-4', 3),
    ('test@example.com', 'MM-M-999', NULL,     'BZ-U-9', 2);

CREATE TABLE bronze.mm_pos_named (rec_type VARCHAR, RECEIPT_NO VARCHAR, LINE_NO VARCHAR);
INSERT INTO bronze.mm_pos_named VALUES
    ('H', 'R1 ', NULL), ('L', 'R1 ', '1'), ('L', 'R1', ' 2'),
    ('H', 'R2', NULL),  ('L', 'R2', '1'),
    ('H', 'R3', NULL),  ('L', 'R3', '1');

CREATE TABLE silver.pos_lines (receipt_no VARCHAR, line_no INTEGER, is_test BOOLEAN);
INSERT INTO silver.pos_lines VALUES
    ('R1', 1, FALSE), ('R1', 2, FALSE),
    ('R3', 1, TRUE);  -- test fişi: işaretli, silinmemiş
