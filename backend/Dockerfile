FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Homework AI QR reader: installed from the bundled wheels (no internet needed - see wheels/README.md).
# A separate step after requirements.txt, so it never invalidates the cached package install above.
COPY wheels/ /tmp/wheels/
RUN pip install --no-index --find-links /tmp/wheels zxing-cpp==3.1.1 pillow==13.0.0     && rm -rf /tmp/wheels

COPY . .

RUN addgroup --system app \
    && adduser --system --ingroup app app \
    && chown -R app:app /app

USER app

EXPOSE 8000

ENV APP_PORT=8000 \
    FLASK_HOST=0.0.0.0 \
    FLASK_PORT=8000 \
    FLASK_DEBUG=False

CMD ["sh", "-c", "${BACKEND_START_CMD:-python run.py}"]
