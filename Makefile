PY := uv run
IMAGE ?= medlab-insight:local
DOCKER_IMAGE ?= nguyenphong8852/medlab-insight
TAG ?= dev
GATEWAY_IMAGE ?= medlab-gateway:local

.PHONY: install train train-fast run test lint fmt docker-build docker-run k8s-apply k8s-secret k8s-forward k8s-status clean \
	 dagger-check dagger-build dagger-push dagger-bump dagger-pipeline \
	agent-test agent-lint agent-image agent-deploy agent-forward agent-rbac-check

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

# ---- Dagger CI (parallel to Jenkins; see ci/) ----
dagger-check:
	dagger call check --source=.

dagger-build:
	dagger call build --source=. --tag=$(TAG)

dagger-push:
	@test -n "$$DOCKER_USERNAME" || (echo "DOCKER_USERNAME is required" && exit 1)
	@test -n "$$DOCKER_PASSWORD" || (echo "DOCKER_PASSWORD is required" && exit 1)
	dagger call build-push --source=. --tag=$(TAG) \
		--username=env:DOCKER_USERNAME --password=env:DOCKER_PASSWORD

dagger-bump:
	@test -n "$$GITHUB_TOKEN" || (echo "GITHUB_TOKEN is required" && exit 1)
	dagger call bump-manifest --tag=$(TAG) --token=env:GITHUB_TOKEN

# Full handoff: verify -> publish -> commit manifest -> ArgoCD rolls out.
dagger-pipeline: dagger-check dagger-push dagger-bump

# ---- AI agent tool gateway (read-only) ----
agent-test:
	cd agents/gateway && uv sync --extra dev -q && uv run pytest

agent-lint:
	cd agents/gateway && uv run ruff check src tests && uv run ruff format --check src tests

agent-image:
	docker build -t $(GATEWAY_IMAGE) agents/gateway

agent-deploy:
	kubectl apply -k k8s/agents
	kubectl -n agents rollout status deploy/agent-gateway --timeout=120s

agent-forward:
	kubectl -n agents port-forward svc/agent-gateway 8700:80

agent-rbac-check:
	@kubectl auth can-i delete pods -n medlab --as=system:serviceaccount:agents:agent-gateway
	@kubectl auth can-i get pods/log -n medlab --as=system:serviceaccount:agents:agent-gateway

clean:
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage
