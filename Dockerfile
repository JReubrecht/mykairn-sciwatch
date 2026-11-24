FROM python:3.12-slim

LABEL org.opencontainers.image.title="myKairn SciWatch"
LABEL org.opencontainers.image.description="Moteur modulaire d'audit et de veille scientifique automatisée 6D"
LABEL org.opencontainers.image.authors="Jérôme Reubrecht <contact@mykairn.fr>"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    SCIWATCH_HOST=0.0.0.0 \
    SCIWATCH_PORT=8095 \
    SCIWATCH_DB_PATH=/app/data/sciwatch.db \
    SCIWATCH_PROFILES_DIR=/app/profiles \
    SCIWATCH_REPORTS_DIR=/app/reports

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
COPY profiles/ ./profiles/

RUN pip install --no-cache-dir -e . && \
    mkdir -p /app/data /app/reports && \
    useradd -m -u 1000 sciwatch && \
    chown -R sciwatch:sciwatch /app

USER sciwatch

EXPOSE 8095

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8095/api/health', timeout=4)" || exit 1

CMD ["python3", "-m", "mykairn_sciwatch", "serve", "--host", "0.0.0.0", "--port", "8095"]
