from __future__ import annotations

from typing import Self

import pytest
from fastapi.testclient import TestClient

from gateway import tools
from gateway.app import create_app
from gateway.config import Settings

TOKEN = "test-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        tools,
        "run_kubectl",
        lambda args, timeout=15: '{"items": [], "kind": "PodList"}',
    )
    app = create_app(Settings(gateway_token=TOKEN))
    return TestClient(app)


def test_healthz_has_no_auth(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong"}])
def test_auth_required(client: TestClient, headers: dict[str, str]) -> None:
    response = client.post(
        "/tools/k8s_get",
        json={"namespace": "medlab", "resource": "pods"},
        headers=headers,
    )
    assert response.status_code == 401


def test_token_not_configured_is_503() -> None:
    app = create_app(Settings(gateway_token=""))
    response = TestClient(app).post(
        "/tools/k8s_get",
        json={"namespace": "medlab", "resource": "pods"},
        headers=AUTH,
    )
    assert response.status_code == 503


def test_tools_list(client: TestClient) -> None:
    response = client.get("/tools", headers=AUTH)
    assert response.status_code == 200
    names = {tool["name"] for tool in response.json()["tools"]}
    assert {"k8s_get", "k8s_logs", "argocd_app", "jenkins_status"} <= names


def test_k8s_get_builds_safe_args(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[list[str]] = []
    monkeypatch.setattr(
        tools,
        "run_kubectl",
        lambda args, timeout=15: captured.append(args) or '{"items": []}',
    )
    response = client.post(
        "/tools/k8s_get",
        json={"namespace": "medlab", "resource": "pods", "label_selector": "app=medlab"},
        headers=AUTH,
    )
    assert response.status_code == 200
    assert captured == [["get", "pods", "-n", "medlab", "-o", "json", "-l", "app=medlab"]]


@pytest.mark.parametrize("namespace", ["default", "kube-system", ""])
def test_k8s_get_rejects_namespace(client: TestClient, namespace: str) -> None:
    response = client.post(
        "/tools/k8s_get",
        json={"namespace": namespace, "resource": "pods"},
        headers=AUTH,
    )
    assert response.status_code == 422


@pytest.mark.parametrize("resource", ["secrets", "clusterroles", "pods/exec", "delete"])
def test_k8s_get_rejects_resource(client: TestClient, resource: str) -> None:
    response = client.post(
        "/tools/k8s_get",
        json={"namespace": "medlab", "resource": resource},
        headers=AUTH,
    )
    assert response.status_code == 422


def test_k8s_logs_tail_cap(client: TestClient) -> None:
    response = client.post(
        "/tools/k8s_logs",
        json={"namespace": "medlab", "pod": "medlab-insight-abc", "tail_lines": 5000},
        headers=AUTH,
    )
    assert response.status_code == 422


def test_k8s_logs_builds_tail_arg(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[list[str]] = []
    monkeypatch.setattr(
        tools,
        "run_kubectl",
        lambda args, timeout=15: captured.append(args) or "log line",
    )
    response = client.post(
        "/tools/k8s_logs",
        json={"namespace": "medlab", "pod": "medlab-insight-abc", "tail_lines": 50},
        headers=AUTH,
    )
    assert response.status_code == 200
    assert captured == [["logs", "medlab-insight-abc", "-n", "medlab", "--tail=50"]]


def test_describe_rejects_bad_name(client: TestClient) -> None:
    response = client.post(
        "/tools/k8s_describe",
        json={"namespace": "medlab", "resource": "pods", "name": "foo; rm -rf /"},
        headers=AUTH,
    )
    assert response.status_code == 422


def test_argocd_app_uses_crd(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[list[str]] = []
    monkeypatch.setattr(
        tools,
        "run_kubectl",
        lambda args, timeout=15: captured.append(args) or '{"status": {}}',
    )
    response = client.post("/tools/argocd_app", json={"name": "medlab-insight"}, headers=AUTH)
    assert response.status_code == 200
    assert captured == [
        ["get", "applications.argoproj.io", "medlab-insight", "-n", "argocd", "-o", "json"]
    ]


def test_output_is_truncated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tools, "run_kubectl", lambda args, timeout=15: "x" * 50)
    app = create_app(Settings(gateway_token=TOKEN, max_output_chars=10))
    response = TestClient(app).post(
        "/tools/k8s_get",
        json={"namespace": "medlab", "resource": "pods"},
        headers=AUTH,
    )
    assert "...[truncated at 10 chars]" in response.json()["output"]


def test_kubectl_error_maps_to_502(monkeypatch: pytest.MonkeyPatch) -> None:
    from gateway.kube import KubectlError

    def boom(args: list[str], timeout: float = 15) -> str:
        raise KubectlError("pods forbidden", 1)

    monkeypatch.setattr(tools, "run_kubectl", boom)
    app = create_app(Settings(gateway_token=TOKEN))
    response = TestClient(app).post(
        "/tools/k8s_get",
        json={"namespace": "medlab", "resource": "pods"},
        headers=AUTH,
    )
    assert response.status_code == 502
    assert "forbidden" in response.json()["error"]


def test_http_health_rejects_foreign_host(client: TestClient) -> None:
    response = client.post(
        "/tools/http_health",
        json={"host": "example.com", "path": "/_stcore/health"},
        headers=AUTH,
    )
    assert response.status_code == 400


def test_http_health_honours_scheme(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, str] = {}

    class FakeResponse:
        status = 200

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

    def fake_urlopen(request, timeout, context=None):
        seen["url"] = request.full_url
        return FakeResponse()

    monkeypatch.setattr(tools.urllib.request, "urlopen", fake_urlopen)
    response = client.post(
        "/tools/http_health",
        json={"host": "medlab.k8s.orb.local", "path": "/", "scheme": "http"},
        headers=AUTH,
    )
    assert response.status_code == 200
    assert seen["url"] == "http://medlab.k8s.orb.local/"


def test_jenkins_unconfigured_is_503(client: TestClient) -> None:
    response = client.post("/tools/jenkins_status", json={"job": "medlab-insight"}, headers=AUTH)
    assert response.status_code == 503
