FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONUTF8=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install dependencies first (cached unless requirements change)
COPY MediaCrawler-main/requirements.txt /tmp/mediacrawler-requirements.txt
COPY requirements-app.txt /tmp/requirements-app.txt

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r /tmp/mediacrawler-requirements.txt \
    && python -m pip install --no-cache-dir -r /tmp/requirements-app.txt \
    && rm /tmp/mediacrawler-requirements.txt /tmp/requirements-app.txt

# Create non-root user before copying app code
RUN groupadd -g 1001 appgroup \
    && useradd -u 1001 -g appgroup -m -s /bin/bash appuser \
    && mkdir -p /app/data/runs /app/data/history \
    && chown -R appuser:appgroup /app

# Copy application code
COPY --chown=appuser:appgroup app ./app
COPY --chown=appuser:appgroup web ./web
COPY --chown=appuser:appgroup MediaCrawler-main ./MediaCrawler-main

USER appuser

EXPOSE 8088

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8088"]
