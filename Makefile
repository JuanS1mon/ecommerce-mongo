# Makefile with common dev tasks
.PHONY: install build up down test fmt

install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt

build:
	docker compose -f docker-compose.dev.yml build --no-cache

up:
	docker compose -f docker-compose.dev.yml up --build -d

down:
	docker compose -f docker-compose.dev.yml down

test:
	# Run unit tests (exclude selenium/playwright heavy tests)
	docker compose -f docker-compose.dev.yml exec -T -e PYTHONPATH=/app app pytest -q tests -m "not selenium and not playwright"

lint:
	# Placeholder for linters (flake8, ruff, etc.)
	@echo "Run ruff/flake8 here"
