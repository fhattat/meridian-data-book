# A: raw bronze schema only
python ch11_modeling/text_to_sql_eval.py --env local --layer bronze

# B: bronze + source guide (ref/source_guide.yaml; started in Chapter 7, completed in Chapter 14)
python ch11_modeling/text_to_sql_eval.py --env local --layer bronze --guide ref/source_guide.yaml

# C: gold layer + grain and metric definitions (ch11_modeling/gold_grain.md)
python ch11_modeling/text_to_sql_eval.py --env local --layer gold
