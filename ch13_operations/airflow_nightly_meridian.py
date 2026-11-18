import pendulum
from airflow import DAG                           # recommended in Airflow 3: from airflow.sdk import DAG
from airflow.operators.bash import BashOperator  # in Airflow 3: airflow.providers.standard.operators.bash

with DAG("nightly_meridian", schedule="0 2 * * *",
         start_date=pendulum.datetime(2027, 1, 1, tz="America/New_York"), catchup=False,
         default_args={"retries": 2}) as dag:
    ingest = BashOperator(task_id="ingest", bash_command="python ch08_ingestion/ingest_to_bronze.py --env local")
    silver = BashOperator(task_id="clean_silver", bash_command="python ch09_medallion/clean_silver.py --env local")
    gate = BashOperator(task_id="quality_gate", bash_command="python ch10_quality/quality_checks.py --env local")
    gold = BashOperator(task_id="build_gold", bash_command="python ch11_modeling/build_gold.py --env local")
    checks = BashOperator(task_id="model_checks", bash_command="python ch11_modeling/model_checks.py --env local")
    ingest >> silver >> gate >> gold >> checks
