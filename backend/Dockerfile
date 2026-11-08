# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

COPY app ./app

RUN groupadd --system app && useradd --system --gid app app \
    && mkdir -p /app/data && chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; r=urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3); sys.exit(0 if r.status == 200 else 1)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
