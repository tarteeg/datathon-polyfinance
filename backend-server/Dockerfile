FROM python:3.12-slim

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

USER app
EXPOSE 8000

# Bind on all interfaces. The container image never contains a .env file:
# STOCKSFEED_BASE_URL and other settings come from the service configuration.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
