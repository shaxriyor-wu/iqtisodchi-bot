FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN useradd --system --uid 10001 --no-create-home bot
COPY --chown=bot:bot app ./app
COPY --chown=bot:bot migrations ./migrations
COPY --chown=bot:bot knowledge ./knowledge
COPY --chown=bot:bot alembic.ini .
USER bot

CMD ["python", "-m", "app"]
