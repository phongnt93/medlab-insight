# AI DevOps agent — read-only tool gateway

Phase A of the Kubiya/Slack integration. The gateway exposes a small,
allowlisted set of **read-only** DevOps tools over HTTP so an AI agent
(Kubiya, later) can answer questions about this cluster without ever getting
write access.

## Architecture

```
Slack  ->  Kubiya Cloud  ->  agent-gateway (k8s ns agents)
                                 |-- kubectl get/describe/logs   (Role: get/list/watch)
                                 |-- ArgoCD Application status   (Role in argocd)
                                 |-- Jenkins job status          (HTTP, optional)
                                 '-- allowlisted health checks
```

Dagger stays the **CI layer**; the gateway is diagnostic tooling. Neither
replaces Jenkins (orchestration) or ArgoCD (GitOps deploy).

## Tools

| Tool | What it does | Guardrails |
|---|---|---|
| `k8s_get` | Read objects as JSON | namespaces `medlab/argocd/jenkins/agents`; no secrets/exec |
| `k8s_describe` | Describe one object | name regex, no shell |
| `k8s_logs` | Tail pod logs | max 500 lines, output capped |
| `argocd_app` | Application sync/health | CR read via kubectl |
| `jenkins_status` | Build status | optional, needs `JENKINS_URL` + creds |
| `http_health` | GET health endpoint | host allowlist; `scheme` https/http; `insecure` skips TLS verify for internal self-signed hosts |

All responses are truncated at `MAX_OUTPUT_CHARS` (default 20 000).

## Run locally

```bash
cd agents/gateway
uv sync --extra dev
GATEWAY_TOKEN=dev-token uv run uvicorn gateway.app:app --port 8700

curl -s -H "Authorization: Bearer dev-token" localhost:8700/tools
```

If kubectl on the host points at OrbStack, the tools work straight away.

## Deploy to OrbStack k8s

```bash
# 1. build image into OrbStack's docker store (k8s shares it)
docker build -t medlab-gateway:local agents/gateway

# 2. secret (never committed)
TOKEN=$(openssl rand -hex 32)
kubectl create secret generic agent-gateway-secret -n agents \
  --from-literal=token="$TOKEN" --dry-run=client -o yaml | kubectl apply -f -

# 3. deploy
kubectl apply -k k8s/agents
kubectl -n agents rollout status deploy/agent-gateway

# 4. smoke via port-forward
kubectl -n agents port-forward svc/agent-gateway 8700:80
curl -s -H "Authorization: Bearer $TOKEN" localhost:8700/tools
```

## Verify RBAC is read-only

```bash
kubectl auth can-i delete pods -n medlab \
  --as=system:serviceaccount:agents:agent-gateway   # -> no
kubectl auth can-i get pods/log -n medlab \
  --as=system:serviceaccount:agents:agent-gateway   # -> yes
kubectl auth can-i get secrets -n medlab \
  --as=system:serviceaccount:agents:agent-gateway   # -> no
```

Notes from the OrbStack deployment:

- `imagePullPolicy: IfNotPresent` + the moving `:local` tag means kubelet can
  keep serving the old build; after rebuilding, run
  `kubectl -n agents rollout restart deploy/agent-gateway`.
- The `agent-gateway-ingress` NetworkPolicy only admits traffic from the
  ingress-nginx namespace, so in-cluster calls to
  `agent-gateway.agents.svc.cluster.local` time out by design. Add an
  explicit `from` rule before Phase B connects Kubiya Cloud.
- OrbStack ingress uses a self-signed certificate; call
  `http_health` with `"insecure": true` for `medlab.k8s.orb.local`.

## Dagger CI (parallel to Jenkins)

`ci/` is a Dagger module (Python SDK, `Ci` class) that verifies code and can
publish the image + bump the GitOps manifest. Jenkins remains the orchestrator
and ArgoCD remains the deployer.

```bash
dagger call check --source=.                       # ruff + pytest in clean container
dagger call build --source=. --tag=dev             # build image, prints ID

DOCKER_USERNAME=... DOCKER_PASSWORD=... \
  dagger call build-push --source=. --tag=dev \
  --username=env:DOCKER_USERNAME --password=env:DOCKER_PASSWORD

GITHUB_TOKEN=... dagger call bump-manifest --tag=dev --token=env:GITHUB_TOKEN

make dagger-pipeline   # check -> build-push -> bump-manifest
```

`bump-manifest` clones the repo, rewrites `k8s/base/deployment.yaml`, commits
as `dagger-ci` and pushes, which is the same GitOps hop Jenkins does.

## Phase B — Kubiya + Slack (later)

1. Create the Kubiya account, copy `KUBIYA_API_KEY`.
2. Register the tools: `GET /tools` returns the schema; point each tool at
   `http(s)://<gateway>/tools/<name>` with the bearer token.
3. Create the Slack app from `agents/slack/manifest.json` (bot scopes:
   `chat:write`, `app_mentions:read`, `commands`), install to the workspace,
   and connect it in Kubiya. Example tool payloads:

   ```json
   {"namespace": "medlab", "resource": "pods", "label_selector": "app=medlab-insight"}
   {"namespace": "medlab", "resource": "deployments"}
   {"namespace": "medlab", "pod": "<pod-name>", "tail_lines": 100}
   {"name": "medlab-insight"}
   {"job": "medlab-insight"}
   {"host": "medlab.k8s.orb.local", "path": "/", "insecure": true}
   ```
4. Expose the gateway to Kubiya Cloud only via ingress + IP allowlist or a
   Cloudflare Tunnel — never publicly without the bearer token.
5. Ask the agent: "pod nào đang lỗi trong namespace medlab?",
   "deployment đang chạy image gì?", "ArgoCD app medlab-insight đã sync chưa?",
   "Jenkins build gần nhất thế nào?".
