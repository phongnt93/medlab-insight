from __future__ import annotations

import secrets

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import tools
from .config import Settings
from .kube import KubectlError

TOOL_SCHEMA = [
    {
        "name": "k8s_get",
        "description": "Read Kubernetes objects (pods, deployments, services, events, ...) as JSON",
        "endpoint": "/tools/k8s_get",
        "params": {
            "namespace": "medlab|argocd|jenkins|agents",
            "resource": "kind",
            "name": "optional",
        },
    },
    {
        "name": "k8s_describe",
        "description": "Describe one Kubernetes object",
        "endpoint": "/tools/k8s_describe",
        "params": {
            "namespace": "medlab|argocd|jenkins|agents",
            "resource": "kind",
            "name": "required",
        },
    },
    {
        "name": "k8s_logs",
        "description": "Read the last N lines of a pod log (max 500)",
        "endpoint": "/tools/k8s_logs",
        "params": {"namespace": "namespace", "pod": "pod name", "container": "optional"},
    },
    {
        "name": "argocd_app",
        "description": "Read an ArgoCD Application status (sync/health)",
        "endpoint": "/tools/argocd_app",
        "params": {"name": "application name"},
    },
    {
        "name": "jenkins_status",
        "description": "Read Jenkins job/build status",
        "endpoint": "/tools/jenkins_status",
        "params": {"job": "job name", "build": "optional build number"},
    },
    {
        "name": "http_health",
        "description": "Check an allowlisted service health endpoint",
        "endpoint": "/tools/http_health",
        "params": {
            "host": "allowlisted host",
            "path": "/_stcore/health",
            "scheme": "https|http",
            "insecure": "skip TLS verify (internal hosts)",
        },
    },
]


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    bearer = HTTPBearer(auto_error=False)

    app = FastAPI(
        title="MedLab agent tool gateway",
        description="Read-only DevOps tools for AI agents. No write operations by design.",
        version="0.1.0",
    )

    def require_token(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),  # noqa: B008
    ) -> None:
        if not app_settings.gateway_token:
            raise HTTPException(status_code=503, detail="gateway token is not configured")
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="missing bearer token")
        if not secrets.compare_digest(credentials.credentials, app_settings.gateway_token):
            raise HTTPException(status_code=401, detail="invalid token")

    @app.exception_handler(KubectlError)
    def _kubectl_error(_: Request, exc: KubectlError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"ok": False, "error": str(exc)})

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/tools", dependencies=[Depends(require_token)])
    def list_tools() -> dict[str, object]:
        return {"tools": TOOL_SCHEMA}

    @app.post("/tools/k8s_get", dependencies=[Depends(require_token)])
    def tool_k8s_get(payload: tools.K8sGetRequest) -> dict[str, object]:
        return tools.k8s_get(payload, app_settings.max_output_chars)

    @app.post("/tools/k8s_describe", dependencies=[Depends(require_token)])
    def tool_k8s_describe(payload: tools.K8sDescribeRequest) -> dict[str, object]:
        return tools.k8s_describe(payload, app_settings.max_output_chars)

    @app.post("/tools/k8s_logs", dependencies=[Depends(require_token)])
    def tool_k8s_logs(payload: tools.K8sLogsRequest) -> dict[str, object]:
        return tools.k8s_logs(payload, app_settings.max_output_chars)

    @app.post("/tools/argocd_app", dependencies=[Depends(require_token)])
    def tool_argocd_app(payload: tools.ArgoAppRequest) -> dict[str, object]:
        return tools.argocd_app(payload, app_settings.max_output_chars)

    @app.post("/tools/jenkins_status", dependencies=[Depends(require_token)])
    def tool_jenkins_status(payload: tools.JenkinsStatusRequest) -> dict[str, object]:
        try:
            return tools.jenkins_status(
                payload,
                url=app_settings.jenkins_url,
                user=app_settings.jenkins_user,
                password=app_settings.jenkins_password,
                limit=app_settings.max_output_chars,
            )
        except LookupError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/tools/http_health", dependencies=[Depends(require_token)])
    def tool_http_health(payload: tools.HttpHealthRequest) -> dict[str, object]:
        try:
            return tools.http_health(payload, allowed_hosts=app_settings.allowed_health_hosts)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("gateway.app:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
