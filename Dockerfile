FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONUTF8=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY MediaCrawler-main/requirements.txt /tmp/mediacrawler-requirements.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/mediacrawler-requirements.txt \
    && python -m pip install "fastapi>=0.115" "uvicorn>=0.32" "pydantic>=2.10"

COPY app ./app
COPY web ./web
COPY MediaCrawler-main ./MediaCrawler-main

RUN mkdir -p /app/data/runs /app/data/history

EXPOSE 8088

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8088"]
