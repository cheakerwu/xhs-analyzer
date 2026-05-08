FROM mcr.microsoft.com/playwright/python:v1.59.0-noble

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONUTF8=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Use Chinese pip mirror
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

# Install dependencies first (cached unless requirements change)
COPY MediaCrawler-main/requirements.txt /tmp/mediacrawler-requirements.txt
COPY requirements-app.txt /tmp/requirements-app.txt

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r /tmp/mediacrawler-requirements.txt \
    && python -m pip install --no-cache-dir -r /tmp/requirements-app.txt \
    && rm /tmp/mediacrawler-requirements.txt /tmp/requirements-app.txt

# Create non-root user before copying app code
RUN getent group 1001 > /dev/null || groupadd -g 1001 appgroup \
    && getent passwd 1001 > /dev/null || useradd -u 1001 -g 1001 -m -s /bin/bash appuser \
    && mkdir -p /app/data/runs /app/data/history \
    && chown -R 1001:1001 /app

# Copy application code
COPY --chown=1001:1001 app ./app
COPY --chown=1001:1001 web ./web
COPY --chown=1001:1001 MediaCrawler-main ./MediaCrawler-main

USER 1001

EXPOSE 8088

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8088"]
