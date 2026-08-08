from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

DBT_PROJECT_DIR = "/opt/airflow/dbt"
DBT_PROFILES_DIR = "/opt/airflow/dbt"
PIPELINE_BIN = "/opt/airflow/pipeline/pipeline"
PIPELINE_CONFIG = "/opt/airflow/pipeline/config/tenants.json"
PIPELINE_STATE_DIR = "/opt/airflow/pipeline/state"

default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="parkee_elt_dag",
    description="Parkee POS multi-tenant ELT: Golang extract/load -> dbt staging -> dbt mart",
    default_args=default_args,
    schedule_interval="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["parkee", "elt"],
) as dag:

    extract_load_golang_binary = BashOperator(
        task_id="extract_load_golang_binary",
        bash_command=f"{PIPELINE_BIN} --config {PIPELINE_CONFIG} --state-dir {PIPELINE_STATE_DIR}",
    )

    dbt_run_staging = BashOperator(
        task_id="dbt_run_staging",
        bash_command=(
            f"dbt run --select staging.* "
            f"--project-dir {DBT_PROJECT_DIR} --profiles-dir {DBT_PROFILES_DIR}"
        ),
    )

    dbt_test_staging = BashOperator(
        task_id="dbt_test_staging",
        bash_command=(
            f"dbt test --select staging.* "
            f"--project-dir {DBT_PROJECT_DIR} --profiles-dir {DBT_PROFILES_DIR}"
        ),
    )

    dbt_run_mart = BashOperator(
        task_id="dbt_run_mart",
        bash_command=(
            f"dbt run --select marts.* "
            f"--project-dir {DBT_PROJECT_DIR} --profiles-dir {DBT_PROFILES_DIR}"
        ),
    )

    dbt_test_mart = BashOperator(
        task_id="dbt_test_mart",
        bash_command=(
            f"dbt test --select marts.* "
            f"--project-dir {DBT_PROJECT_DIR} --profiles-dir {DBT_PROFILES_DIR}"
        ),
    )

    dbt_docs_generate = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=(
            f"dbt docs generate "
            f"--project-dir {DBT_PROJECT_DIR} --profiles-dir {DBT_PROFILES_DIR}"
        ),
    )

    extract_load_golang_binary >> dbt_run_staging >> dbt_test_staging >> dbt_run_mart >> dbt_test_mart >> dbt_docs_generate
