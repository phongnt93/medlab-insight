from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

# Namespaces the agent may inspect (read-only).
ALLOWED_NAMESPACES: frozenset[str] = frozenset({"medlab", "argocd", "jenkins", "agents"})

# kubectl resource kinds the agent may query. Everything else (secrets, exec,
# delete, apply, ...) is rejected before a command is ever built.
ALLOWED_RESOURCES: frozenset[str] = frozenset(
    {
        "pods",
        "deployments",
        "services",
        "events",
        "replicasets",
        "statefulsets",
        "ingresses",
        "endpoints",
        "persistentvolumeclaims",
    }
)

# ArgoCD Application CRs are only readable in the argocd namespace.
ARGOCD_RESOURCE = "applications.argoproj.io"

MAX_OUTPUT_CHARS = 20_000

NAME_PATTERN = r"^[a-z0-9]([-a-z0-9.]{0,251}[a-z0-9])?$"
JOB_PATTERN = r"^[a-z0-9][-a-z0-9_]*$"
CONTAINER_PATTERN = r"^[a-z0-9]([-a-z0-9.]{0,61}[a-z0-9])?$"

DEFAULT_HEALTH_HOSTS: frozenset[str] = frozenset({"medlab.k8s.orb.local"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    gateway_token: str = ""
    jenkins_url: str = ""
    jenkins_user: str = ""
    jenkins_password: str = ""
    extra_health_hosts: str = ""
    max_output_chars: int = MAX_OUTPUT_CHARS

    @property
    def allowed_health_hosts(self) -> frozenset[str]:
        extra = {h.strip() for h in self.extra_health_hosts.split(",") if h.strip()}
        return DEFAULT_HEALTH_HOSTS | extra
