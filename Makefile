# Meridian data book - shortcuts (Appendix F). Run from the repository root.
PY ?= python
export PYTHONPATH := .

.PHONY: data sample profile bronze silver quality gold checks all serve rag metadata rls review logs test clean

data:            ## Chapter 3: generate the synthetic data set (small)
	$(PY) data/generate_data.py --size small --seed 2027 --out data/raw

sample:          ## Chapter 3: first tables in DuckDB (raw schema)
	$(PY) ch03_toolkit/load_sample.py

profile:         ## Chapter 7
	$(PY) ch07_profiling/profile_source.py --env local

bronze:          ## Chapter 8
	$(PY) ch08_ingestion/ingest_to_bronze.py --env local --source all

silver:          ## Chapter 9
	$(PY) ch09_medallion/clean_silver.py --env local

quality:         ## Chapter 10 (exit 1 on a critical failure)
	$(PY) ch10_quality/quality_checks.py --env local

gold:            ## Chapter 11
	$(PY) ch11_modeling/build_gold.py --env local

checks:          ## Chapter 11
	$(PY) ch11_modeling/model_checks.py --env local

all:             ## Chapter 18: the whole night in one command
	$(PY) run_pipeline.py --env local --size small

serve:           ## Chapter 12: ML features
	$(PY) ch12_serving/export_features.py --env local

rag:             ## Chapter 12/17/18: RAG index with the injection scan
	$(PY) ch12_serving/build_rag_index.py --env local

metadata:        ## Chapter 14
	$(PY) ch14_governance/extract_metadata.py --env local --schema gold

rls:             ## Chapter 14
	$(PY) ch14_governance/rls_test.py

review:          ## Chapter 13
	$(PY) ch13_operations/big_review.py

logs:            ## Chapter 13: the 15 April 2027 incident
	$(PY) ch13_operations/check_pipeline_logs.py data/raw/ops/pipeline_logs/2027-04-15.log --no-append

test:
	$(PY) -m pytest -q tests

clean:
	rm -rf data/layers data/meridian.duckdb data/meridian.duckdb.wal reports/* metadata/*.yaml metadata/*.html metadata/*.mmd site
