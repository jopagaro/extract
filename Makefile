.PHONY: install dev api web desktop test lint

install:
	pip install -e ".[dev]"
	pnpm install

dev:
	uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

api:
	uvicorn api.main:app --host 127.0.0.1 --port 8000

web:
	pnpm --filter web dev

desktop:
	pnpm --filter desktop tauri dev

test:
	pytest

lint:
	ruff check . && mypy engine/ api/
