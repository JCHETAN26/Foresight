FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
COPY foresight_kpi ./foresight_kpi
RUN pip install --upgrade pip && pip install .

RUN useradd --create-home --uid 10003 appuser
USER appuser

CMD ["python", "-m", "foresight_kpi"]
