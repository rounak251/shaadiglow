# ShaadiGlow: FastAPI + static mobile web app. Small image, non-root, Render-ready.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SG_DATA_DIR=/tmp/shaadiglow \
    PORT=10000

WORKDIR /srv
COPY requirements.txt .
RUN pip install -r requirements.txt && useradd --create-home --uid 10001 app

COPY app ./app
COPY cache_seed ./cache_seed

USER app
EXPOSE 10000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"10000\")}/api/health',timeout=4)"
# YOUCAM_API_KEY is injected at runtime (Render secret); without it the app runs in demo mode.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
