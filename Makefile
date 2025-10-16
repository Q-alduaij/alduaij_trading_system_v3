PY=python
VENV=.venv

.PHONY: init db health lint fmt precommit

init:
	$(PY) -m venv $(VENV); . $(VENV)/Scripts/activate; pip install -r requirements.txt

db:
	$(PY) utils/db_init.py

health:
	$(PY) tools/api_key_health_check.py

lint:
	ruff check . && black --check . && isort --check-only .

fmt:
	black . && ruff check --fix . && isort .

precommit:
	pip install pre-commit && pre-commit install
