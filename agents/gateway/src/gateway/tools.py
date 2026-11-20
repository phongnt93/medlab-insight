from __future__ import annotations

import base64
import json
import ssl
import urllib.error
import urllib.request
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .config import (
    ALLOWED_NAMESPACES,
    ALLOWED_RESOURCES,
    ARGOCD_RESOURCE,
    CONTAINER_PATTERN,
    JOB_PATTERN,
    NAME_PATTERN,
)
from .kube import run_kubectl

_ALLOWED_NAMESPACE_LIST = sorted(ALLOWED_NAMESPACES)
_ALLOWED_RESOURCE_LIST = sorted(ALLOWED_RESOURCES)


class K8sGetRequest(BaseModel):
    namespace: Literal["medlab", "argocd", "jenkins", "agents"]
    resource: str = Field(description=f"One of: {', '.join(_ALLOWED_RESOURCE_LIST)}")
    name: str | None = Field(default=None, pattern=NAME_PATTERN)
    label_selector: str | None = Field(default=None, max_length=200)

    @field_validator("resource")
    @classmethod
    def _check_resource(cls, value: str) -> str:
        if value not in ALLOWED_RESOURCES:
            raise ValueError(
                f"resource '{value}' is not allowed; allowed: {', '.join(_ALLOWED_RESOURCE_LIST)}"
            )
        return value

    @field_validator("label_selector")
    @classmethod
    def _check_selector(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not all(c.isalnum() or c in "-_./=, " for c in value):
            raise ValueError("label_selector contains unsupported characters")
        return value


class K8sDescribeRequest(BaseModel):
    namespace: Literal["medlab", "argocd", "jenkins", "agents"]
    resource: str
    name: str = Field(pattern=NAME_PATTERN)

    @field_validator("resource")
    @classmethod
    def _check_resource(cls, value: str) -> str:
        if value not in ALLOWED_RESOURCES:
            raise ValueError(f"resource '{value}' is not allowed")
        return value


class K8sLogsRequest(BaseModel):
    namespace: Literal["medlab", "argocd", "jenkins", "agents"]
    pod: str = Field(pattern=NAME_PATTERN)
    container: str | None = Field(default=None, pattern=CONTAINER_PATTERN)
    tail_lines: int = Field(default=100, ge=1, le=500)


class ArgoAppRequest(BaseModel):
    name: str = Field(pattern=NAME_PATTERN)
    namespace: str = "argocd"


class JenkinsStatusRequest(BaseModel):
    job: str = Field(default="medlab-insight", pattern=JOB_PATTERN)
    build: int | None = Field(default=None, ge=1)


class HttpHealthRequest(BaseModel):
    host: str = Field(
        description="Allowlisted host only, e.g. medlab.k8s.orb.local",
        max_length=253,
    )
    path: str = Field(default="/_stcore/health", pattern=r"^/[A-Za-z0-9/_.-]*$")
    scheme: Literal["https", "http"] = "https"
    insecure: bool = Field(
        default=False,
        description="Skip TLS verification (allowlisted internal hosts only)",
    )


def _cap(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated at {limit} chars]"


def k8s_get(payload: K8sGetRequest, limit: int) -> dict[str, object]:
    args = ["get", payload.resource, "-n", payload.namespace, "-o", "json"]
    if payload.name:
        args.append(payload.name)
    if payload.label_selector:
        args.extend(["-l", payload.label_selector])
    output = run_kubectl(args)
    return {"tool": "k8s_get", "ok": True, "output": _cap(output, limit)}


def k8s_describe(payload: K8sDescribeRequest, limit: int) -> dict[str, object]:
    args = ["describe", payload.resource, payload.name, "-n", payload.namespace]
    output = run_kubectl(args)
    return {"tool": "k8s_describe", "ok": True, "output": _cap(output, limit)}


def k8s_logs(payload: K8sLogsRequest, limit: int) -> dict[str, object]:
    args = ["logs", payload.pod, "-n", payload.namespace, f"--tail={payload.tail_lines}"]
    if payload.container:
        args.extend(["-c", payload.container])
    output = run_kubectl(args)
    return {"tool": "k8s_logs", "ok": True, "output": _cap(output, limit)}


def argocd_app(payload: ArgoAppRequest, limit: int) -> dict[str, object]:
    args = ["get", ARGOCD_RESOURCE, payload.name, "-n", "argocd", "-o", "json"]
    output = run_kubectl(args)
    return {"tool": "argocd_app", "ok": True, "output": _cap(output, limit)}


def jenkins_status(
    payload: JenkinsStatusRequest,
    *,
    url: str,
    user: str,
    password: str,
    limit: int,
) -> dict[str, object]:
    if not url:
        raise LookupError("Jenkins is not configured on this gateway (JENKINS_URL empty)")
    base = url.rstrip("/")
    target = f"{base}/job/{payload.job}"
    if payload.build:
        target += f"/{payload.build}"
    target += "/api/json?tree=number,result,building,duration,timestamp"

    request = urllib.request.Request(target)
    if user:
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        request.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return {
            "tool": "jenkins_status",
            "ok": False,
            "output": f"HTTP {exc.code}: {exc.reason}",
        }
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"tool": "jenkins_status", "ok": False, "output": f"unreachable: {exc}"}

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return {"tool": "jenkins_status", "ok": False, "output": _cap(body, limit)}
    summary = {
        "job": payload.job,
        "number": data.get("number"),
        "result": data.get("result"),
        "building": data.get("building"),
        "duration_ms": data.get("duration"),
        "timestamp": data.get("timestamp"),
    }
    return {"tool": "jenkins_status", "ok": True, "output": json.dumps(summary)}


def http_health(payload: HttpHealthRequest, *, allowed_hosts: frozenset[str]) -> dict[str, object]:
    if payload.host not in allowed_hosts:
        raise ValueError(f"host '{payload.host}' is not in the health allowlist")
    url = f"{payload.scheme}://{payload.host}{payload.path}"
    request = urllib.request.Request(url, method="GET")
    context = ssl._create_unverified_context() if payload.insecure else None
    try:
        with urllib.request.urlopen(request, timeout=10, context=context) as response:
            return {"tool": "http_health", "ok": True, "output": f"HTTP {response.status}"}
    except urllib.error.HTTPError as exc:
        return {"tool": "http_health", "ok": False, "output": f"HTTP {exc.code}"}
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"tool": "http_health", "ok": False, "output": f"unreachable: {exc}"}
