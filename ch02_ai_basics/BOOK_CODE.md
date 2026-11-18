# Bölüm 2 — AI ile çalışmanın temelleri

## Code from the book

Every code block of this chapter, in book order, under the book's section headings (Turkish, as printed).
Runnable files are in this folder; for scripts printed as "(shortened)" the full version is the file here.
Bu dosya bölümdeki bütün kod bloklarını kitaptaki sırasıyla ve alt bölüm başlıklarıyla verir.

### 2.3 İyi prompt ve bağlam: proje dosyası, örnekler, kurallar

> Proje bağlam dosyası. Her sohbette aynı şeyleri tekrar anlatmak yerine, projenin köküne kısa bir “işe alışma belgesi” koyun. Kod asistanları bu dosyayı her oturumun başında okur. Araçtan araca adı değişir (CLAUDE.md, AGENTS.md ya da aracın proje…

**Code 2.1**

```markdown
# Meridian Data Platform — project context

## What we are building
We combine Meridian Market (48 stores, US) and Bazaarly (online marketplace) data
on Databricks in bronze/silver/gold layers.

## Folders
- data/raw: source files, NEVER modify
- ref/: reference and seed files (code mappings, test records, source guide)
- chXX_*/: chapter scripts (Python, English names)
- tests/: a small-data test for every script

## Rules
- Never write to raw data; output goes only to bronze/silver/gold.
- Never change a failing test; fix the code.
- One change touches one file and at most ~200 lines.
- Do not invent column meanings or code mappings; if the source document does not say, leave it empty and ask.
- Never write personal data columns (email, phone, birth date) to output or logs.

## Known traps
- Meridian POS: ';' delimiter, Windows-1252, store local time.
- Bazaarly: UTC; channel_code meanings are in source_system_guide.pdf.
```
