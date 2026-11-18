# Ek D — Hata günlüğü

## Code from the book

Every code block of this chapter, in book order, under the book's section headings (Turkish, as printed).
Runnable files are in this folder; for scripts printed as "(shortened)" the full version is the file here.
Bu dosya bölümdeki bütün kod bloklarını kitaptaki sırasıyla ve alt bölüm başlıklarıyla verir.

### Kendi hata günlüğünüz için şablon

> Bölüm 13’teki alanları kendi ekibinizde de kullanabilirsiniz. Kök nedeni ve kalıcı çözümü her zaman bir insan doldurur; check_pipeline_logs.py yalnızca açık bir kayıt ekler.

**Code Ek D.1**

```yaml
- id: INC-YYYYMMDD-NN          # date + running number in the log (check_pipeline_logs.py: len(incidents) + 1)
  opened_at: 2027-01-01T00:00:00Z
  closed_at: null
  step: <pipeline step>
  source: <source table or file>
  class: transient | schema | data | security | unknown
  summary: <one sentence: what happened?>
  symptom: <first symptom seen: a log line or an error message>
  root_cause: null              # filled in by a human
  temp_fix: <what did we do today?>
  permanent_fix: <what changed so that it does not happen again?>
  keywords: [<3-5 words for search>]
  related: [<similar records>]
  impact: <which consumer, how much delay, SLO/SLA status>
  status: open | monitoring | closed
```
