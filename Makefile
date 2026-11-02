PY := uv run
IMAGE ?= medlab-insight:local

.PHONY: install train train-fast run test lint fmt docker-build docker-run k8s-apply k8s-secret k8s-forward k8s-status clean

install:
	uv sync --extra dev --extra train

train:
	$(PY) python -m training.train

train-fast:
	$(PY) python -m training.train --no-mlflow

run:
	$(PY) streamlit run app/streamlit_app.py --server.port 8601

test:
	$(PY) pytest --cov --cov-report=term-missing

lint:
	$(PY) ruff check src app training tests
	$(PY) ruff format --check src app training tests

fmt:
	$(PY) ruff check --fix src app training tests
	$(PY) ruff format src app training tests

docker-build:
	docker build -t $(IMAGE) .

docker-run:
	docker run --rm -p 8601:8501 --env-file .env $(IMAGE)

k8s-apply:
	kubectl apply -k k8s/overlays/local

k8s-secret:
	@test -n "$(GEMINI_API_KEY)" || (echo "GEMINI_API_KEY is required" && exit 1)
	kubectl -n medlab create secret generic medlab-secrets \
		--from-literal=GEMINI_API_KEY="$(GEMINI_API_KEY)" \
		--dry-run=client -o yaml | kubectl apply -f -

k8s-forward:
	kubectl -n medlab port-forward svc/medlab-insight 8601:80

k8s-status:
	kubectl -n medlab get pods,svc,hpa,ingress

clean:
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage
