FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    MODEL_PATH=/app/models/heart_disease_pipeline.joblib \
    MODEL_METADATA_PATH=/app/models/model_metadata.json

WORKDIR /app
COPY requirements-serving.txt ./
RUN python -m pip install --no-cache-dir -r requirements-serving.txt \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home app
COPY stages/__init__.py ./stages/__init__.py
COPY stages/stage_05_ci_cd/*.py ./stages/stage_05_ci_cd/
COPY stages/stage_06_model_containerization/*.py ./stages/stage_06_model_containerization/
COPY models/heart_disease_pipeline.joblib models/model_metadata.json ./models/

USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3)"
CMD ["python", "-m", "uvicorn", "stages.stage_06_model_containerization.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]