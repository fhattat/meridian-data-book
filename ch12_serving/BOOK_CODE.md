# Bölüm 12 — Veriyi sunmak: BI, ML ve AI tüketicileri

## Code from the book

Every code block of this chapter, in book order, under the book's section headings (Turkish, as printed).
Runnable files are in this folder; for scripts printed as "(shortened)" the full version is the file here.
Bu dosya bölümdeki bütün kod bloklarını kitaptaki sırasıyla ve alt bölüm başlıklarıyla verir.

### 12.1 Gold’dan tüketime: view, CTAS, semantik katman

> View (görünüm). Kaydedilmiş bir sorgudur; veri tutmaz, her çağrıldığında yeniden çalışır. Avantajı her zaman güncel olması, dezavantajı her seferinde hesap yapmasıdır.

**Code 12.1**

```sql
-- Runs the same on Databricks SQL and DuckDB
CREATE OR REPLACE VIEW gold.v_daily_sales AS
SELECT
    d.date,
    s.region,
    p.category,
    f.source_company,                 -- 'MM' store, 'BZ' online
    SUM(f.quantity)        AS units,
    SUM(f.amount_usd)      AS net_sales_usd,
    COUNT(DISTINCT f.order_id) AS orders
FROM gold.fact_sales f
JOIN gold.dim_date    d ON f.date_key    = d.date_key
JOIN gold.dim_product p ON f.product_key = p.product_key
LEFT JOIN gold.dim_store s ON f.store_key = s.store_key   -- defensive LEFT JOIN: rows with a missing key are not lost
GROUP BY d.date, s.region, p.category, f.source_company;
```

> CTAS (Create Table As Select). Aynı sorgunun sonucunu bir tabloya yazar. Pano her açıldığında 25 milyon satır taranacaksa, gece bir kez hesaplayıp sonucu saklamak daha ucuz ve hızlıdır:

**Code 12.2**

```sql
CREATE OR REPLACE TABLE gold.agg_sales_daily AS
SELECT * FROM gold.v_daily_sales;
```

> Semantik katman. Üçüncü araç bir tablo değil, bir tanımlar dosyasıdır. “Net satış” ne demek? İadeler düşülüyor mu? Kargo ücreti dahil mi? Euro ile yapılan satış hangi kurla çevriliyor? Bu soruların cevabı her panoda, her notebook’ta ayrı ayrı yazılırsa üç…

**Code 12.3**

```yaml
# metrics/sales.yaml
metric: net_sales_usd
description: Sales in USD, excluding test records and cancelled orders, net of returns, excluding shipping and tax.
source: gold.fact_sales
expression: SUM(amount_usd)
grain_note: fact_sales is at line level; use COUNT(DISTINCT order_id) for order counts.
currency_rule: Rate of the order date (silver.fx_rates); for weekends, the last business day.
owner: Marcus (finans)
```

### 12.3 ML tüketicisi: Lena’nın fraud modeli için feature tablosu

> En önemli kelime: “önceki”. amt_to_user_mean hesaplanırken kullanıcının bütün işlemlerinin ortalaması alınırsa, model eğitim sırasında geleceği görür. Bu hataya sızıntı (leakage) denir: Model testte harika görünür, gerçek hayatta çöker. Doğrusu, her satır…

**Code 12.4**

```python
# ch12_serving/export_features.py
import duckdb

FEATURE_SQL = """
WITH tx AS (
    SELECT t.txn_id, t.user_id, t.device_id, t.card_country, t.ip_country,
           CAST(t.hour AS INTEGER)            AS hour,
           o.order_ts_utc,
           t.amount_usd,
           CAST(t.is_fraud AS BOOLEAN)        AS is_fraud
    FROM silver.payment_transactions t
    JOIN silver.bz_orders o USING (order_id)
)
SELECT
    txn_id, order_ts_utc, amount_usd,
    amount_usd / NULLIF(AVG(amount_usd) OVER (
        PARTITION BY user_id ORDER BY order_ts_utc
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0)  AS amt_to_user_mean,
    hour BETWEEN 0 AND 4                                        AS is_night,
    card_country <> ip_country                                  AS country_mismatch,
    COUNT(user_id) OVER (
        PARTITION BY device_id ORDER BY order_ts_utc
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)       AS device_prior_txn,
    is_fraud
FROM tx
"""

def run(db_path: str = "data/meridian.duckdb") -> dict:
    """Builds the feature table, writes it to gold.ml_fraud_features and returns a summary."""
    con = duckdb.connect(db_path)
    con.execute(f"CREATE OR REPLACE TABLE gold.ml_fraud_features AS {FEATURE_SQL}")
    rows, frauds, null_ratio = con.execute("""
        SELECT COUNT(*), SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END),
               AVG(CASE WHEN amt_to_user_mean IS NULL THEN 1.0 ELSE 0 END)
        FROM gold.ml_fraud_features""").fetchone()
    return {"table": "gold.ml_fraud_features", "rows": rows,
            "fraud_rows": frauds, "first_txn_null_ratio": round(null_ratio, 4)}

if __name__ == "__main__":
    print(run())
```

### 12.4 Dördüncü tüketici, AI: RAG pipeline’ı = veri pipeline’ı

> Adım 3: Embedding ve indeks. Her parça bir embedding modeliyle sayı dizisine (vektöre) çevrilir. Benzer anlamlı metinlerin vektörleri birbirine yakın düşer. Arama, sorunun vektörüne en yakın parçaları bulmaktır. Embedding modeli ve vektör veritabanı hızla…

**Code 12.5**

```python
# ch12_serving/build_rag_index.py
import hashlib, json, re
from pathlib import Path
from typing import Protocol

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")

class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...

class VectorStore(Protocol):
    def upsert(self, rows: list[dict]) -> None: ...
    def search(self, vector: list[float], top_k: int, source: str) -> list[dict]: ...

def mask_pii(text: str) -> str:
    return PHONE.sub("[PHONE]", EMAIL.sub("[EMAIL]", text))

def chunk(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    step = size - overlap
    return [text[i:i + size] for i in range(0, max(len(text), 1), step)]

def load_tickets(con) -> list[dict]:
    """BZ11 from bronze (loaded in Chapter 8 with --source bz_tickets); latest version of each ticket."""
    rows = con.execute("""
        SELECT ticket_id, created_at, subject, body
        FROM bronze.bz_support_tickets
        QUALIFY ROW_NUMBER() OVER (PARTITION BY ticket_id ORDER BY _ingested_at DESC) = 1
    """).fetchall()
    return [{"doc_id": f"ticket:{tid}", "source": "tickets", "version": created,
             "text": f"{subject}\n{body}"} for tid, created, subject, body in rows]

def load_pdfs(folder: str) -> list[dict]:
    from pypdf import PdfReader
    docs = []
    for pdf in sorted(Path(folder).glob("*.pdf")):
        text = "\n".join(p.extract_text() or "" for p in PdfReader(pdf).pages)
        docs.append({"doc_id": f"doc:{pdf.stem}", "source": "docs",
                     "version": str(pdf.stat().st_mtime), "text": text})
    return docs

def build(docs: list[dict], embedder: Embedder, store: VectorStore) -> dict:
    rows = []
    for d in docs:
        for n, piece in enumerate(chunk(mask_pii(d["text"]))):
            rows.append({"chunk_id": hashlib.sha256(f"{d['doc_id']}|{n}|{piece}".encode()).hexdigest()[:16],
                         "doc_id": d["doc_id"], "source": d["source"], "version": d["version"],
                         "chunk_no": n, "text": piece})
    for i in range(0, len(rows), 64):                      # embed in small batches
        batch = rows[i:i + 64]
        for r, v in zip(batch, embedder.embed([r["text"] for r in batch])):
            r["vector"] = v
    store.upsert(rows)
    return {"documents": len(docs), "chunks": len(rows)}
```

> Script → araç: belge_ara. Sam’in asistanı indeksi doğrudan okumaz; bir araç çağırır. Aynı dosyaya küçük bir run() fonksiyonu ekliyoruz:

**Code 12.6**

```python
def run(query: str, top_k: int = 5, source: str = "all") -> dict:
    """Finds the most relevant chunks in the index. Read-only."""
    vector = get_embedder().embed([mask_pii(query)])[0]
    hits = get_store().search(vector, top_k=top_k, source=source)
    return {"query": query, "hits": [{k: h[k] for k in ("doc_id", "source", "version", "chunk_no", "text", "score")} for h in hits]}
```

### 12.5 Doğal dille soru (text-to-SQL) ve neden modellenmiş veri şart

> Doğrulanmış birkaç örnek soru ve sorgusu.

**Code 12.7**

```text
Sen Meridian Market'in veri asistanısın. Yalnızca aşağıdaki gold tablolarını ve
metrik tanımlarını kullan. Bir metrik tanımda yoksa uydurma; "tanımlı değil" de.
Sorguyu salt okunur çalıştır, sonucu bir cümleyle anlat ve kullandığın SQL'i,
tabloları ve metrik tanımının adını cevabın altına yaz.

[gold şeması ve sütun açıklamaları]
[metrics/sales.yaml]
[örnek soru ve sorgular]

Soru: Mart 2027'de online kanalın net satışlardaki payı ne kadardı?
```

> İyi bir cevabın altında şöyle bir sorgu durur:

**Code 12.8**

```sql
SELECT
    SUM(CASE WHEN source_company = 'BZ' THEN net_sales_usd END)
      / SUM(net_sales_usd) AS online_share
FROM gold.v_daily_sales
WHERE date >= DATE '2027-03-01' AND date < DATE '2027-04-01';
```
