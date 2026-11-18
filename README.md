# AI-Assisted Data Engineering — meridian-data-book

**Türkçe** · [English below](#english)

*AI-Assisted Data Engineering* (Dr. Fatih Hattatoglu) kitabının kod ve veri deposu. Kitaptaki
bütün kodlar, 32 sentetik veri seti, script'ler, prompt'lar ve şablonlar burada.

> **Sentetik veri uyarısı:** Bu depodaki bütün veri setleri `data/generate_data.py` ile sentetik
> olarak üretilmiştir. Meridian Market ve Bazaarly kurgusal şirketlerdir. Verilerdeki adlar,
> e-posta adresleri, telefon numaraları, adresler ve işlemler hiçbir gerçek kişiye veya şirkete ait
> değildir. Gerçek bir kişi ya da kuruluşla herhangi bir benzerlik tesadüfidir.

## Hızlı başlangıç (ücretsiz yol, DuckDB)

```bash
git clone https://github.com/fhattat/meridian-data-book && cd meridian-data-book
pip install -r requirements.txt
python data/generate_data.py --size small --seed 2027 --out data/raw   # veya: make data (veri depoda hazır)
export PYTHONPATH=.                                                     # Windows PowerShell: $env:PYTHONPATH="."
python run_pipeline.py --env local --size small                         # veya: make all
```

Son satır şunu yazmalı: `[reconcile] status: pass`. Gold'daki net satış, `data/raw/control_totals.json`
ile 60 ayın 60'ında sentine kadar tutar. Aynı seed her çalışmada birebir aynı dosyaları üretir.

## Depoda ne var?

| Klasör / dosya | İçerik |
|---|---|
| `ch01_…` – `ch20_…` | Bölüm klasörleri (QR-01 … QR-20). Her birinde `README.md`, `BOOK_CODE.md` (bölümdeki bütün kod blokları, kitaptaki alt bölüm başlıklarıyla) ve çalıştırılabilir script'ler |
| `data/generate_data.py`, `data/raw/` | Veri üretici ve küçük sürüm veri seti (Ek F: MM01–MM11, BZ01–BZ13, OP01–OP08), `control_totals.json`, `answer_key.json` |
| `ref/` | Eşleme ve referans dosyaları: kanal kodları, test kayıtları, ürün eşlemesi, eyalet eş adları, `source_guide.yaml` |
| `contracts/`, `metrics/`, `governance/`, `products/`, `glossary.yaml` | Veri sözleşmeleri, metrik tanımları, sahiplik, veri ürünü kartı, iş sözlüğü |
| `lib/` | Ortak kütüphane: `io.py`, `reconcile.py`, `schema_gate.py`, `llm.py`, `log.py` |
| `prompts/` | Ek E: prompt ve skill kütüphanesi (E.0–E.21), ayrı dosyalar hâlinde (QR-Ek E) |
| `runbooks/`, `jobs/`, `databricks.yml`, `pipelines.yaml` | Runbook'lar, Databricks job'ları ve Asset Bundle, config tabanlı pipeline |
| `appendices/` | Ek D ve Ek F'deki kodlar |
| `tests/` | Kütüphane, veri seti ve pipeline testleri; Ek C mülakat SQL alıştırmaları |
| `REFERENCES.md` | Ek G kaynakçası, tıklanabilir bağlantılarla (QR-Ek G) |
| `CLAUDE.md`, `RULES.md`, `corrections.md`, `CODEOWNERS` | AI ile kod yazarken proje bağlamı, kurallar ve hata hafızası (Bölüm 2.3 ve 17.5) |

`make` komutları: `data`, `sample`, `profile`, `bronze`, `silver`, `quality`, `gold`, `checks`, `all`,
`serve`, `rag`, `metadata`, `rls`, `review`, `logs`, `test`.

## Notlar

- **Ortamlar:** Her script `--env local|databricks` alır. `local` sonuçları `data/meridian.duckdb` ve
  `data/layers/<katman>/<tablo>.parquet` içine yazar. Databricks yolu için Bölüm 3.1 ve 18.2.
- **"Şimdi" tarihi:** Veri 30 Haziran 2027'de biter. Tazelik ve gelecek tarih kuralları bilgisayarın
  saatini değil `MERIDIAN_AS_OF` değişkenini (varsayılan `2027-07-01 07:00:00`) kullanır.
- **AI çağrıları:** Kitap `lib/llm.py` içindeki `ask_llm()` fonksiyonunu bilerek boş bırakır; kendi
  asistanınıza bağlarsınız. İsterseniz hazır bağdaştırıcı: `pip install anthropic`, `MERIDIAN_LLM=anthropic`.
  AI gerektiren script'ler (agent'lar, text-to-SQL deneyi) bağlantı kurulmadan açık bir mesajla durur.
- **Kitaptan farklar:** Kitapta "(shortened)" diye gösterilen script'lerin tam hâli buradadır. Depoya
  eklenen satırlar kodda `repo:` notuyla işaretlidir.
- **CI:** Her push'ta GitHub Actions bütün pipeline'ı çalıştırır ve testleri koşar (`.github/workflows/ci.yml`).

## Lisans

Kod: MIT (`LICENSE`). Veri: CC BY 4.0 (`LICENSE-DATA.md`). Kitap metni bu depoda değildir; tüm hakları saklıdır.

---

<a id="english"></a>
# English

Code and data repository of the book *AI-Assisted Data Engineering* by Dr. Fatih Hattatoglu: every
code block of the book, 32 synthetic data sets, scripts, prompts and templates.

> **Synthetic data notice:** All datasets in this repository were synthetically generated with
> `data/generate_data.py`. Meridian Market and Bazaarly are fictional companies. Names, email
> addresses, phone numbers, addresses and transactions in the data do not belong to any real person or
> company. Any resemblance to real persons or organizations is coincidental.

## Quick start (free path, DuckDB)

```bash
git clone https://github.com/fhattat/meridian-data-book && cd meridian-data-book
pip install -r requirements.txt
export PYTHONPATH=.
python run_pipeline.py --env local --size small        # or: make all
```

The last line should read `[reconcile] status: pass`: net sales in gold match
`data/raw/control_totals.json` to the cent in all 60 company-months.

Chapter folders `ch01_…` to `ch20_…` hold a `README.md`, `BOOK_CODE.md` (every code block of the chapter
in book order, under the book's Turkish section headings) and the runnable scripts. `prompts/` is the
prompt and skill library of Appendix E; `REFERENCES.md` is the bibliography of Appendix G.

Code: MIT. Data: CC BY 4.0. The book text is not part of this repository.
