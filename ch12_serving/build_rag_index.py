"""build_rag_index.py - Chapter 18 version (Chapter 12 + Chapter 17 additions).

Usage: python ch12_serving/build_rag_index.py --env local

Built from the Chapter 12.4 version (chunking, PII masking, Embedder/VectorStore interfaces),
the Chapter 17.2 additions (instruction scan + quarantine) and the Chapter 18.3 run().
repo: a local, dependency-free embedder (hashed bag of words) and a DuckDB table as the vector
store, so the whole index runs offline. Replace get_embedder()/get_store() with your provider.
"""
import argparse
import math
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

# the list from Chapter 17.2, unchanged
INJECTION_PATTERNS = [
    r"ignore (all |your )?(previous|prior) instructions",
    r"(system|developer) (note|prompt|message)\s*(to|for)?\s*(the )?(ai|assistant|model)",
    r"you are now\b", r"disregard (the )?(rules|instructions)",
    r"(list|send|reveal|export) (all )?(customer|user)s?'? (emails?|phones?|data)",
]
INJECTION = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)


def scan_for_instructions(doc: dict) -> str | None:
    """Returns the matching fragment if the text looks like it contains instructions aimed at the model."""
    m = INJECTION.search(doc["text"])
    return m.group(0) if m else None


def split_suspicious(docs: list[dict]) -> tuple[list[dict], list[dict]]:
    clean, held = [], []
    for d in docs:
        hit = scan_for_instructions(d)
        if hit:
            held.append({**d, "reason": f"possible_prompt_injection: {hit}"})
        else:
            clean.append(d)
    return clean, held




# --------------------------------------------------------------------------- repo: local implementations
DB = "data/meridian.duckdb"
DOCS = "data/raw/bazaarly/docs"
WORD = re.compile(r"[a-z0-9]+")


class HashEmbedder:
    """Hashed bag-of-words vectors (no model download). Good enough to test the pipeline end to end."""
    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            v = [0.0] * self.dim
            for w in WORD.findall(t.lower()):
                h = int(hashlib.md5(w.encode()).hexdigest(), 16)
                v[h % self.dim] += 1.0 if (h >> 8) % 2 else -1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([round(x / n, 6) for x in v])
        return out


class DuckDBStore:
    """gold.rag_chunks: one row per chunk; the vector is kept as JSON text."""
    def __init__(self, db: str = DB, read_only: bool = False):
        self.db, self.read_only = db, read_only

    def upsert(self, rows: list[dict]) -> None:
        import duckdb
        import pandas as pd
        con = duckdb.connect(self.db)
        df = pd.DataFrame([{**{k: r[k] for k in ("chunk_id", "doc_id", "source", "version", "chunk_no", "text")},
                            "vector_json": json.dumps(r["vector"])} for r in rows])
        con.execute("CREATE SCHEMA IF NOT EXISTS gold")
        con.register("chunks_df", df)
        con.execute("CREATE OR REPLACE TABLE gold.rag_chunks AS SELECT * FROM chunks_df")
        con.close()

    def search(self, vector: list[float], top_k: int, source: str) -> list[dict]:
        import duckdb
        con = duckdb.connect(self.db, read_only=True)
        sql = "SELECT chunk_id, doc_id, source, version, chunk_no, text, vector_json FROM gold.rag_chunks"
        rows = con.execute(sql + ("" if source == "all" else " WHERE source = ?"),
                           [] if source == "all" else [source]).fetchall()
        con.close()
        scored = []
        for chunk_id, doc_id, src, version, chunk_no, text, vj in rows:
            score = sum(a * b for a, b in zip(vector, json.loads(vj)))
            scored.append({"chunk_id": chunk_id, "doc_id": doc_id, "source": src, "version": version,
                           "chunk_no": chunk_no, "text": text, "score": round(score, 4)})
        return sorted(scored, key=lambda r: -r["score"])[:top_k]


def get_embedder() -> Embedder:
    return HashEmbedder()


def get_store() -> VectorStore:
    return DuckDBStore()


def load_sources(env: str = "local") -> list[dict]:
    import duckdb
    con = duckdb.connect(DB, read_only=True)
    docs = load_tickets(con) + load_pdfs(DOCS)
    con.close()
    return docs


def chunk_documents(docs: list[dict]) -> list[dict]:
    """Chapter 12 chunking rule; each chunk keeps the document's id, source and version."""
    out = []
    for d in docs:
        for n, piece in enumerate(chunk(mask_pii(d["text"]))):
            out.append({"chunk_id": hashlib.sha256(f"{d['doc_id']}|{n}|{piece}".encode()).hexdigest()[:16],
                        "doc_id": d["doc_id"], "source": d["source"], "version": d["version"],
                        "chunk_no": n, "text": piece})
    return out


def write_quarantine(held: list[dict], env: str = "local") -> None:
    import duckdb
    from datetime import datetime, timezone
    con = duckdb.connect(DB)
    con.execute("CREATE SCHEMA IF NOT EXISTS quality")
    con.execute("""CREATE TABLE IF NOT EXISTS quality.quarantine (
        table_name VARCHAR, reason VARCHAR, row_payload JSON, quarantined_at TIMESTAMP)""")
    con.execute("DELETE FROM quality.quarantine WHERE table_name = 'gold.rag_chunks'")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for h in held:
        payload = json.dumps({k: h[k] for k in ("chunk_id", "doc_id", "source", "chunk_no")})
        con.execute("INSERT INTO quality.quarantine VALUES ('gold.rag_chunks', ?, ?, ?)",
                    [h["reason"][:200], payload, now])
    con.close()


def embed(chunks: list[dict]) -> list[dict]:
    embedder = get_embedder()
    for i in range(0, len(chunks), 64):                    # embed in small batches
        batch = chunks[i:i + 64]
        for r, v in zip(batch, embedder.embed([r["text"] for r in batch])):
            r["vector"] = v
    return chunks


def write_index(rows: list[dict], env: str = "local") -> None:
    get_store().upsert(rows)


# --------------------------------------------------------------------------- Chapter 18.3 run()
def run(env: str = "local", size: str = "small", **kwargs) -> dict:
    docs = load_sources(env)              # support tickets (bronze.bz_support_tickets) + help docs
    chunks = chunk_documents(docs)        # chunking rule from Chapter 12
    clean, held = split_suspicious(chunks)
    write_quarantine(held, env)           # quality.quarantine
    write_index(embed(clean), env)        # gold.rag_chunks
    return {"chunks": len(chunks), "indexed": len(clean), "quarantined": len(held)}


# --------------------------------------------------------------------------- the belge_ara tool (Chapter 12.4)
def belge_ara(query: str, top_k: int = 5, source: str = "all") -> dict:
    """Finds the most relevant chunks in the index. Read-only."""
    vector = get_embedder().embed([mask_pii(query)])[0]
    hits = get_store().search(vector, top_k=top_k, source=source)
    return {"query": query, "hits": [{k: h[k] for k in ("doc_id", "source", "version", "chunk_no", "text", "score")} for h in hits]}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--env", default="local", choices=["local", "databricks"])
    p.add_argument("--size", default="small")
    p.add_argument("--query", help="search the index instead of building it (belge_ara)")
    a = p.parse_args()
    if a.query:
        print(json.dumps(belge_ara(a.query), indent=2, ensure_ascii=False))
    else:
        result = run(a.env, a.size)
        print(json.dumps(result, indent=2))
        if result["quarantined"] < 1:      # T-18842 is in the data set on purpose (Chapter 18.3)
            raise SystemExit("quarantined = 0: the instruction scan did not run")
