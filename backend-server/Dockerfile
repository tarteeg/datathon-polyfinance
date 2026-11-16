ARG PYTHON_IMAGE=python:3.12-slim
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STOCKSFEED_BASE_URL=https://stockfeedai-server-283151671335.us-central1.run.app

# Unprivileged user with a writable home (yfinance keeps a small cache there).
RUN useradd --create-home --uid 10001 app
WORKDIR /srv

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY data ./data

# The pre-fetched fixtures above are read-only, but RiskRipple also live-fetches and
# caches filings for any ticker not already in data/fixtures (fetch_and_cache_10k).
# /srv is root-owned, so the unprivileged `app` user below can't create data/ itself --
# confirmed live: a first-ever scan for a ticker outside the pre-fetched set crashed
# the whole alert scan with "PermissionError: [Errno 13] Permission denied: '/srv/data'".
RUN chown -R app:app ./data

USER app
EXPOSE 8000

# Bind on all interfaces. The container image never contains a .env file:
# STOCKSFEED_BASE_URL and other settings come from the service configuration.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
