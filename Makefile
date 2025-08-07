.PHONY: help install test lint run docker-build docker-run clean

help:		## Show this help
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:	## Install dependencies
	pip install -r requirements.txt

test:		## Run tests
	pytest

test-cov:	## Run tests with coverage
	pytest --cov=. --cov-report=html

lint:		## Run linting (placeholder for future linting tools)
	@echo "Linting (add flake8/black/isort when ready)"

run:		## Run the application
	python app.py

run-prod:	## Run with gunicorn (production)
	gunicorn --bind 0.0.0.0:5000 --workers 4 app:app

docker-build:	## Build Docker image
	docker build -t ke-wp-mapping .

docker-run:	## Run Docker container
	docker run -p 5000:5000 --env-file .env ke-wp-mapping

docker-compose-up:	## Start with docker-compose
	docker-compose up -d

docker-compose-down:	## Stop docker-compose
	docker-compose down

migrate:	## Run database migration
	python migrate_csv_to_db.py

clean:		## Clean up generated files
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

setup-dev:	## Setup development environment
	python -m venv venv
	source venv/bin/activate && pip install -r requirements.txt
	cp .env.example .env
	@echo "Don't forget to edit .env with your actual values!"

backup-db:	## Backup the database
	cp ke_wp_mapping.db ke_wp_mapping.db.backup.$(shell date +%Y%m%d_%H%M%S)

restore-db:	## Restore database from backup (requires BACKUP_FILE variable)
	@if [ -z "$(BACKUP_FILE)" ]; then echo "Usage: make restore-db BACKUP_FILE=backup.db"; exit 1; fi
	cp $(BACKUP_FILE) ke_wp_mapping.db