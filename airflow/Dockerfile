FROM golang:1.21-alpine AS pipeline-build
WORKDIR /src
COPY pipeline/go.mod pipeline/go.sum* ./
RUN go mod download
COPY pipeline/ .
RUN go build -o /out/pipeline .

FROM apache/airflow:2.7.3-python3.11

USER root
COPY --from=pipeline-build /out/pipeline /opt/airflow/pipeline/pipeline
COPY pipeline/config /opt/airflow/pipeline/config
COPY dbt /opt/airflow/dbt
RUN chmod +x /opt/airflow/pipeline/pipeline && mkdir -p /opt/airflow/pipeline/state /opt/airflow/dbt/target && chown -R airflow: /opt/airflow/pipeline /opt/airflow/dbt

USER airflow
COPY airflow/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
