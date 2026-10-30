.PHONY: up down logs build venv test lint
up:     ; docker compose up -d --build
down:   ; docker compose down
logs:   ; docker compose logs -f bot
build:  ; docker compose build
venv:   ; python3 -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -r requirements-dev.txt
test:   ; .venv/bin/pytest
lint:   ; .venv/bin/ruff check .
