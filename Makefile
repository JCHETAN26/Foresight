.PHONY: up down logs test lint fmt tf-validate

up:  ## Start the local dev stack
	docker compose up -d --build

down:  ## Stop the stack and remove volumes
	docker compose down -v

logs:  ## Tail all service logs
	docker compose logs -f

test:  ## Run ingestion test suite
	cd services/ingestion && pytest -q

lint:  ## Lint + type-check ingestion
	cd services/ingestion && ruff check . && mypy app

fmt:  ## Auto-format
	cd services/ingestion && ruff check --fix . && ruff format .
	cd infra/terraform && terraform fmt -recursive

tf-validate:  ## Validate Terraform
	cd infra/terraform && terraform init -backend=false && terraform validate
