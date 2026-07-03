# bookworm(Debian 12) 固定：trixie 下 playwright --with-deps 引用了已废弃字体包会失败
FROM python:3.12-slim-bookworm

WORKDIR /app

# System deps kept minimal; psycopg[binary] ships its own libpq.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# M1 Playwright 源：装无头 Chromium + 系统依赖（JS 渲染站抓取用）
RUN python -m playwright install --with-deps chromium

COPY app ./app
COPY alembic.ini .
COPY migrations ./migrations

EXPOSE 8000

# --reload for dev; app dir is bind-mounted via docker-compose so edits hot-reload.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
